"""
Anime Index Mini App — Flask JSON API + static/HTML for the Telegram WebApp.

Telegram bot commands (/anidex, library search, request Accept/Reject) live in
plugins/index.py (Pyrogram). This module only serves HTTP.
"""

import hashlib
import hmac
import json
import re
import threading
import time
from collections import defaultdict, deque
from functools import wraps
from pathlib import Path
from urllib.parse import parse_qsl, quote

import requests
from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from flask_compress import Compress

from config import Config, TOKEN, ADMINS, WEBAPP_URL, BRAND_NAME, BRAND_HANDLE, CATALOG_CACHE_TTL, LOG_CHANNEL_ID
from helper import database as db

# AniList source
from plugins.anilist import AniListSource

SOURCES = {"anilist": AniListSource()}

# Resolved at runtime from bot.py after Pyrogram starts
_pyrogram_client = None


def set_bot_client(client):
    """Called from bot startup so invite-link creation + log posts use Pyrogram."""
    global _pyrogram_client
    _pyrogram_client = client


WEB_DIR = Path(__file__).resolve().parent / "plugins" / "web"

app = Flask(
    __name__,
    static_folder=str(WEB_DIR),
    static_url_path="/static",
    template_folder=str(WEB_DIR),
)
app.config["SECRET_KEY"] = Config.SECRET_KEY
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 3600
app.config["COMPRESS_MIMETYPES"] = [
    "text/html", "text/css", "text/javascript", "application/javascript",
    "application/json",
]
Compress(app)

try:
    db.init_db()
except Exception as e:
    print(f"[anime_db] init deferred / failed: {e}")

GENRES = ["Action", "Adventure", "Comedy", "Drama", "Fantasy", "Romance", "Sci-Fi", "Horror"]

USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")


def verify_init_data(init_data: str) -> dict | None:
    if not init_data or not Config.BOT_TOKEN:
        return None
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", Config.BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    user_raw = parsed.get("user")
    if not user_raw:
        return None
    return json.loads(user_raw)


def current_user():
    """Returns the verified Telegram user dict for this request, or None if
    the request didn't come from inside Telegram (or failed verification)."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    return verify_init_data(init_data)


def is_admin(user: dict | None) -> bool:
    return bool(user) and user.get("id") in Config.ADMIN_IDS


# ---------------------------------------------------------------------------
# Spam / flood-wait protection
#
# In-memory sliding-window limiter, keyed per Telegram user (falling back to
# IP only for the rare unauthenticated call). This matches the app's
# existing architecture — a single gunicorn worker holding in-memory state
# (see the AniList plugin's cache, and the module docstring above) — so a
# plain dict is enough; there's no second process for it to be inconsistent
# with. Admins are exempt so moderating the queue is never throttled.
# ---------------------------------------------------------------------------
_rate_lock = threading.Lock()
_rate_hits: dict[str, deque] = defaultdict(deque)


def _rate_limit_key(user: dict | None) -> str:
    if user and user.get("id"):
        return f"tg:{user['id']}"
    return f"ip:{request.remote_addr or 'unknown'}"


def _check_rate_limit(bucket: str, key: str, limit: int, window_seconds: float) -> bool:
    """True if this call is allowed (and is recorded); False if `key` has
    already made `limit` calls to `bucket` within the trailing
    `window_seconds`."""
    now = time.time()
    dq_key = f"{bucket}:{key}"
    with _rate_lock:
        dq = _rate_hits[dq_key]
        while dq and dq[0] <= now - window_seconds:
            dq.popleft()
        if len(dq) >= limit:
            return False
        dq.append(now)
        return True


def rate_limited(bucket: str, limit: int, window_seconds: float):
    """Decorator for a Flask view: rejects with 429 once the calling user
    exceeds `limit` calls to `bucket` per `window_seconds`. Use this for
    endpoints that create/send something (requests, reports) on top of the
    blanket per-request flood guard below, since spam there is cheap for
    an abuser but costly for admins reading the Logs feed."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if is_admin(user):
                return fn(*args, **kwargs)
            key = _rate_limit_key(user)
            if not _check_rate_limit(bucket, key, limit, window_seconds):
                return jsonify(error="Too many requests — please slow down and try again in a bit."), 429
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@app.before_request
def _flood_guard():
    """Blanket flood-wait protection for every API call, independent of
    the stricter per-action limits above. Generous enough that normal use
    (Home's several parallel loads, fast tab-switching, typing a search)
    never comes close, but it stops a runaway client loop or a scripted
    abuser from hammering the server."""
    if not request.path.startswith("/api/"):
        return None
    user = current_user()
    if is_admin(user):
        return None
    key = _rate_limit_key(user)
    if not _check_rate_limit("global", key, 120, 60):
        return jsonify(error="Too many requests — please slow down and try again in a bit."), 429
    return None


