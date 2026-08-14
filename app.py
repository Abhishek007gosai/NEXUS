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
    TOKEN, ADMINS, WEBAPP_URL, BRAND_NAME, BRAND_HANDLE, BOTNAME,
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


def _warm_catalog_cache(pages: int = 1, delay_sec: float = 0):
    """Pre-fill discovery catalog (memory + disk) after redeploy.

    Uses few pages + optional start delay so we don't trip AniList 429
    right as the bot and web process also boot.
    """
    if delay_sec and delay_sec > 0:
        time.sleep(delay_sec)
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
    """Re-warm discovery feeds every ~15 minutes so soft TTL rarely expires cold."""
    while True:
        time.sleep(15 * 60)
        try:
            _warm_catalog_cache(pages=1)
        except Exception:
            pass


try:
    import threading
    # Delay first warm so boot traffic + bot start don't stack 429s
    threading.Thread(
        target=_warm_catalog_cache,
        kwargs={"pages": 1, "delay_sec": 8},
        daemon=True,
        name="catalog-warm",
    ).start()
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
    bot = _bot_username()
    name = (BOTNAME or BRAND_NAME or "").strip()
    if bot:
        bot_line = f"Bot: @{bot}"
    elif name:
        bot_line = f"Bot: {name}"
    else:
        bot_line = "Bot: (unknown)"
    text = (
        "🚨 New Report\n"
        f"{bot_line}\n"
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

    bot = _bot_username()
    name = (BOTNAME or BRAND_NAME or "").strip()
    if bot:
        bot_line = f"Bot: @{bot}"
    elif name:
        bot_line = f"Bot: {name}"
    else:
        bot_line = "Bot: (unknown)"

    text = (
        f"📝 New Request\n"
        f"{bot_line}\n"
        f"Anime: {title}\n"
        f"By: {requester_name}"
    )
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Accept", "callback_data": f"reqaccept:{request_id}"},
            {"text": "❌ Reject", "callback_data": f"reqreject:{request_id}"},
        ]]
    }

    print(f"[request-log] Posting request #{request_id} '{title}' by {requester_name} → {chat_id}")

    # Text-only (no poster) so the log channel stays clean
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


_bot_username_cache = {"name": None, "ts": 0}


def _bot_username() -> str | None:
    """Resolve this bot's public @username (cached)."""
    now = time.time()
    if _bot_username_cache["name"] and now - _bot_username_cache["ts"] < 3600:
        return _bot_username_cache["name"]
    if not TOKEN:
        return None
    try:
        r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=8)
        data = r.json()
        if data.get("ok") and data.get("result", {}).get("username"):
            _bot_username_cache["name"] = data["result"]["username"]
            _bot_username_cache["ts"] = now
            return _bot_username_cache["name"]
    except Exception:
        pass
    return None


def normalize_join_link(raw: str) -> str:
    """Turn admin paste into a safe Telegram URL. Raises ValueError on bad input.

    Accepts full t.me links, @username, channel IDs, and deep-link fragments
    like `?start=TOKEN` or `start=TOKEN` (completed using this bot's username).
    """
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        if "t.me/" not in raw and "telegram.me/" not in raw:
            raise ValueError("That doesn't look like a Telegram link.")
        return raw
    if raw.startswith("t.me/") or raw.startswith("telegram.me/"):
        return "https://" + raw
    # Deep-link start payload — including truncated pastes from mobile:
    #   ?start=XXX  start=XXX  t?start=XXX  me?start=XXX  Bot?start=XXX
    start_payload = None
    m = re.search(r"(?:\?start=|^start=)([A-Za-z0-9_\-]+)$", raw)
    if m:
        start_payload = m.group(1)
    elif re.match(r"^t=([A-Za-z0-9_\-]+)$", raw):
        # Truncated URL that only kept the end of ?start=...
        start_payload = raw.split("=", 1)[1]
    elif re.fullmatch(r"[A-Za-z0-9_\-]{8,}", raw) and ("=" not in raw) and ("/" not in raw):
        # Bare start token (base64-ish)
        start_payload = raw
    if start_payload:
        bot = _bot_username()
        if not bot:
            raise ValueError(
                "Paste the full https://t.me/YourBot?start=... link "
                "(couldn't resolve this bot's username automatically)."
            )
        return f"https://t.me/{bot}?start={start_payload}"
    if re.fullmatch(r"-?\d+", raw):
        if not TOKEN:
            raise ValueError("Bot isn't connected — can't generate an invite link for a channel ID.")
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/createChatInviteLink",
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
            "a bot deep link (https://t.me/Bot?start=...), or a channel ID."
        )
    return f"https://t.me/{username}"


