"""
Anime Index bot handlers (Touka integrated into NexusV2).

Same bot token as the file-store. Commands:
  /anidex              — welcome + Open Mini App button
  plain text (private) — search Available library
Callbacks:
  searchpick / cancel
  reqaccept / reqreject / reqreason / reqback
"""

from __future__ import annotations

import asyncio
import secrets
import threading
import time
from urllib.parse import quote

import requests
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)

from config import (
    Config,
    TOKEN,
    BRAND_NAME,
    WEBAPP_URL,
    BANNER_IMAGE_URL,
    INDEX_MSG,
    ADMINS,
    MESSAGES,
)
from helper import database as db

SESSIONS: dict[str, dict] = {}
SESSION_TTL = 15 * 60

REJECT_REASONS = {
    "dup": "This title is already posted — check the library.",
    "unavailable": "This title isn't available right now.",
    "unreleased": "This title hasn't been released yet.",
    "other": "Sorry, we're not able to add this title right now.",
}

# Commands that must NOT be treated as anime title search
_BOT_COMMANDS = {
    "start", "anidex", "shortner", "users", "broadcast", "batch", "genlink",
    "usage", "pbroadcast", "ban", "unban", "addpremium", "delpremium",
    "premiumusers", "request", "profile", "db", "adddb", "removedb",
    "settings", "help", "about", "commands",
}


def _gc_sessions() -> None:
    now = time.time()
    expired = [k for k, v in SESSIONS.items() if now - v.get("_created", now) > SESSION_TTL]
    for k in expired:
        SESSIONS.pop(k, None)


def new_session(**kwargs) -> str:
    sid = secrets.token_hex(4)
    kwargs["_created"] = time.time()
    SESSIONS[sid] = kwargs
    _gc_sessions()
    return sid


def _webapp_button(label: str | None = None) -> InlineKeyboardButton:
    """/anidex — open the Anime Index mini app."""
    label = label or "🟢 ᴏᴘᴇɴ ɪɴᴅᴇx 🟢"
    if WEBAPP_URL.startswith("https://"):
        return InlineKeyboardButton(label, web_app=WebAppInfo(url=WEBAPP_URL))
    return InlineKeyboardButton(label, url=WEBAPP_URL or "https://telegram.org")


def _open_post_button(anime: dict) -> InlineKeyboardButton | None:
    """Available titles: direct join_link only — never the mini app."""
    join = (anime.get("join_link") or "").strip()
    if join.startswith("http://") or join.startswith("https://"):
        return InlineKeyboardButton("🟢 ᴄʟɪᴄᴋ 🟢", url=join)
    return None


def _search_in_app_button(text: str) -> InlineKeyboardButton:
    """Not available — open mini app Search to request it."""
    label = "🟢 ᴏᴘᴇɴ 🟢"
    if WEBAPP_URL.startswith("https://"):
        url = f"{WEBAPP_URL}?search={quote(text)}"
        return InlineKeyboardButton(label, web_app=WebAppInfo(url=url))
    return InlineKeyboardButton(label, url=WEBAPP_URL or "https://telegram.org")


async def _send_anime_result(
    message: Message,
    anime: dict,
    reply_markup: InlineKeyboardMarkup,
    client: Client | None = None,
    chat_id: int | None = None,
):
    """Send poster image when available, otherwise plain title text."""
    title = anime.get("title") or "Anime"
    custom = ""
    if client is not None:
        custom = (getattr(client, "messages", {}) or {}).get("SEARCH_PHOTO") or ""
    if not custom:
        custom = (MESSAGES.get("SEARCH_PHOTO") or "").strip()
    custom = (custom or "").strip()
    if custom:
        poster = custom
    else:
        poster = (anime.get("poster_url") or "").strip()
    target = chat_id or (message.chat.id if message and message.chat else None)
    kwargs = dict(reply_markup=reply_markup, protect_content=True)
    if poster:
        try:
            if client and target is not None:
                return await client.send_photo(target, poster, caption=title, **kwargs)
            return await message.reply_photo(poster, caption=title, **kwargs)
        except Exception:
            pass
    if client and target is not None:
        return await client.send_message(target, title, **kwargs)
    return await message.reply_text(title, **kwargs)


