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

from config import (
    TOKEN, ADMINS, WEBAPP_URL, BRAND_NAME, BRAND_HANDLE,
    CATALOG_CACHE_TTL, LOG_CHANNEL_ID, SECRET_KEY, SUPPORT_CHAT_URL,
)
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
app.config["SECRET_KEY"] = SECRET_KEY
# Short default for static; real cache-busting uses ?v=ASSET_VERSION on HTML links.
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 120
# Bumps on every process start so redeploys invalidate Telegram/browser caches.
ASSET_VERSION = str(int(time.time()))
app.config["COMPRESS_MIMETYPES"] = [
    "text/html", "text/css", "text/javascript", "application/javascript",
    "application/json",
]
Compress(app)

try:
    db.init_db()
except Exception as e:
    print(f"[anime_db] init deferred / failed: {e}")


def _warm_catalog_cache(pages: int = 3):
    """Pre-fill discovery catalog (memory + disk) fast after redeploy."""
    src = SOURCES.get("anilist")
    if not src:
        return
    try:
        if hasattr(src, "warm_home"):
            src.warm_home(pages=pages)
        else:
            src.get_trending()
            src.get_popular()
            src.get_most_popular()
        print(f"[catalog] cache warmed (pages={pages})")
    except Exception as e:
        print(f"[catalog] warm failed: {e}")


def _catalog_rewarm_loop():
    """Re-warm discovery feeds every ~12 minutes so soft TTL rarely expires cold."""
    import time as _t
    while True:
        _t.sleep(12 * 60)
        try:
            _warm_catalog_cache(pages=2)
        except Exception:
            pass


try:
    import threading
    # Fire warm immediately on process start (redeploy / cold boot)
    threading.Thread(target=_warm_catalog_cache, kwargs={"pages": 3}, daemon=True, name="catalog-warm").start()
    threading.Thread(target=_catalog_rewarm_loop, daemon=True, name="catalog-rewarm").start()
except Exception:
    pass

GENRES = ["Action", "Adventure", "Comedy", "Drama", "Fantasy", "Romance", "Sci-Fi", "Horror"]

USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")


def verify_init_data(init_data: str) -> dict | None:
    if not init_data or not TOKEN:
        return None
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
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
    return bool(user) and user.get("id") in ADMINS


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
    """Call Telegram Bot API. Logs failures so request notifications can be debugged."""
    token = TOKEN
    if not token:
        print("[request-log] TOKEN is empty — cannot send to log channel")
        return None
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/{method}",
            json=payload,
            timeout=15,
        )
        data = r.json() if r.content else {}
        if not data.get("ok"):
            print(f"[request-log] Bot API {method} failed: {data.get('description') or r.text[:200]}")
            return None
        return data
    except requests.RequestException as e:
        print(f"[request-log] Bot API {method} network error: {e}")
        return None


def notify_new_report(title: str, reason: str, details: str, reporter_name: str):
    if not LOG_CHANNEL_ID:
        print("[request-log] LOG_CHANNEL_ID not set — report not posted")
        return
    text = (
        "🚨 New Report\n"
        f"Anime: {title}\n"
        f"Reason: {reason}\n"
        + (f"Details: {details}\n" if details else "")
        + f"By: {reporter_name}"
    )
    chat_id = LOG_CHANNEL_ID
    try:
        chat_id = int(str(LOG_CHANNEL_ID).strip())
    except (TypeError, ValueError):
        pass
    _bot_api("sendMessage", {"chat_id": chat_id, "text": text})


def notify_new_request(request_id: int, title: str, requester_name: str, poster_url: str | None):
    """Post new anime request to LOG_CHANNEL_ID with Accept/Reject buttons (copied from working ECCHI)."""
    if not LOG_CHANNEL_ID:
        print(f"[request-log] LOG_CHANNEL_ID not set — request #{request_id} ({title}) saved but NOT logged")
        return

    chat_id = LOG_CHANNEL_ID
    try:
        chat_id = int(str(LOG_CHANNEL_ID).strip())
    except (TypeError, ValueError):
        chat_id = str(LOG_CHANNEL_ID).strip()

    text = (
        f"📝 New Request\n"
        f"Anime: {title}\n"
        f"By: {requester_name}\n"
        f"ID: {request_id}"
    )
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Accept", "callback_data": f"reqaccept:{request_id}"},
            {"text": "❌ Reject", "callback_data": f"reqreject:{request_id}"},
        ]]
    }

    print(f"[request-log] Posting request #{request_id} '{title}' by {requester_name} → {chat_id}")

    # Prefer photo when poster is available
    if poster_url:
        ok = _bot_api("sendPhoto", {
            "chat_id": chat_id,
            "photo": poster_url,
            "caption": text,
            "reply_markup": keyboard,
        })
        if ok:
            print(f"[request-log] Delivered request #{request_id} as photo")
            return

    ok = _bot_api("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": keyboard,
    })
    if ok:
        print(f"[request-log] Delivered request #{request_id} as text")
    else:
        print(
            f"[request-log] FAILED to post request #{request_id}. "
            f"Check LOG_CHANNEL_ID={chat_id}, bot is admin there, and TOKEN is valid."
        )


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
        token = TOKEN or TOKEN
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


