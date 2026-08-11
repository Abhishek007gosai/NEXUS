import re
import secrets
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError, UserNotParticipant
from helper.helper_func import encode, styled_button, safe_edit_text, safe_edit_caption, safe_edit_reply_markup
from config import OWNER_ID

LINK_SHARE_PREFIX = "ls_"
LINK_SHARE_PAGE_SIZE = 6


def is_admin(client, user_id):
    return user_id == OWNER_ID or user_id in client.admins


def _parse_expires_at(value):
    """Normalize expires_at from DB (datetime | iso str | None) → datetime | None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None
    return None


def _is_expired(expires_at) -> bool:
    exp = _parse_expires_at(expires_at)
    if exp is None:
        return False
    return datetime.utcnow() > exp


async def _resolve_token_ttl(client) -> int:
    """Effective TTL in minutes from DB (0 = never expire)."""
    try:
        ttl = await client.linkshare_db.get_link_share_token_ttl()
        if ttl is not None:
            return max(0, int(ttl))
    except Exception:
        pass
    return 0


async def _compute_expires_at(client):
    """Return expires_at datetime or None (never) based on configured TTL."""
    ttl = await _resolve_token_ttl(client)
    if ttl <= 0:
        return None
    return datetime.utcnow() + timedelta(minutes=ttl)


def _format_expires(expires_at) -> str:
    exp = _parse_expires_at(expires_at)
    if exp is None:
        return "Never"
    if _is_expired(exp):
        return f"Expired ({exp.strftime('%Y-%m-%d %H:%M')} UTC)"
    remaining = exp - datetime.utcnow()
    mins = int(remaining.total_seconds() // 60)
    if mins < 60:
        left = f"{mins}m left"
    elif mins < 1440:
        left = f"{mins // 60}h {mins % 60}m left"
    else:
        left = f"{mins // 1440}d left"
    return f"{exp.strftime('%Y-%m-%d %H:%M')} UTC ({left})"


async def _edit_query_message(query, text, **kwargs):
    """Edit either a normal text message or the photo-based Link Share screen."""
    if query.message.photo:
        return await safe_edit_caption(query.message, text, **kwargs)
    return await safe_edit_text(query.message, text, **kwargs)


async def _show_link_share_home(client, query):
    """Render the Link Share home screen in the Kafka-style layout."""
    buttons = [
        [styled_button("ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", style="primary", callback_data="ls_add"),
         styled_button("ᴅᴇʟᴇᴛᴇ ᴄʜᴀɴɴᴇʟ", style="primary", callback_data="ls_delete")],
        [styled_button("ɴᴏʀᴍᴀʟ", style="primary", callback_data="ls_normal"),
         styled_button("ʀᴇǫᴜᴇsᴛ", style="primary", callback_data="ls_request")],
        [styled_button("ᴄʜᴀɴɴᴇʟs ʟɪsᴛ", style="primary", callback_data="ls_list")],
        [styled_button("ʙᴀᴄᴋ", style="primary", callback_data="settings")]
    ]
    markup = InlineKeyboardMarkup(buttons)
    caption = (
        "<b>ʟɪɴᴋ sʜᴀʀᴇ ᴍᴇɴᴜ</b>\n\n"
        "<blockquote>In this you can change and view your channels...!!</blockquote>"
    )
    photo = getattr(client, "messages", {}).get("START_PHOTO")
    try:
        if query.message.photo:
            await safe_edit_caption(query.message, caption, reply_markup=markup)
        elif photo:
            await query.message.delete()
            await client.send_photo(
                chat_id=query.message.chat.id,
                photo=photo,
                caption=caption,
                reply_markup=markup
            )
        else:
            await _edit_query_message(query, caption, reply_markup=markup)
    except Exception as e:
        client.LOGGER(__name__, client.name).warning(f"Link Share home render failed: {e}")
        try:
            await _edit_query_message(query, caption, reply_markup=markup)
        except Exception:
            pass


@Client.on_callback_query(filters.regex(r"^link_share$"))
async def link_share_menu(client, query):
    if not is_admin(client, query.from_user.id):
        return await query.answer("Only admins can access this!", show_alert=True)
    await query.answer()
    await _show_link_share_home(client, query)


@Client.on_callback_query(filters.regex(r"^ls_add$"))
async def link_share_add(client, query):
    if not is_admin(client, query.from_user.id):
        return await query.answer("Only admins can add channels!", show_alert=True)
    back = InlineKeyboardMarkup([[styled_button("back", style="primary", callback_data="link_share")]])
    await _edit_query_message(query, "<b>Send the channel ID to add.\n\nExample: <code>-1001234567890</code>\n\n/cancel to cancel.</b>", reply_markup=back)
    try:
        msg = await client.listen(chat_id=query.message.chat.id, filters=filters.text, timeout=300)
    except Exception:
        return
    if msg.text.strip().lower() == "/cancel":
        return await msg.reply("Cancelled.", reply_markup=back)
    if not re.fullmatch(r"-100\d{10,}", msg.text.strip()):
        return await msg.reply("<b>Invalid channel ID.</b>", reply_markup=back)
    channel_id = int(msg.text.strip())
    try:
        member = await client.get_chat_member(channel_id, client.me.id)
        if member.status not in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
            return await msg.reply("<b>I must be an administrator in that channel.</b>", reply_markup=back)
        chat = await client.get_chat(channel_id)
    except UserNotParticipant:
        return await msg.reply("<b>I am not a member of that channel.</b>", reply_markup=back)
    except RPCError as e:
        return await msg.reply(f"<b>Unable to access channel:</b> {e}", reply_markup=back)
    await client.linkshare_db.add_link_share_channel(channel_id, {"name": chat.title, "username": chat.username, "added_at": datetime.utcnow(), "is_active": True})
    await msg.reply(f"<b>Channel <code>{chat.title}</code> ({channel_id}) has been added successfully.</b>", reply_markup=back)


@Client.on_callback_query(filters.regex(r"^ls_delete$"))
async def link_share_delete(client, query):
    if not is_admin(client, query.from_user.id):
        return await query.answer("Only admins can delete channels!", show_alert=True)
    channels = await client.linkshare_db.get_link_share_channels()
    if not channels:
        return await _edit_query_message(query, "<b>No Link Share channels found.</b>", reply_markup=InlineKeyboardMarkup([[styled_button("back", style="primary", callback_data="link_share")]]))
    buttons = [[styled_button(f"{data.get('name', cid)}", style="primary", callback_data=f"ls_del:{cid}")] for cid, data in channels.items()]
    buttons.append([styled_button("back", style="primary", callback_data="link_share")])
    await _edit_query_message(query, "<b>Select a channel to delete:</b>", reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r"^ls_del:-100\d+$"))
async def link_share_delete_confirm(client, query):
    if not is_admin(client, query.from_user.id):
        return await query.answer("Only admins can delete channels!", show_alert=True)
    channel_id = int(query.data.split(":", 1)[1])
    # Invalidate any stable tokens for this channel
    for kind in ("normal", "request"):
        old = await client.linkshare_db.get_link_share_channel_token(channel_id, kind)
        if old:
            await client.linkshare_db.delete_link_share_token(old)
    await client.linkshare_db.clear_link_share_channel_token(channel_id)
    removed = await client.linkshare_db.remove_link_share_channel(channel_id)
    await query.answer("Channel deleted." if removed else "Channel not found.", show_alert=True)
    await _show_link_share_home(client, query)


async def _get_channel_link(client, channel_id: int, is_request: bool) -> str:
    """Get (or create) a Link Share token for a channel and build its deep link.

    - Reuses the stable per-channel token while it is still valid.
    - If the stored token is missing or expired, issues a new one using the
      configured TTL (0 = never expire) and updates the channel mapping.
    """
    kind = "request" if is_request else "normal"
    token = await client.linkshare_db.get_link_share_channel_token(channel_id, kind)

    if token:
        token_data = await client.linkshare_db.get_link_share_token(token)
        if token_data and not _is_expired(token_data.get("expires_at")):
            return f"https://t.me/{client.username}?start={LINK_SHARE_PREFIX}{token}"
        # Stale / expired mapping → drop it so we can mint a fresh token
        if token_data:
            await client.linkshare_db.delete_link_share_token(token)
        await client.linkshare_db.clear_link_share_channel_token(channel_id, kind)

    token = secrets.token_urlsafe(16)
    expires_at = await _compute_expires_at(client)
    await client.linkshare_db.create_link_share_token(token, channel_id, is_request, expires_at)
    await client.linkshare_db.set_link_share_channel_token(channel_id, kind, token)
    return f"https://t.me/{client.username}?start={LINK_SHARE_PREFIX}{token}"


async def _regenerate_channel_token(client, channel_id: int, kind: str) -> str:
    """Force-mint a new token for a channel/kind and return the deep link."""
    old = await client.linkshare_db.get_link_share_channel_token(channel_id, kind)
    if old:
        await client.linkshare_db.delete_link_share_token(old)
    await client.linkshare_db.clear_link_share_channel_token(channel_id, kind)

    is_request = kind == "request"
    token = secrets.token_urlsafe(16)
    expires_at = await _compute_expires_at(client)
    await client.linkshare_db.create_link_share_token(token, channel_id, is_request, expires_at)
    await client.linkshare_db.set_link_share_channel_token(channel_id, kind, token)
    return f"https://t.me/{client.username}?start={LINK_SHARE_PREFIX}{token}"


async def send_link_share_page(client, query, request_link: bool, page: int):
    """Render a paginated grid of direct invite-link buttons for the
    Normal/Request Links screens, matching the Kafka-style layout."""
    if not is_admin(client, query.from_user.id):
        return await query.answer("Only admins can access this!", show_alert=True)

    channels = await client.linkshare_db.get_link_share_channels()
    if not channels:
        await _edit_query_message(
            query,
            "<b>No Link Share channels found. Add a channel first.</b>",
            reply_markup=InlineKeyboardMarkup([[styled_button("‹ Bᴀᴄᴋ", style="primary", callback_data="link_share")]])
        )
        return await query.answer()

    items = list(channels.items())
    total_pages = max(1, (len(items) + LINK_SHARE_PAGE_SIZE - 1) // LINK_SHARE_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start_idx = page * LINK_SHARE_PAGE_SIZE
    chunk = items[start_idx:start_idx + LINK_SHARE_PAGE_SIZE]
    page_cb = "ls_reqpage" if request_link else "ls_normpage"

    buttons = []
    row = []
    for cid, data in chunk:
        channel_id = int(cid)
        link = await _get_channel_link(client, channel_id, request_link)
        row.append(styled_button(f"{data.get('name', str(channel_id))}", style="primary", url=link))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    nav = []
    if page > 0:
        nav.append(styled_button("ᴘʀᴇᴠɪᴏᴜs", style="primary", callback_data=f"{page_cb}:{page - 1}"))
    if page < total_pages - 1:
        nav.append(styled_button("ɴᴇxᴛ", style="primary", callback_data=f"{page_cb}:{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([styled_button("‹ Bᴀᴄᴋ", style="primary", callback_data="link_share")])

    title = "📢 Nᴏʀᴍᴀʟ Iɴᴠɪᴛᴇ Lɪɴᴋs" if not request_link else "📩 Rᴇǫᴜᴇsᴛ Iɴᴠɪᴛᴇ Lɪɴᴋs"
    text = (
        f"<b>{title}</b>\n\n"
        f"<i>Click on a channel button to get its link:</i>\n\n"
        f"<b>Page {page + 1} of {total_pages}</b>"
    )
    await _edit_query_message(query, text, reply_markup=InlineKeyboardMarkup(buttons))
    await query.answer()


@Client.on_callback_query(filters.regex(r"^ls_normal$"))
async def link_share_normal(client, query):
    await send_link_share_page(client, query, False, 0)


@Client.on_callback_query(filters.regex(r"^ls_request$"))
async def link_share_request(client, query):
    await send_link_share_page(client, query, True, 0)


@Client.on_callback_query(filters.regex(r"^ls_normpage:\d+$"))
async def link_share_normal_page(client, query):
    page = int(query.data.split(":", 1)[1])
    await send_link_share_page(client, query, False, page)


@Client.on_callback_query(filters.regex(r"^ls_reqpage:\d+$"))
async def link_share_request_page(client, query):
    page = int(query.data.split(":", 1)[1])
    await send_link_share_page(client, query, True, page)


@Client.on_callback_query(filters.regex(r"^ls_list$"))
async def link_share_list(client, query):
    if not is_admin(client, query.from_user.id):
        return await query.answer("Only admins can access this!", show_alert=True)
    channels = await client.linkshare_db.get_link_share_channels()
    if not channels:
        text = "<b>No Link Share channels configured.</b>"
    else:
        lines = []
        for cid, data in channels.items():
            name = data.get("name", "Unknown")
            parts = [f"• <b>{name}</b>\n  <code>{cid}</code>"]
            for kind, label in (("normal", "Normal"), ("request", "Request")):
                tok = await client.linkshare_db.get_link_share_channel_token(int(cid), kind)
                if not tok:
                    parts.append(f"  {label}: <i>no token</i>")
                    continue
                td = await client.linkshare_db.get_link_share_token(tok)
                if not td:
                    parts.append(f"  {label}: <i>missing</i>")
                else:
                    parts.append(f"  {label}: {_format_expires(td.get('expires_at'))}")
            lines.append("\n".join(parts))
        text = "<b>Link Share Channels</b>\n\n" + "\n\n".join(lines)
    await _edit_query_message(
        query,
        text,
        reply_markup=InlineKeyboardMarkup([[styled_button("back", style="primary", callback_data="link_share")]]),
    )
    await query.answer()

