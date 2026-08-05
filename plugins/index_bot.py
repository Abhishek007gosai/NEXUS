"""
Anime Index features on Pyrogram:
  /anidex  — welcome + Open Mini App button
  plain text (private) — search Available library
  callback reqaccept / reqreject / reqreason / reqback — admin request queue
"""
import asyncio
import re
import threading
import time
from urllib.parse import quote

import requests
from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
)

from config import Config, BRAND_NAME, WEBAPP_URL, ADMIN_IDS, LOG_CHANNEL_ID, BOT_TOKEN
from helper import catalog_db as db

SESSIONS: dict[str, dict] = {}
SESSION_TTL = 15 * 60


def _gc_sessions():
    now = time.time()
    for k in [k for k, v in SESSIONS.items() if now - v.get("_created", now) > SESSION_TTL]:
        SESSIONS.pop(k, None)


def _new_session(**kwargs) -> str:
    import secrets
    sid = secrets.token_hex(4)
    kwargs["_created"] = time.time()
    SESSIONS[sid] = kwargs
    _gc_sessions()
    return sid


def _webapp_url(path_query: str = "") -> str:
    base = (WEBAPP_URL or Config.WEBAPP_URL or "").rstrip("/")
    if not base:
        return "https://telegram.org"
    if path_query:
        return f"{base}{path_query}" if path_query.startswith("?") else f"{base}/{path_query}"
    return base


def _open_webapp_button(label: str = None, url: str = None):
    label = label or f"Open {BRAND_NAME}"
    target = url or _webapp_url()
    if target.startswith("https://"):
        return InlineKeyboardButton(label, web_app=WebAppInfo(url=target))
    return InlineKeyboardButton(label, url=target)


def _delete_later(client: Client, chat_id: int, message_id: int, delay: float = 120):
    def _do():
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                json={"chat_id": chat_id, "message_id": message_id},
                timeout=10,
            )
        except Exception:
            pass
    threading.Timer(delay, _do).start()


# ---------------------------------------------------------------------------
# /anidex
# ---------------------------------------------------------------------------
@Client.on_message(filters.command("anidex") & filters.private)
async def cmd_anidex(client: Client, message: Message):
    user = message.from_user
    try:
        text = Config.START_MSG.format(first_name=user.first_name or "", brand_name=BRAND_NAME)
    except Exception:
        text = Config.START_MSG
    kb = InlineKeyboardMarkup([[_open_webapp_button()]])
    banner = Config.BANNER_IMAGE_URL
    if banner:
        await message.reply_photo(banner, caption=text, reply_markup=kb)
    else:
        await message.reply_text(text, reply_markup=kb)


# ---------------------------------------------------------------------------
# Plain-text library search (private only, not commands)
# ---------------------------------------------------------------------------
@Client.on_message(filters.private & filters.text & ~filters.command([
    "start", "anidex", "shortner", "users", "broadcast", "batch", "genlink",
    "usage", "pbroadcast", "ban", "unban", "addpremium", "delpremium",
    "premiumusers", "request", "profile", "db", "adddb", "removedb", "settings",
]))
async def on_text_search(client: Client, message: Message):
    text = (message.text or "").strip()
    if len(text) < 2:
        return
    # Skip if looks like a deep-link payload already handled by start
    if text.startswith("/"):
        return

    local_matches = await asyncio.to_thread(db.search_local, text)
    if not local_matches:
        kb = InlineKeyboardMarkup([[
            _open_webapp_button(
                f"Open {BRAND_NAME}",
                _webapp_url(f"?search={quote(text)}"),
            )
        ]])
        sent = await message.reply_text(
            f"'{text}' isn't posted yet. Open {BRAND_NAME} to search and request it.",
            reply_markup=kb,
        )
        _delete_later(client, sent.chat.id, sent.id)
        return

    if len(local_matches) == 1:
        anime = local_matches[0]
        url = _webapp_url(f"?anime={anime['id']}")
        sent = await message.reply_text(
            anime["title"],
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Open Post", web_app=WebAppInfo(url=url))
                if url.startswith("https://") else
                InlineKeyboardButton("Open Post", url=url)
            ]]),
        )
        _delete_later(client, sent.chat.id, sent.id)
        return

    sid = _new_session(kind="searchpick", matches=local_matches[:8])
    rows = [
        [InlineKeyboardButton(m["title"], callback_data=f"searchpick:{sid}:{i}")]
        for i, m in enumerate(local_matches[:8])
    ]
    rows.append([InlineKeyboardButton("Cancel", callback_data=f"cancel:{sid}")])
    sent = await message.reply_text(
        f"Found {len(local_matches)} matches for '{text}':",
        reply_markup=InlineKeyboardMarkup(rows),
    )
    _delete_later(client, sent.chat.id, sent.id)