def propagate_link_full_franchise(anime_id: int, link: str) -> int:
    """Expand AniList franchise into MongoDB and share the finished join link.

    Skips titles marked display_mode=solo so Solo highlights keep their own link.
    New franchise members are stored as display_mode=group.
    """
    doc = db.get_anime(anime_id)
    if not doc:
        return 0
    source = doc["source"]
    src = SOURCES.get(source) or SOURCES.get("anilist")
    if not src:
        return 0
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
            # Never overwrite a Solo highlight's own link/mode
            if (existing.get("display_mode") or "group") == "solo":
                frontier.extend(str(x) for x in (existing.get("related_ids") or []))
                continue
            db.update_link(existing["id"], link)
            try:
                db.update_display_mode(existing["id"], "group")
            except Exception:
                pass
            updated += 1
            frontier.extend(str(x) for x in (existing.get("related_ids") or []))
            continue
        try:
            details = src.get_details(sid)
        except Exception:
            continue
        new_id = db.upsert_anime(details)
        db.update_link(new_id, link)
        try:
            db.update_display_mode(new_id, "group")
        except Exception:
            pass
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



_DOWN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>Website Down</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #0d0d0d;
      color: #e8e8e8;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      padding: 24px;
      text-align: center;
    }
    .card {
      max-width: 340px;
      width: 100%;
      background: #1a1a1a;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 18px;
      padding: 32px 24px;
    }
    .icon { font-size: 42px; margin-bottom: 12px; }
    h1 { font-size: 20px; font-weight: 700; margin-bottom: 8px; }
    p { font-size: 14px; color: rgba(255,255,255,0.55); line-height: 1.45; margin-bottom: 20px; }
    button {
      border: none;
      border-radius: 12px;
      padding: 12px 22px;
      background: linear-gradient(135deg, #1f5628, #2d7a3a);
      color: #fff;
      font-weight: 700;
      font-size: 14px;
      cursor: pointer;
      width: 100%;
    }
    button:active { opacity: 0.9; transform: scale(0.98); }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">⚠</div>
    <h1>Website is temporarily down</h1>
    <p>We're updating the service. Please try again in a few minutes.</p>
    <button onclick="location.reload()">Try Again</button>
  </div>
</body>
</html>
"""


@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/"):
        return jsonify(error="Not found"), 404
    return _DOWN_HTML, 404, {"Content-Type": "text/html; charset=utf-8"}


@app.errorhandler(502)
@app.errorhandler(503)
@app.errorhandler(504)
def service_unavailable(_e):
    if request.path.startswith("/api/"):
        return jsonify(error="Service unavailable"), 503
    return _DOWN_HTML, 503, {"Content-Type": "text/html; charset=utf-8"}


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
    """Search local MongoDB first (fast), then AniList (cached in Mongo).

    Merges local posted titles with AniList results so search works even
    when AniList is rate-limited or slow.
    """
    q = (request.args.get("q") or "").strip()
    page = request.args.get("page", 1, type=int)
    if not q:
        return jsonify({"results": [], "has_next": False})

    local_hits = []
    try:
        local_hits = db.search_local(q, limit=40)
    except Exception as e:
        print(f"[search] local failed: {e}")

    # Normalize local docs to the same shape as AniList search rows
    results = []
    seen_ids = set()
    for a in local_hits:
        sid = str(a.get("source_id") or a.get("anilist_id") or a.get("id") or "")
        if sid:
            seen_ids.add(sid)
        results.append({
            "id": a.get("id"),
            "source_id": a.get("source_id") or a.get("anilist_id"),
            "anilist_id": a.get("anilist_id") or a.get("source_id"),
            "title": a.get("title"),
            "alt_title": a.get("alt_title"),
            "year": a.get("year"),
            "poster_url": a.get("poster_url"),
            "rating": a.get("rating"),
            "genres": (a.get("genres") or [])[:3],
            "format": a.get("format"),
            "episodes": a.get("episodes"),
            "status": a.get("status"),
            "join_link": a.get("join_link"),
            "ongoing_link": a.get("ongoing_link"),
            "matchedJoinLink": a.get("join_link") or a.get("ongoing_link"),
            "from_library": True,
        })

    # AniList (page 1 merges with local; later pages are AniList-only)
    al_error = None
    has_next = False
    try:
        al = SOURCES["anilist"].search(q, page)
        has_next = bool(al.get("has_next"))
        for item in al.get("results") or []:
            sid = str(item.get("anilist_id") or item.get("source_id") or "")
            if sid and sid in seen_ids:
                continue
            if sid:
                seen_ids.add(sid)
            # Prefer library match for join links
            matched = None
            try:
                if sid:
                    matched = db.find_by_source_id("anilist", sid)
            except Exception:
                matched = None
            if matched:
                item["id"] = matched.get("id")
                item["join_link"] = matched.get("join_link")
                item["ongoing_link"] = matched.get("ongoing_link")
                item["matchedJoinLink"] = matched.get("join_link") or matched.get("ongoing_link")
            results.append(item)
    except requests.RequestException as e:
        al_error = str(e) or "AniList unavailable"
    except Exception as e:
        al_error = str(e) or "Search failed"

    # If AniList failed but we have local results, still return 200
    if al_error and not results:
        return jsonify({"results": [], "has_next": False, "error": al_error}), 502

    # Page > 1: local already shown on page 1; only return AniList page slice
    # (AniList results already appended above for this page)
    if page > 1:
        # Drop pure-local-only rows on later pages (they were page-1)
        results = [r for r in results if not r.get("from_library")]

    return jsonify({"results": results, "has_next": has_next, "error": al_error})


@app.get("/api/genres/<genre>")
def api_genre_browse(genre):
    page = request.args.get("page", 1, type=int)
    media_type = (request.args.get("type") or "anime").lower()
    if media_type not in ("anime", "manga"):
        media_type = "anime"
    try:
        return jsonify(SOURCES["anilist"].browse_genre(genre, page, media_type=media_type))
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

    # Enrich missing synopsis / related_ids from AniList so prequel/sequel + description work
    needs_enrich = (
        not (anime.get("description") or "").strip()
        or not (anime.get("related_ids") or [])
        or not anime.get("banner_url")
    )
    sid = anime.get("source_id")
    if needs_enrich and sid and (anime.get("source") or "anilist") == "anilist":
        try:
            details = SOURCES["anilist"].get_details(int(sid), use_cache=True)
            patch = {}
            if not (anime.get("description") or "").strip() and details.get("description"):
                patch["description"] = details["description"]
            if not (anime.get("related_ids") or []) and details.get("related_ids"):
                patch["related_ids"] = [str(x) for x in details["related_ids"]]
                patch["relations"] = details.get("relations") or []
            if not anime.get("banner_url") and details.get("banner_url"):
                patch["banner_url"] = details["banner_url"]
            if details.get("status"):
                patch["status"] = details["status"]
            if details.get("airing_day") and not anime.get("airing_day"):
                patch["airing_day"] = details["airing_day"]
            if patch:
                try:
                    from helper.database import anime_col
                    import time as _time
                    anime_col.update_one(
                        {"_id": anime_id},
                        {"$set": {**patch, "updated_at": _time.time()}},
                    )
                except Exception:
                    pass
                anime.update(patch)
        except Exception as e:
            # Avoid flooding logs on repeated opens of the same broken source_id
            print(f"[detail] enrich failed for {anime_id} (source_id={sid}): {e}")

    anime["related_posted"] = _related_posted(anime)
    return jsonify(anime)


@app.get("/api/anilist/<int:anilist_id>")
def api_anilist_details(anilist_id):
    """Full details (genres/synopsis/banner) for a Trending/Popular card —
    the lightweight discovery query doesn't include those fields."""
    try:
        details = SOURCES["anilist"].get_details(anilist_id)
    except LookupError:
        abort(404)
    except (ValueError, requests.HTTPError) as e:
        msg = str(e)
        if "400" in msg or "404" in msg or "not found" in msg:
            abort(404)
        abort(502)
    except requests.RequestException:
        abort(502)
    except Exception:
        abort(502)
    # Match local library links for join buttons
    try:
        matched = db.find_by_source_id("anilist", str(anilist_id))
        if matched:
            details["id"] = matched.get("id")
            details["join_link"] = matched.get("join_link")
            details["ongoing_link"] = matched.get("ongoing_link")
            details["display_mode"] = matched.get("display_mode")
    except Exception:
        pass
    details["related_posted"] = _related_posted(details)
    return jsonify(details)


@app.post("/api/catalog/sync-ongoing")
def api_sync_ongoing():
    """Scan Finished library franchises for newly airing seasons and add them
    to MongoDB so they appear under Ongoing (with inherited finished link)."""
    user = current_user()
    # Allow any Telegram user to trigger a light sync; writes only create
    # airing siblings of already-posted titles.
    added = 0
    updated = 0
    checked = 0
    try:
        posts = [a for a in db.list_available() if a.get("join_link") or a.get("ongoing_link")]
    except Exception as e:
        return jsonify(error=str(e), added=0, updated=0), 500

    src = SOURCES.get("anilist")
    if not src:
        return jsonify(added=0, updated=0, checked=0)

    # Collect related ids from posted titles (limit work per request)
    candidate_ids = []
    seen = set()
    for a in posts:
        if (a.get("source") or "anilist") != "anilist":
            continue
        for rid in (a.get("related_ids") or [])[:12]:
            rid = str(rid)
            if rid in seen:
                continue
            seen.add(rid)
            candidate_ids.append((rid, a))
        if len(candidate_ids) >= 60:
            break

    MAX_FETCH = 15
    fetches = 0
    for rid, parent in candidate_ids:
        if fetches >= MAX_FETCH:
            break
        existing = db.find_by_source_id("anilist", rid)
        # Skip solo highlights — they manage their own lifecycle
        if existing and (existing.get("display_mode") or "group") == "solo":
            continue
        # If already in library and marked airing/hiatus with airing_day, skip fetch
        if existing:
            st = (existing.get("status") or "").upper()
            if st in ("RELEASING", "NOT_YET_RELEASED", "HIATUS") and existing.get("airing_day"):
                checked += 1
                continue
        try:
            details = src.get_details(int(rid), use_cache=True)
            fetches += 1
            checked += 1
        except Exception:
            continue
        st = (details.get("status") or "").upper()
        if st not in ("RELEASING", "NOT_YET_RELEASED", "HIATUS"):
            # Update status on existing finished-family members so they leave Ongoing
            if existing and (existing.get("status") or "").upper() != st:
                try:
                    from helper.database import anime_col
                    import time as _time
                    anime_col.update_one(
                        {"_id": existing["id"]},
                        {"$set": {"status": details.get("status"), "updated_at": _time.time()}},
                    )
                    updated += 1
                except Exception:
                    pass
            continue

        inherited = parent.get("join_link") or parent.get("ongoing_link")
        new_id = db.upsert_anime(details, added_by=(user or {}).get("id"))
        if inherited and not (existing or {}).get("join_link"):
            db.update_link(new_id, inherited)
        try:
            db.update_display_mode(new_id, "group")
        except Exception:
            pass
        if existing:
            updated += 1
        else:
            added += 1

    return jsonify(status="ok", added=added, updated=updated, checked=checked, fetched=fetches)


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
    """Set/clear independent links (all can coexist):

    - group_link   → All seasons (franchise shared finished URL → join_link)
    - solo_link    → Solo only for this title (own card + own URL → solo_link)
    - ongoing_link → Ongoing tab URL
    - legacy `link` + `display_mode` still accepted
    """
    user = current_user()
    if not is_admin(user):
        abort(403)
    payload = request.get_json(force=True, silent=True) or {}
    anime = db.get_anime(anime_id)
    if not anime:
        abort(404)

    has_group = "group_link" in payload or (
        "link" in payload and payload.get("display_mode") != "solo"
    )
    has_solo = "solo_link" in payload or (
        "link" in payload and payload.get("display_mode") == "solo"
    )
    has_ongoing = "ongoing_link" in payload

    # Resolve raw strings (None = field not sent; "" = explicit clear)
    if "group_link" in payload:
        raw_group = (payload.get("group_link") or "").strip()
    elif "link" in payload and (payload.get("display_mode") or "group") != "solo":
        raw_group = (payload.get("link") or "").strip()
    else:
        raw_group = None

    if "solo_link" in payload:
        raw_solo = (payload.get("solo_link") or "").strip()
    elif "link" in payload and payload.get("display_mode") == "solo":
        raw_solo = (payload.get("link") or "").strip()
    else:
        raw_solo = None

    raw_ongoing = (payload.get("ongoing_link") or "").strip() if has_ongoing else None

    try:
        group_link = normalize_join_link(raw_group) if raw_group else ("" if raw_group is not None else None)
        solo_link = normalize_join_link(raw_solo) if raw_solo else ("" if raw_solo is not None else None)
        ongoing_link = normalize_join_link(raw_ongoing) if raw_ongoing else ("" if has_ongoing else None)
    except ValueError as e:
        return jsonify(error=str(e)), 400

    existing_group = anime.get("join_link") or ""
    existing_solo = anime.get("solo_link") or ""
    existing_ongoing = anime.get("ongoing_link") or ""

    final_group = group_link if group_link is not None else existing_group
    final_solo = solo_link if solo_link is not None else existing_solo
    final_ongoing = ongoing_link if has_ongoing else existing_ongoing

    # Nothing left at all → remove from library
    if not final_group and not final_solo and not final_ongoing:
        # Prefer family delete only when we were clearing the franchise link
        if (anime.get("display_mode") or "group") == "solo" and not existing_group:
            db.delete_anime(anime_id)
            return jsonify(status="deleted", link="", solo_link="", ongoing_link="", propagated=0)
        propagated = db.delete_anime_family(anime_id)
        return jsonify(status="deleted", link="", solo_link="", ongoing_link="", propagated=propagated)

    propagated = 0

    # --- All seasons (group / join_link) — independent of solo_link ---
    if group_link is not None and group_link != "":
        db.update_link(anime_id, group_link)
        try:
            propagated = propagate_link_full_franchise(anime_id, group_link)
        except Exception as e:
            print(f"[link] full franchise expand failed: {e}")
            try:
                propagated = db.propagate_join_link(anime_id, group_link)
            except Exception:
                pass
        # Mark non-solo family members as group; leave titles that have solo_link alone
        try:
            import time as _time
            from helper.database import anime_col
            anime_col.update_many(
                {
                    "source": anime.get("source") or "anilist",
                    "join_link": group_link,
                    "$or": [
                        {"solo_link": {"$in": [None, ""]}},
                        {"solo_link": {"$exists": False}},
                    ],
                },
                {"$set": {"display_mode": "group", "updated_at": _time.time()}},
            )
        except Exception:
            pass
    elif group_link == "":
        # Clear franchise join_link on this title and non-solo family that shared it
        old = existing_group
        db.update_link(anime_id, None)
        if old:
            try:
                from helper.database import anime_col
                import time as _time
                anime_col.update_many(
                    {
                        "source": anime.get("source") or "anilist",
                        "join_link": old,
                        "$or": [
                            {"solo_link": {"$in": [None, ""]}},
                            {"solo_link": {"$exists": False}},
                        ],
                        "_id": {"$ne": anime_id},
                    },
                    {"$set": {"join_link": None, "updated_at": _time.time()}},
                )
            except Exception:
                pass

    # --- Solo (this title only) — independent of join_link ---
    if solo_link is not None and solo_link != "":
        db.update_solo_link(anime_id, solo_link)
        try:
            db.update_display_mode(anime_id, "solo")
        except Exception:
            pass
    elif solo_link == "":
        db.update_solo_link(anime_id, None)
        # Drop solo mode if no solo link left; keep group membership via join_link
        if final_group:
            try:
                db.update_display_mode(anime_id, "group")
            except Exception:
                pass
        else:
            try:
                db.update_display_mode(anime_id, "group")
            except Exception:
                pass

    # Keep display_mode in sync when only group was set and no solo remains
    if group_link is not None and group_link != "" and not final_solo:
        try:
            db.update_display_mode(anime_id, "group")
        except Exception:
            pass

    if has_ongoing:
        db.update_ongoing_link(anime_id, ongoing_link or None)
        # Share the same ongoing link across all other Ongoing posts
        try:
            propagated += db.propagate_ongoing_link(anime_id, ongoing_link or None)
        except Exception as e:
            print(f"[link] ongoing propagate failed: {e}")

    # Per-post toggle: show / hide the ONGOING button on this card
    if "ongoing_enabled" in payload:
        try:
            db.update_ongoing_enabled(anime_id, bool(payload.get("ongoing_enabled")))
        except Exception as e:
            print(f"[link] ongoing_enabled update failed: {e}")

    try:
        db.accept_requests_for_title((anime or {}).get("title") or "")
    except Exception:
        pass
    updated = db.get_anime(anime_id)
    if not updated:
        return jsonify(status="deleted", link="", solo_link="", ongoing_link="", propagated=propagated)
    return jsonify(
        status="updated",
        link=(updated or {}).get("join_link") or "",
        solo_link=(updated or {}).get("solo_link") or "",
        ongoing_link=(updated or {}).get("ongoing_link") or "",
        ongoing_enabled=(updated or {}).get("ongoing_enabled", True),
        propagated=propagated,
        anime=updated,
    )




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


@app.post("/api/admin/refresh-airing-days")
def api_refresh_airing_days():
    """Pull airing_day + status from AniList for posted titles.

    Used by the mini-app Ongoing tab (silent auto-fill). Any authenticated
    user may call it. Always refreshes status so RELEASING / HIATUS /
    NOT_YET_RELEASED titles are not stuck as FINISHED (or blank) and
    therefore hidden from Ongoing.
    """
    user = current_user()
    if not user:
        abort(401)
    payload = request.get_json(force=True, silent=True) or {}
    force = bool(payload.get("force"))

    all_posts = db.list_available()
    candidates = []
    for a in all_posts:
        sid = a.get("source_id")
        if not sid:
            continue
        # source may be missing on very old rows — still try AniList
        st = (a.get("status") or "").upper()
        has_day = bool(a.get("airing_day"))
        if not force:
            # Prefer titles that look ongoing-or-unknown and are missing a day,
            # or have no/blank status so they can be corrected.
            if has_day and st in ("RELEASING", "NOT_YET_RELEASED", "HIATUS"):
                continue
            # Skip clearly finished only when we already have a day and
            # status — still allow status correction when status is blank
            # or day is missing.
            if st in ("FINISHED", "CANCELLED") and has_day:
                continue
        candidates.append(a)

    # Cap work per request to avoid AniList rate limits on large libraries.
    # Prefer titles that look like they should be on Ongoing (blank status,
    # RELEASING/HIATUS, or have an ongoing_link) so the first refresh fixes
    # the most important rows.
    def _prio(a):
        st = (a.get("status") or "").upper()
        score = 0
        if a.get("ongoing_link"):
            score += 4
        if st in ("RELEASING", "HIATUS", ""):
            score += 3
        if not a.get("airing_day"):
            score += 1
        if st in ("FINISHED", "CANCELLED"):
            score -= 2
        return -score

    candidates.sort(key=_prio)
    MAX_FETCH = 80 if force else 30
    candidates = candidates[:MAX_FETCH]

    updated = 0
    status_updated = 0
    failed = 0
    skipped = 0
    results = []
    src = SOURCES.get("anilist")
    if not src:
        return jsonify(error="AniList source unavailable"), 502

    for a in candidates:
        try:
            details = src.get_details(a["source_id"], use_cache=False)
            day = (details.get("airing_day") or "").strip().lower() or None
            old_status = (a.get("status") or "").upper()
            new_status = (details.get("status") or "").upper()

            # Always refresh status/metadata so Ongoing filters stay accurate
            try:
                db.upsert_anime(details)
                if new_status and new_status != old_status:
                    status_updated += 1
            except Exception:
                pass

            if day:
                db.update_airing_day(a["id"], day)
                updated += 1
                results.append({
                    "id": a["id"],
                    "title": a.get("title"),
                    "day": day,
                    "status": details.get("status"),
                })
            else:
                skipped += 1
                if new_status and new_status != old_status:
                    results.append({
                        "id": a["id"],
                        "title": a.get("title"),
                        "day": None,
                        "status": details.get("status"),
                    })
        except Exception:
            failed += 1

    return jsonify(
        status="ok",
        updated=updated,
        status_updated=status_updated,
        skipped=skipped,
        failed=failed,
        total_candidates=len(candidates),
        results=results[:50],
    )


@app.post("/api/anime/link-anilist/<int:anilist_id>")
def api_set_link_from_anilist(anilist_id):
    """Create library entry from AniList with separate group/solo/ongoing links."""
    user = current_user()
    if not is_admin(user):
        abort(403)
    payload = request.get_json(force=True, silent=True) or {}
    raw_group = (payload.get("group_link") or payload.get("link") or "").strip()
    raw_solo = (payload.get("solo_link") or "").strip()
    raw_ongoing = (payload.get("ongoing_link") or "").strip()
    if not raw_group and not raw_solo and not raw_ongoing:
        return jsonify(error="An All seasons, Solo, or Ongoing join link is required."), 400
    try:
        group_link = normalize_join_link(raw_group) if raw_group else ""
        solo_link = normalize_join_link(raw_solo) if raw_solo else ""
        ongoing_link = normalize_join_link(raw_ongoing) if raw_ongoing else ""
    except ValueError as e:
        return jsonify(error=str(e)), 400

    details = None
    try:
        details = SOURCES["anilist"].get_details(anilist_id, use_cache=True)
    except Exception as e:
        print(f"[link-anilist] details fetch failed for {anilist_id}: {e}")

    if not details or not details.get("title"):
        details = {
            "source": "anilist",
            "source_id": anilist_id,
            "title": (payload.get("title") or f"AniList #{anilist_id}").strip(),
            "alt_title": (payload.get("alt_title") or None),
            "year": payload.get("year"),
            "poster_url": payload.get("poster_url"),
            "banner_url": payload.get("banner_url"),
            "description": payload.get("description"),
            "genres": payload.get("genres") or [],
            "rating": payload.get("rating"),
            "status": payload.get("status") or "FINISHED",
            "episodes": payload.get("episodes"),
            "format": payload.get("format"),
            "related_ids": [],
            "relations": [],
        }

    details["source"] = details.get("source") or "anilist"
    details["source_id"] = details.get("source_id") or anilist_id

    anime_id = db.upsert_anime(details, added_by=user["id"])
    propagated = 0

    # All seasons + Solo are independent fields — both may be set at once.
    if group_link:
        db.update_link(anime_id, group_link)
        try:
            propagated = propagate_link_full_franchise(anime_id, group_link)
        except Exception as e:
            print(f"[link-anilist] full franchise expand failed: {e}")
            try:
                propagated = db.propagate_join_link(anime_id, group_link)
            except Exception:
                pass

    if solo_link:
        db.update_solo_link(anime_id, solo_link)
        try:
            db.update_display_mode(anime_id, "solo")
        except Exception:
            pass
    elif group_link:
        try:
            db.update_display_mode(anime_id, "group")
        except Exception:
            pass

    if ongoing_link:
        db.update_ongoing_link(anime_id, ongoing_link)
        try:
            propagated += db.propagate_ongoing_link(anime_id, ongoing_link)
        except Exception as e:
            print(f"[link-anilist] ongoing propagate failed: {e}")

    if "ongoing_enabled" in payload:
        try:
            db.update_ongoing_enabled(anime_id, bool(payload.get("ongoing_enabled")))
        except Exception:
            pass

    try:
        db.accept_requests_for_title(details.get("title") or "")
    except Exception:
        pass

    anime = db.get_anime(anime_id)
    return jsonify(status="updated", anime=anime, propagated=propagated)


