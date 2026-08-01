.....#"""
Permanent Link Share Menu.

- Settings -> Link Share Menu
- Normal Links and Request Links are displayed as channel-name buttons.
- Link Share records are persisted in MongoDB.
- Links are permanent (no expiry).
- This feature is separate from File Store persistence.
"""

import os
import secrets
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import RPCError

try:
    from bot import db
except Exception:
    db = None

OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)

def _admins():
    raw = os.getenv("ADMINS", "") or os.getenv("ADMIN_IDS", "")
    ids = set()
    for x in raw.replace(",", " ").split():
        try:
            ids.add(int(x))
        except ValueError:
            pass
    if OWNER_ID:
        ids.add(OWNER_ID)
    return ids

def _collection():
    if db is None:
        return None
    # Reuse a Mongo collection exposed by common DB wrappers, otherwise create one.
    for attr in ("link_share", "linkshare", "link_share_collection"):
        obj = getattr(db, attr, None)
        if obj is not None:
            return obj
    # Motor/PyMongo database wrappers commonly expose .database or .db.
    mongo_db = getattr(db, "database", None) or getattr(db, "db", None)
    if mongo_db is not None:
        try:
            return mongo_db["link_share"]
        except Exception:
            pass
    return None

def _token():
    return secrets.token_urlsafe(16).replace("-", "").replace("_", "")

async def _save_link(chat_id: int, title: str, kind: str, bot_username: str):
    col = _collection()
    if col is None:
        return None
    doc = await col.find_one({"chat_id": chat_id, "kind": kind})
    if doc and doc.get("token"):
        return doc["token"]
    token = _token()
    await col.update_one(
        {"chat_id": chat_id, "kind": kind},
        {"$set": {"chat_id": chat_id, "title": title, "kind": kind, "token": token}},
        upsert=True,
    )
    return token

async def _channels():
    col = _collection()
    if col is None:
        return []
    out = []
    async for doc in col.find({}).sort("title", 1):
        out.append(doc)
    return out

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Channel", callback_data="ls_add")],
        [InlineKeyboardButton("🗑 Delete Channel", callback_data="ls_del")],
        [InlineKeyboardButton("🔗 Normal Links", callback_data="ls_normal")],
        [InlineKeyboardButton("📥 Request Links", callback_data="ls_request")],
        [InlineKeyboardButton("📋 List Channels", callback_data="ls_list")],
        [InlineKeyboardButton("🔙 Back", callback_data="ls_back")],
    ])

def _link_button(doc, bot_username):
    kind = doc.get("kind")
    label = f"🔗 {doc.get('title', 'Channel')}"
    url = f"https://t.me/{bot_username}?start=ls_{doc.get('token')}"
    return InlineKeyboardButton(label, url=url)

@Client.on_callback_query(filters.regex("^ls_menu$"))
async def link_share_menu(client, query: CallbackQuery):
    if query.from_user.id not in _admins():
        return await query.answer("Admin only.", show_alert=True)
    await query.message.edit_text("🔗 **Link Share Menu**\n\nSelect an option:", reply_markup=menu())

@Client.on_callback_query(filters.regex("^ls_normal$|^ls_request$"))
async def link_list(client, query: CallbackQuery):
    if query.from_user.id not in _admins():
        return await query.answer("Admin only.", show_alert=True)
    kind = "normal" if query.data == "ls_normal" else "request"
    docs = []
    for d in await _channels():
        if d.get("kind") == kind:
            docs.append(d)
    me = await client.get_me()
    rows = [[_link_button(d, me.username)] for d in docs]
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="ls_menu")])
    title = "🔗 **Normal Links**" if kind == "normal" else "📥 **Request Links**"
    await query.message.edit_text(
        f"{title}\n\nSelect a channel:",
        reply_markup=InlineKeyboardMarkup(rows),
    )

@Client.on_callback_query(filters.regex("^ls_list$"))
async def list_channels(client, query: CallbackQuery):
    if query.from_user.id not in _admins():
        return await query.answer("Admin only.", show_alert=True)
    docs = await _channels()
    if not docs:
        text = "📋 **List Channels**\n\nNo Link Share channels configured."
    else:
        lines = []
        for d in docs:
            lines.append(f"• {d.get('title', 'Unknown')} — {d.get('kind', 'unknown').title()}")
        text = "📋 **List Channels**\n\n" + "\n".join(lines)
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="ls_menu")]
    ]))

# The Add/Delete flows are intentionally left to the target bot's existing
# channel-management handlers if present; this module only provides the
# permanent MongoDB-backed link menu and display.