# A Telegram public username: 5-32 chars, must start with a letter, only
# letters/digits/underscores after that (Telegram's own username rules).


def _telegram_user_label(user: dict | None) -> str:
    if not user:
        return "Guest"
    if user.get("username"):
        return f"@{user['username']}"
    name = " ".join(filter(None, [user.get("first_name"), user.get("last_name")]))
    return name or str(user.get("id"))


def _bot_api(method: str, payload: dict):
    token = Config.BOT_TOKEN or TOKEN
    if not token:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{token}/{method}", json=payload, timeout=15)
    except requests.RequestException:
        pass


def notify_new_report(title: str, reason: str, details: str, reporter_name: str):
    if not Config.LOG_CHANNEL_ID:
        return
    text = (
        f"\U0001f6a9 New Report\n"
        f"Anime: {title}\n"
        f"Reason: {reason}\n"
        + (f"Details: {details}\n" if details else "")
        + f"By: {reporter_name}"
    )
    _bot_api("sendMessage", {"chat_id": Config.LOG_CHANNEL_ID, "text": text})


def notify_new_request(request_id: int, title: str, requester_name: str, poster_url: str | None):
    if not Config.LOG_CHANNEL_ID:
        return
    text = (
        f"\U0001f4dd New Request\n"
        f"Anime: {title}\n"
        f"By: {requester_name}"
    )
    keyboard = {
        "inline_keyboard": [[
            {"text": "\u2705 Accept", "callback_data": f"reqaccept:{request_id}"},
            {"text": "\u274c Reject", "callback_data": f"reqreject:{request_id}"},
        ]]
    }
    _bot_api("sendMessage", {
        "chat_id": Config.LOG_CHANNEL_ID,
        "text": text,
        "reply_markup": keyboard,
    })



USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")