@app.after_request
def _cache_headers(resp):
    """HTML must not be cached (Telegram WebApp + browsers otherwise keep old UI).
    Versioned static assets (?v=) can be cached briefly."""
    path = request.path or ""
    if path == "/" or path.endswith(".html"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    elif path.startswith("/static/"):
        # Short browser cache; ?v= on the URL is the real invalidation key.
        resp.headers["Cache-Control"] = "public, max-age=300, must-revalidate"
    return resp


@app.route("/", methods=["GET", "POST"])
def index():
    # Telegram may still POST updates here if an old webhook points at WEBAPP_URL.
    # We run Pyrogram in polling mode, so ignore POSTs with 200 to stop retry spam.
    if request.method == "POST":
        return "", 200
    return render_template(
        "index.html",
        brand_name=BRAND_NAME,
        brand_handle=BRAND_HANDLE,
        asset_version=ASSET_VERSION,
    )


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
        src = SOURCES.get("anilist")
        if src and hasattr(src, "warm_home"):
            src.warm_home(pages=1)
        elif src:
            src.get_trending()
            src.get_popular()
            src.get_most_popular()
    except Exception:
        pass
    return jsonify(status="ok")


@app.get("/api/catalog/trending")
def api_trending():
    page = request.args.get("page", 1, type=int)
    try:
        data = SOURCES["anilist"].get_trending(page)
        resp = jsonify(data)
        # Browser may reuse for 5 min; allow stale while revalidating for 1 h
        resp.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=3600"
        return resp
    except Exception as e:
        app.logger.warning("catalog/trending failed: %s", e)
        return jsonify({"results": [], "has_next": False, "error": str(e)[:200]}), 200


@app.get("/api/catalog/popular")
def api_popular():
    page = request.args.get("page", 1, type=int)
    try:
        data = SOURCES["anilist"].get_popular(page)
        resp = jsonify(data)
        resp.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=3600"
        return resp
    except Exception as e:
        app.logger.warning("catalog/popular failed: %s", e)
        return jsonify({"results": [], "has_next": False, "error": str(e)[:200]}), 200


@app.get("/api/catalog/most-popular")
def api_most_popular():
    page = request.args.get("page", 1, type=int)
    try:
        data = SOURCES["anilist"].get_most_popular(page)
        resp = jsonify(data)
        resp.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=3600"
        return resp
    except Exception as e:
        app.logger.warning("catalog/most-popular failed: %s", e)
        return jsonify({"results": [], "has_next": False, "error": str(e)[:200]}), 200


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
    env_url = (SUPPORT_CHAT_URL or "").strip()
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
    # Optional separate ongoing-only join URL (empty string clears it)
    has_ongoing = "ongoing_link" in payload
    raw_ongoing = (payload.get("ongoing_link") or "").strip() if has_ongoing else None
    if not db.get_anime(anime_id):
        abort(404)
    try:
        link = normalize_join_link(raw_link) if raw_link else ""
        ongoing_link = normalize_join_link(raw_ongoing) if (has_ongoing and raw_ongoing) else ("" if has_ongoing else None)
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
        if has_ongoing:
            db.update_ongoing_link(anime_id, ongoing_link or None)
        propagated = propagate_link_full_franchise(anime_id, link)
        db.accept_requests_for_title(anime["title"])
        updated = db.get_anime(anime_id)
        return jsonify(status="updated", link=link, ongoing_link=updated.get("ongoing_link"), propagated=propagated, anime=updated)
    # Only ongoing_link update without touching/clearing the main link
    if has_ongoing and not raw_link:
        existing = db.get_anime(anime_id)
        if not existing or not existing.get("join_link"):
            return jsonify(error="Set a main Join URL first."), 400
        updated = db.update_ongoing_link(anime_id, ongoing_link or None)
        return jsonify(status="updated", link=existing.get("join_link"), ongoing_link=updated.get("ongoing_link"), propagated=0, anime=updated)
    # No link = not a real post anymore — delete it (and the rest of its
    # franchise, which just lost the link via propagation) from MongoDB
    # entirely, rather than leaving an unlinked, unjoinable entry behind.
    propagated = db.delete_anime_family(anime_id)
    return jsonify(status="deleted", link="", propagated=propagated)




@app.patch("/api/anime/<int:anime_id>/display-mode")
def api_set_display_mode(anime_id):
    """Admin: solo card vs group with franchise seasons on Home → Finished."""
    user = current_user()
    if not is_admin(user):
        abort(403)
    if not db.get_anime(anime_id):
        abort(404)
    payload = request.get_json(force=True, silent=True) or {}
    mode = payload.get("mode") or "group"
    try:
        updated = db.update_display_mode(anime_id, mode)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    return jsonify(status="ok", anime=updated)


@app.patch("/api/anime/<int:anime_id>/airing-day")
def api_set_airing_day(anime_id):
    """Admin: assign this posted anime to a weekday for the Home ONGOING tab."""
    user = current_user()
    if not is_admin(user):
        abort(403)
    if not db.get_anime(anime_id):
        abort(404)
    payload = request.get_json(force=True, silent=True) or {}
    day = payload.get("day")
    try:
        updated = db.update_airing_day(anime_id, day)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    return jsonify(status="ok", anime=updated)


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