@Client.on_callback_query(filters.regex(r"^searchpick:"))
async def on_searchpick(client: Client, query: CallbackQuery):
    parts = (query.data or "").split(":")
    if len(parts) < 3:
        return await query.answer()
    sid, idx = parts[1], int(parts[2])
    session = SESSIONS.get(sid)
    if not session:
        return await query.answer("Session expired — search again.", show_alert=True)
    match = session["matches"][idx]
    SESSIONS.pop(sid, None)
    await query.answer()
    url = _webapp_url(f"?anime={match['id']}")
    btn = (
        InlineKeyboardButton("Open Post", web_app=WebAppInfo(url=url))
        if url.startswith("https://")
        else InlineKeyboardButton("Open Post", url=url)
    )
    await query.edit_message_text(match["title"], reply_markup=InlineKeyboardMarkup([[btn]]))


@Client.on_callback_query(filters.regex(r"^cancel:"))
async def on_cancel(client: Client, query: CallbackQuery):
    parts = (query.data or "").split(":")
    if len(parts) > 1:
        SESSIONS.pop(parts[1], None)
    await query.answer("Cancelled")
    await query.edit_message_text("Cancelled.")


# ---------------------------------------------------------------------------
# Request Accept / Reject (log channel)
# ---------------------------------------------------------------------------
REJECT_REASONS = {
    "dup": "This title is already posted — check the library.",
    "unavailable": "This title isn't available right now.",
    "unreleased": "This title hasn't been released yet.",
    "other": "Sorry, we're not able to add this title right now.",
}


def _is_admin(uid: int) -> bool:
    return uid in (ADMIN_IDS or [])


@Client.on_callback_query(filters.regex(r"^reqaccept:"))
async def on_req_accept(client: Client, query: CallbackQuery):
    if not _is_admin(query.from_user.id):
        return await query.answer("Admins only.", show_alert=True)
    rid = (query.data or "").split(":")[1]
    try:
        request_id = int(rid)
    except ValueError:
        return await query.answer()
    updated = await asyncio.to_thread(db.resolve_request_by_id, request_id, "accepted")
    if updated is None:
        return await query.answer("Already handled.", show_alert=True)
    await query.answer("Accepted")
    name = query.from_user.username or query.from_user.first_name or str(query.from_user.id)
    label = f"\n\nAccepted by @{name}" if query.from_user.username else f"\n\nAccepted by {name}"
    try:
        if query.message.caption is not None:
            await query.edit_message_caption(caption=(query.message.caption or "") + label)
        else:
            await query.edit_message_text((query.message.text or "") + label)
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^reqreject:"))
async def on_req_reject_menu(client: Client, query: CallbackQuery):
    if not _is_admin(query.from_user.id):
        return await query.answer("Admins only.", show_alert=True)
    rid = (query.data or "").split(":")[1]
    await query.answer()
    rows = [
        [InlineKeyboardButton("Already posted", callback_data=f"reqreason:{rid}:dup")],
        [InlineKeyboardButton("Not available", callback_data=f"reqreason:{rid}:unavailable")],
        [InlineKeyboardButton("Not released yet", callback_data=f"reqreason:{rid}:unreleased")],
        [InlineKeyboardButton("Other", callback_data=f"reqreason:{rid}:other")],
        [InlineKeyboardButton("Back", callback_data=f"reqback:{rid}")],
    ]
    try:
        await query.edit_message_reply_markup(InlineKeyboardMarkup(rows))
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^reqback:"))
async def on_req_back(client: Client, query: CallbackQuery):
    if not _is_admin(query.from_user.id):
        return await query.answer("Admins only.", show_alert=True)
    rid = (query.data or "").split(":")[1]
    await query.answer()
    rows = [[
        InlineKeyboardButton("Accept", callback_data=f"reqaccept:{rid}"),
        InlineKeyboardButton("Reject", callback_data=f"reqreject:{rid}"),
    ]]
    try:
        await query.edit_message_reply_markup(InlineKeyboardMarkup(rows))
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^reqreason:"))
async def on_req_reason(client: Client, query: CallbackQuery):
    if not _is_admin(query.from_user.id):
        return await query.answer("Admins only.", show_alert=True)
    parts = (query.data or "").split(":")
    if len(parts) < 3:
        return await query.answer()
    try:
        request_id = int(parts[1])
    except ValueError:
        return await query.answer()
    note = REJECT_REASONS.get(parts[2], REJECT_REASONS["other"])
    updated = await asyncio.to_thread(db.resolve_request_by_id, request_id, "rejected", note)
    if updated is None:
        return await query.answer("Already handled.", show_alert=True)
    await query.answer("Rejected")
    name = query.from_user.username or query.from_user.first_name or str(query.from_user.id)
    label = f"\n\nRejected by {name} — {note}"
    try:
        if query.message.caption is not None:
            await query.edit_message_caption(caption=(query.message.caption or "") + label)
        else:
            await query.edit_message_text((query.message.text or "") + label)
    except Exception:
        pass