def normalize_join_link(raw: str) -> str:
    """Turn admin paste into a safe Telegram URL. Raises ValueError on bad input."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        if "t.me/" not in raw and "telegram.me/" not in raw:
            raise ValueError("That doesn't look like a Telegram link.")
        return raw
    if raw.startswith("t.me/") or raw.startswith("telegram.me/"):
        return "https://" + raw
    if re.fullmatch(r"-?\d+", raw):
        token = Config.BOT_TOKEN or TOKEN
        if not token:
            raise ValueError("Bot isn't connected — can't generate an invite link for a channel ID.")
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/createChatInviteLink",
                json={"chat_id": int(raw)},
                timeout=15,
            )
            data = r.json()
            if not data.get("ok"):
                raise ValueError(
                    "Couldn't create an invite link for that channel ID — make sure the bot "
                    "has been added to that channel as an admin with 'Invite Users' permission."
                )
            return data["result"]["invite_link"]
        except requests.RequestException:
            raise ValueError("Couldn't create an invite link right now. Try again.")
    username = raw[1:] if raw.startswith("@") else raw
    if not USERNAME_RE.match(username):
        raise ValueError(
            "Enter a Telegram @username, a t.me/ link, an invite link (https://t.me/+...), "
            "or a channel ID."
        )
    return f"https://t.me/{username}"


def propagate_link_full_franchise(anime_id: int, link: str) -> int:
    doc = db.get_anime(anime_id)
    if not doc:
        return 0
    source = doc["source"]
    src = SOURCES[source]
    seen = {str(doc["source_id"])}
    frontier = [str(x) for x in (doc.get("related_ids") or [])]
    updated = 0
    MAX_FETCHES = 40
    while frontier and updated < MAX_FETCHES:
        sid = frontier.pop()
        if sid in seen:
            continue
        seen.add(sid)
        existing = db.find_by_source_id(source, sid)
        if existing:
            db.update_link(existing["id"], link)
            updated += 1
            frontier.extend(str(x) for x in (existing.get("related_ids") or []))
            continue
        try:
            details = src.get_details(sid)
        except requests.RequestException:
            continue
        new_id = db.upsert_anime(details)
        db.update_link(new_id, link)
        updated += 1
        frontier.extend(str(x) for x in (details.get("related_ids") or []))
    return updated


@app.route("/", methods=["GET", "POST"])
def index():
    # Telegram may still POST updates here if an old webhook points at WEBAPP_URL.
    # We run Pyrogram in polling mode, so ignore POSTs with 200 to stop retry spam.
    if request.method == "POST":
        return "", 200
    return render_template("index.html", brand_name=Config.BRAND_NAME, brand_handle=Config.BRAND_HANDLE)


@app.get("/favicon.ico")
def favicon():
    return "", 204


@app.get("/healthz")
def healthz():
    # Also opportunistically warms the Trending/Popular/Most-popular cache
    # (see plugins/anilist.py's _cached — same TTL Home reads from). On a
    # free hosting tier that spins down when idle, the very first real
    # visitor after a cold start would otherwise be the one who eats a
    # live AniList round trip on all three sections at once. Pointing an
    # external uptime monitor (UptimeRobot, cron-job.org, etc.) at this
    # endpoint every ~10 minutes keeps both the process warm *and* this
    # cache fresh, so real users essentially never see a cold load.
    # Best-effort: a slow/unreachable AniList must never fail the health
    # check itself, so failures here are swallowed.
    try:
        SOURCES["anilist"].get_trending()
        SOURCES["anilist"].get_popular()
        SOURCES["anilist"].get_most_popular()
    except Exception:
        pass
    return jsonify(status="ok")


@app.get("/api/catalog/trending")
def api_trending():
    page = request.args.get("page", 1, type=int)
    try:
        resp = jsonify(SOURCES["anilist"].get_trending(page))
    except requests.RequestException:
        return jsonify({"results": [], "has_next": False})
    resp.headers["Cache-Control"] = f"public, max-age={Config.CATALOG_CACHE_TTL}"
    return resp


@app.get("/api/catalog/popular")
def api_popular():
    page = request.args.get("page", 1, type=int)
    try:
        resp = jsonify(SOURCES["anilist"].get_popular(page))
    except requests.RequestException:
        return jsonify({"results": [], "has_next": False})
    resp.headers["Cache-Control"] = f"public, max-age={Config.CATALOG_CACHE_TTL}"
    return resp


@app.get("/api/catalog/most-popular")
def api_most_popular():
    page = request.args.get("page", 1, type=int)
    try:
        resp = jsonify(SOURCES["anilist"].get_most_popular(page))
    except requests.RequestException:
        return jsonify({"results": [], "has_next": False})
    resp.headers["Cache-Control"] = f"public, max-age={Config.CATALOG_CACHE_TTL}"
    return resp


@app.post("/api/search/track")
def api_search_track():
    payload = request.get_json(force=True, silent=True) or {}
    query = (payload.get("query") or "").strip()
    if query:
        db.record_search(query)
    return jsonify(status="ok")


@app.get("/api/search/popular")
def api_search_popular():
    limit = request.args.get("limit", 6, type=int)
    return jsonify(db.get_popular_searches(limit))


@app.post("/api/search/clear")
def api_search_clear():
    user = current_user()
    if not is_admin(user):
        abort(403)
    db.clear_popular_searches()
    return jsonify(status="cleared")


@app.get("/api/search/anime")
def api_search_anime():
    q = (request.args.get("q") or "").strip()
    page = request.args.get("page", 1, type=int)
    if not q:
        return jsonify({"results": [], "has_next": False})
    try:
        return jsonify(SOURCES["anilist"].search(q, page))
    except requests.RequestException:
        return jsonify({"results": [], "has_next": False})


@app.get("/api/genres/<genre>")
def api_genre_browse(genre):
    page = request.args.get("page", 1, type=int)
    try:
        return jsonify(SOURCES["anilist"].browse_genre(genre, page))
    except requests.RequestException:
        return jsonify({"results": [], "has_next": False})


@app.get("/api/catalog/available")
def api_available():
    # A title is only ever saved without being deleted again while it has
    # a join link (see upsert_anime/delete_anime_family in database.py),
    # so in practice db.list_available() is already links-only. This
    # filter is a defensive safety net for that invariant — e.g. any
    # pre-existing data from before this behavior — so the public
    # Available tab never shows an unjoinable title even if one somehow
    # exists without a link.
    return jsonify([a for a in db.list_available() if a.get("available")])


def _related_posted(details: dict) -> list[dict]:
    """The whole franchise (seasons, OVAs, movies, spin-offs, alternates —
    every entry reachable by walking AniList's relation graph) collapsed
    into a single release-chronological timeline, filtered to entries that
    are actually posted. Returns just the immediately-previous and
    immediately-next entry relative to `details` — never one card per
    AniList relation edge — so the detail sheet always shows at most a
    Prequel card and a Sequel card, no matter how large the franchise is."""
    return db.get_franchise_neighbors(details)


@app.get("/api/anime/<int:anime_id>")
def api_anime_detail(anime_id):
    anime = db.get_anime(anime_id)
    if not anime:
        abort(404)
    anime["related_posted"] = _related_posted(anime)
    return jsonify(anime)


@app.get("/api/anilist/<int:anilist_id>")
def api_anilist_details(anilist_id):
    """Full details (genres/synopsis/banner) for a Trending/Popular card —
    the lightweight discovery query doesn't include those fields."""
    try:
        details = SOURCES["anilist"].get_details(anilist_id)
    except requests.RequestException:
        abort(502)
    details["related_posted"] = _related_posted(details)
    return jsonify(details)


@app.post("/api/request")
@rate_limited("request", limit=8, window_seconds=600)
def api_request_anime():
    payload = request.get_json(force=True, silent=True) or {}
    title = (payload.get("title") or "").strip()
    if not title:
        return jsonify(error="title is required"), 400
    source = payload.get("source")
    source_id = payload.get("source_id")
    poster_url = payload.get("poster_url")
    genres = payload.get("genres")

    user = current_user()
    if not user:
        return jsonify(error="Open this inside Telegram to request an anime."), 401

    result = db.create_request(title, source, source_id, poster_url, genres, user["id"], _telegram_user_label(user))
    if result["status"] == "limit_reached":
        return jsonify(
            error=f"You've got {result['limit']} pending requests already — wait for one to be "
                  f"reviewed before requesting more."
        ), 429
    if not result["already_requested"]:
        notify_new_request(result["id"], title, _telegram_user_label(user), poster_url)
    return jsonify(result)


@app.get("/api/notifications")
def api_notifications():
    user = current_user()
    if not user:
        return jsonify(unseen_count=0, notifications=[])
    return jsonify(db.get_user_notifications(user["id"]))


@app.post("/api/notifications/seen")
def api_notifications_seen():
    user = current_user()
    if not user:
        return jsonify(error="Open this inside Telegram."), 401
    db.mark_notifications_seen(user["id"])
    return jsonify(status="ok")


@app.get("/api/admin/requests")
def api_admin_requests():
    user = current_user()
    if not is_admin(user):
        abort(403)
    return jsonify(db.list_pending_requests())


@app.patch("/api/admin/requests/<path:key>")
def api_admin_respond_request(key):
    user = current_user()
    if not is_admin(user):
        abort(403)
    payload = request.get_json(force=True, silent=True) or {}
    status = payload.get("status")
    if status not in ("accepted", "rejected"):
        return jsonify(error="status must be 'accepted' or 'rejected'"), 400
    updated = db.respond_to_request(key, status)
    return jsonify(status="ok", updated=updated)


@app.post("/api/report")
@rate_limited("report", limit=5, window_seconds=600)
def api_report():
    payload = request.get_json(force=True, silent=True) or {}
    reason = (payload.get("reason") or "").strip()
    if not reason:
        return jsonify(error="reason is required"), 400
    details = (payload.get("details") or "").strip()[:50]
    anime_id = payload.get("anime_id")
    anime_title = (payload.get("anime_title") or "").strip()

    user = current_user()
    reporter_id = user.get("id") if user else None
    reporter_name = _telegram_user_label(user) if user else "Guest"

    db.create_report(anime_id, anime_title, reason, details, reporter_id, reporter_name)
    notify_new_report(anime_title, reason, details, reporter_name)
    return jsonify(status="received"), 201


@app.get("/api/profile")
def api_profile():
    user = current_user()
    if not user:
        return jsonify(error="Open this from inside Telegram to view your profile."), 401
    profile = db.get_or_create_user(
        telegram_id=user["id"],
        username=user.get("username"),
        first_name=user.get("first_name"),
        is_admin=is_admin(user),
    )
    return jsonify(profile)


def _resolve_support_chat_url(mongo_url: str | None = None) -> str:
    """Env SUPPORT_CHAT_URL wins when set; otherwise use the value saved in Mongo."""
    env_url = (getattr(Config, "SUPPORT_CHAT_URL", None) or "").strip()
    if env_url:
        return env_url
    return (mongo_url or "").strip()


@app.get("/api/profile/help")
def api_profile_help():
    """Need-help card: title, text, link buttons, more-channels, and support chat."""
    data = db.get_profile_help()
    data["support_chat_url"] = _resolve_support_chat_url(data.get("support_chat_url"))
    return jsonify(data)


@app.put("/api/profile/help")
def api_profile_help_update():
    """Admin: update help card title/text and/or the lists of links."""
    user = current_user()
    if not is_admin(user):
        abort(403)
    payload = request.get_json(force=True, silent=True) or {}
    help_kwargs = {}
    if "title" in payload:
        help_kwargs["title"] = payload.get("title")
    if "text" in payload:
        help_kwargs["text"] = payload.get("text")
    if "support_chat_url" in payload:
        help_kwargs["support_chat_url"] = payload.get("support_chat_url")
    if help_kwargs:
        db.set_profile_help(**help_kwargs)
    if "links" in payload:
        links = payload.get("links")
        if not isinstance(links, list):
            return jsonify(error="links must be a list"), 400
        db.set_profile_links(links)
    if "more_links" in payload:
        more_links = payload.get("more_links")
        if not isinstance(more_links, list):
            return jsonify(error="more_links must be a list"), 400
        db.set_more_channel_links(more_links)
    data = db.get_profile_help()
    data["support_chat_url"] = _resolve_support_chat_url(data.get("support_chat_url"))
    return jsonify(data)


@app.patch("/api/anime/<int:anime_id>/link")
def api_edit_link(anime_id):
    user = current_user()
    if not is_admin(user):
        abort(403)
    payload = request.get_json(force=True, silent=True) or {}
    raw_link = (payload.get("link") or "").strip()
    if not db.get_anime(anime_id):
        abort(404)
    try:
        link = normalize_join_link(raw_link)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    if link:
        # Setting a link is also the natural moment to refresh this post's
        # cached AniList metadata (poster, genres, episode count, and
        # critically its relations list) — not just the join_link field.
        # Without this, a post created before the relations field existed
        # (or one whose franchise has grown since it was posted) would be
        # permanently stuck with stale/missing data and never show
        # Prequel/Sequel cards, since nothing else ever re-fetches it.
        anime = db.get_anime(anime_id)
        try:
            details = SOURCES[anime["source"]].get_details(anime["source_id"], use_cache=False)
            db.upsert_anime(details)
        except requests.RequestException:
            pass  # AniList unreachable — keep whatever's cached, still set the link below
        db.update_link(anime_id, link)
        propagated = propagate_link_full_franchise(anime_id, link)
        db.accept_requests_for_title(anime["title"])
        return jsonify(status="updated", link=link, propagated=propagated)
    # No link = not a real post anymore — delete it (and the rest of its
    # franchise, which just lost the link via propagation) from MongoDB
    # entirely, rather than leaving an unlinked, unjoinable entry behind.
    propagated = db.delete_anime_family(anime_id)
    return jsonify(status="deleted", link="", propagated=propagated)


@app.post("/api/anime/link-anilist/<int:anilist_id>")
def api_set_link_from_anilist(anilist_id):
    """Set a join link for a title that's only been browsed from AniList
    (Discover/Genre) and doesn't have a local library entry yet. Creates
    that entry on the fly — from this point on it's a normal posted anime
    and shows up in the Available tab, same as one added via /addpost."""
    user = current_user()
    if not is_admin(user):
        abort(403)
    payload = request.get_json(force=True, silent=True) or {}
    raw_link = (payload.get("link") or "").strip()
    if not raw_link:
        return jsonify(error="A join link is required."), 400
    try:
        link = normalize_join_link(raw_link)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    try:
        details = SOURCES["anilist"].get_details(anilist_id)
    except requests.RequestException:
        return jsonify(error="Couldn't fetch details from AniList right now."), 502
    anime_id = db.upsert_anime(details, added_by=user["id"])
    db.update_link(anime_id, link)
    propagated = propagate_link_full_franchise(anime_id, link)
    db.accept_requests_for_title(details["title"])
    return jsonify(status="updated", anime=db.get_anime(anime_id), propagated=propagated)