def _delete_message_later(chat_id: int, message_id: int, delay: float = 120) -> None:
    def _do() -> None:
        try:
            token = TOKEN or getattr(Config, "BOT_TOKEN", "")
            if not token:
                return
            requests.post(
                f"https://api.telegram.org/bot{token}/deleteMessage",
                json={"chat_id": chat_id, "message_id": message_id},
                timeout=10,
            )
        except Exception:
            pass

    threading.Timer(delay, _do).start()


def _display_name(user) -> str:
    if getattr(user, "username", None):
        return f"@{user.username}"
    return getattr(user, "first_name", None) or str(user.id)


# ---------------------------------------------------------------------------
# /anidex
# ---------------------------------------------------------------------------

@Client.on_message(filters.command("anidex") & filters.private)
async def cmd_anidex(client: Client, message: Message):
    msgs = getattr(client, "messages", None) or {}
    raw = msgs.get("INDEX") or INDEX_MSG
    try:
        text = raw.format(
            first_name=(message.from_user.first_name if message.from_user else None) or "there",
            brand_name=BRAND_NAME,
        )
    except (KeyError, IndexError, ValueError):
        text = raw
    kb = InlineKeyboardMarkup([[_webapp_button()]])
    photo = (msgs.get("INDEX_PHOTO") or BANNER_IMAGE_URL or "").strip()
    if photo:
        sent = await message.reply_photo(
            photo, caption=text, reply_markup=kb, protect_content=True,
        )
    else:
        sent = await message.reply_text(
            text, reply_markup=kb, protect_content=True,
        )
    _delete_message_later(sent.chat.id, sent.id)


# ---------------------------------------------------------------------------
# Plain-text library search (private only)
# ---------------------------------------------------------------------------

@Client.on_message(
    filters.private
    & filters.text
    & ~filters.command(list(_BOT_COMMANDS))
)
async def on_text_search(client: Client, message: Message):
    text = (message.text or "").strip()
    if len(text) < 2 or len(text) > 80:
        return
    # Skip file-store / link-share deep-link style payloads
    if text.startswith(("yu3elk", "ls_")):
        return
    # Don't treat URLs, pure IDs, or command-like text as anime titles
    # (avoids clashing with admin settings input / channel IDs)
    lower = text.lower()
    if lower.startswith(("http://", "https://", "t.me/", "tg://")):
        return
    if text.lstrip("-").isdigit():
        return
    if text.startswith(("/", "@")):
        return

    try:
        local_matches = await asyncio.to_thread(db.search_local, text)
    except Exception:
        return

    if not local_matches:
        kb = InlineKeyboardMarkup([[_search_in_app_button(text)]])
        sent = await message.reply_text(
            f"'{text}' isn't posted yet. Open {BRAND_NAME} to search and request it.",
            reply_markup=kb,
            protect_content=True,
        )
        _delete_message_later(sent.chat.id, sent.id)
        return

    if len(local_matches) == 1:
        anime = local_matches[0]
        btn = _open_post_button(anime)
        if btn:
            # Available: title + direct link only (no poster)
            sent = await message.reply_text(
                anime.get("title") or text,
                reply_markup=InlineKeyboardMarkup([[btn]]),
                protect_content=True,
            )
        else:
            # Not fully linked — open mini app (optional custom/search photo)
            btn = _search_in_app_button(anime.get("title") or text)
            sent = await _send_anime_result(
                message, anime, InlineKeyboardMarkup([[btn]]), client=client,
            )
        _delete_message_later(sent.chat.id, sent.id)
        return

    matches = local_matches[:8]
    sid = new_session(kind="searchpick", matches=matches)
    rows = [
        [InlineKeyboardButton(f"🟢 {m['title']}", callback_data=f"searchpick:{sid}:{i}")]
        for i, m in enumerate(matches)
    ]
    rows.append([InlineKeyboardButton("🔴 Cancel", callback_data=f"cancel:{sid}")])
    kb = InlineKeyboardMarkup(rows)
    caption = f"Found {len(local_matches)} matches for '{text}':"
    sent = await message.reply_text(
        caption, reply_markup=kb, protect_content=True,
    )
    _delete_message_later(sent.chat.id, sent.id)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@Client.on_callback_query(
    filters.regex(r"^(searchpick|cancel|reqaccept|reqreject|reqreason|reqback):")
)
async def on_anime_callback(client: Client, q: CallbackQuery):
    data = q.data or ""
    parts = data.split(":")
    action = parts[0]

    if action == "cancel":
        sid = parts[1] if len(parts) > 1 else None
        SESSIONS.pop(sid, None)
        await q.answer("Cancelled")
        try:
            await q.message.edit_text("Cancelled.")
        except Exception:
            pass
        return

    if action == "searchpick":
        if len(parts) < 3:
            await q.answer()
            return
        sid, idx_s = parts[1], parts[2]
        session = SESSIONS.get(sid)
        if not session:
            await q.answer("Session expired — search again.", show_alert=True)
            return
        try:
            match = session["matches"][int(idx_s)]
        except (IndexError, ValueError, KeyError):
            await q.answer()
            return
        SESSIONS.pop(sid, None)
        await q.answer()
        try:
            btn = _open_post_button(match)
            chat_id = q.message.chat.id if q.message and q.message.chat else q.from_user.id
            try:
                await q.message.delete()
            except Exception:
                pass
            if btn:
                # Available: title + direct link only (no poster)
                sent = await client.send_message(
                    chat_id,
                    match.get("title") or "Anime",
                    reply_markup=InlineKeyboardMarkup([[btn]]),
                    protect_content=True,
                )
            else:
                btn = _search_in_app_button(match.get("title") or "")
                sent = await _send_anime_result(
                    q.message, match, InlineKeyboardMarkup([[btn]]),
                    client=client, chat_id=chat_id,
                )
            _delete_message_later(sent.chat.id, sent.id)
        except Exception:
            pass
        return

    # Admin-only request actions
    if not q.from_user or q.from_user.id not in ADMINS:
        await q.answer("Admins only.", show_alert=True)
        return

    if action == "reqaccept":
        try:
            request_id = int(parts[1])
        except (IndexError, ValueError):
            await q.answer()
            return
        updated = await asyncio.to_thread(db.resolve_request_by_id, request_id, "accepted")
        if updated is None:
            await q.answer("Already handled.", show_alert=True)
            return
        await q.answer("Accepted \u2705")
        label = f"\n\n\u2705 Accepted by {_display_name(q.from_user)}"
        try:
            if q.message.caption is not None:
                await q.message.edit_caption((q.message.caption or "") + label)
            else:
                await q.message.edit_text((q.message.text or "") + label)
        except Exception:
            pass
        return

    if action == "reqreject":
        rid = parts[1] if len(parts) > 1 else ""
        await q.answer()
        rows = [
            [InlineKeyboardButton("🔵 Already posted", callback_data=f"reqreason:{rid}:dup")],
            [InlineKeyboardButton("🔵 Not available", callback_data=f"reqreason:{rid}:unavailable")],
            [InlineKeyboardButton("🔵 Not release yet", callback_data=f"reqreason:{rid}:unreleased")],
            [InlineKeyboardButton("🔵 Other", callback_data=f"reqreason:{rid}:other")],
            [InlineKeyboardButton("🔴 \u2190 Back", callback_data=f"reqback:{rid}")],
        ]
        try:
            await q.message.edit_reply_markup(InlineKeyboardMarkup(rows))
        except Exception:
            pass
        return

    if action == "reqback":
        rid = parts[1] if len(parts) > 1 else ""
        await q.answer()
        rows = [[
            InlineKeyboardButton("🟢 \u2705 Accept", callback_data=f"reqaccept:{rid}"),
            InlineKeyboardButton("🔴 \u274c Reject", callback_data=f"reqreject:{rid}"),
        ]]
        try:
            await q.message.edit_reply_markup(InlineKeyboardMarkup(rows))
        except Exception:
            pass
        return

    if action == "reqreason":
        try:
            request_id = int(parts[1])
            reason_code = parts[2] if len(parts) > 2 else "other"
        except (IndexError, ValueError):
            await q.answer()
            return
        note = REJECT_REASONS.get(reason_code, REJECT_REASONS["other"])
        updated = await asyncio.to_thread(
            db.resolve_request_by_id, request_id, "rejected", note
        )
        if updated is None:
            await q.answer("Already handled.", show_alert=True)
            return
        await q.answer("Rejected \u274c")
        label = f"\n\n\u274c Rejected by {_display_name(q.from_user)} \u2014 {note}"
        try:
            if q.message.caption is not None:
                await q.message.edit_caption((q.message.caption or "") + label)
            else:
                await q.message.edit_text((q.message.text or "") + label)
        except Exception:
            pass
        return
