import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helper.helper_func import (
    encode,
    get_message_id,
    styled_button,
    get_forward_info,
    is_hidden_forward,
    safe_delete,
)
from config import LOGGER


async def _delete_after(message, seconds):
    await asyncio.sleep(seconds)
    await safe_delete(message)


def _strip_share_button(reply_markup):
    """Remove only the 'Share URL' button from a reply markup, keeping every
    other button (season/episode nav, etc.) untouched.
    Returns (changed, new_markup)."""
    if not reply_markup or not getattr(reply_markup, "inline_keyboard", None):
        return False, reply_markup
    changed = False
    new_rows = []
    for row in reply_markup.inline_keyboard:
        new_row = [btn for btn in row if not (btn.url and "telegram.me/share/url" in (btn.url or ""))]
        if len(new_row) != len(row):
            changed = True
        if new_row:
            new_rows.append(new_row)
    if not changed:
        return False, reply_markup
    return True, (InlineKeyboardMarkup(new_rows) if new_rows else None)


async def _strip_share_button_from_copy(client, chat_id, copied_message):
    """After copying a message into the DB channel, remove its Share URL
    button (if any) so it never gets re-delivered to end users."""
    if not copied_message:
        return
    changed, new_markup = _strip_share_button(copied_message.reply_markup)
    if changed:
        try:
            await client.edit_message_reply_markup(chat_id, copied_message.id, reply_markup=new_markup)
        except Exception:
            pass


async def _get_source_message(client, user_message):
    """Resolve an admin-provided forwarded message, a t.me message link, or
    a plain message ID that is already inside the primary DB channel."""
    fwd_chat_id, fwd_msg_id = get_forward_info(user_message)
    if fwd_chat_id is not None and fwd_msg_id is not None:
        return fwd_chat_id, fwd_msg_id
    if is_hidden_forward(user_message):
        return None, None
    if user_message.text:
        text = user_message.text.strip()

        # Plain message ID (e.g. "1523") = a message already sitting in the
        # primary DB channel. This avoids relying on forward metadata, which
        # Telegram can strip when the DB channel has content protection on.
        if text.isdigit():
            return getattr(client, 'primary_db_channel', client.db), int(text)

        match = re.match(r"https://t.me/(?:c/)?([^/]+)/([0-9]+)", text)
        if not match:
            return None, None
        channel_ref, msg_id = match.group(1), int(match.group(2))
        try:
            chat = await client.get_chat(channel_ref)
            return chat.id, msg_id
        except Exception:
            return None, None
    return None, None


def _is_db_channel(client, channel_id):
    """True if channel_id is already one of the configured DB channels
    (primary or any secondary channel added via the DB Channels settings)."""
    if channel_id is None:
        return False
    if channel_id == getattr(client, 'primary_db_channel', client.db):
        return True
    db_channels = getattr(client, 'db_channels', {})
    return str(channel_id) in db_channels


async def _copy_forward_to_db(client, message):
    """Copy a message the admin forwarded to the bot directly into the DB
    channel, using the content already delivered to the bot's chat. This
    works even if the bot has no access to (or isn't a member of) the
    original source channel, unlike copy_message(from_chat_id=...).

    Any caption / media changes present on the message the admin sent to
    the bot are preserved, because we copy from the bot chat, not from
    the original channel.
    """
    db_chat = getattr(client, 'primary_db_channel', client.db)
    copied = await message.copy(chat_id=db_chat, disable_notification=True)
    await _strip_share_button_from_copy(client, db_chat, copied)
    return copied.id


async def _copy_one_to_db(client, source_channel_id, source_message_id):
    """Copy one explicitly selected source message into the configured DB channel."""
    db_chat = getattr(client, 'primary_db_channel', client.db)
    copied = await client.copy_message(
        chat_id=db_chat,
        from_chat_id=source_channel_id,
        message_id=source_message_id,
        disable_notification=True
    )
    await _strip_share_button_from_copy(client, db_chat, copied)
    return copied.id


async def _copy_range_to_db(client, source_channel_id, first_id, last_id):
    """Copy an explicitly selected message range into the DB channel."""
    if first_id > last_id:
        first_id, last_id = last_id, first_id
    ids = list(range(first_id, last_id + 1))
    copied_ids = []
    db_chat = getattr(client, 'primary_db_channel', client.db)
    # Keep requests reasonably sized to avoid Telegram limits.
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        try:
            copied = await client.copy_messages(
                chat_id=db_chat,
                from_chat_id=source_channel_id,
                message_ids=chunk,
                disable_notification=True
            )
            if copied:
                for m in copied:
                    if not m:
                        continue
                    await _strip_share_button_from_copy(client, db_chat, m)
                    copied_ids.append(m.id)
        except Exception:
            # Fall back to individual copies so one unsupported/service message
            # does not prevent the rest of the selected range from being stored.
            for mid in chunk:
                try:
                    copied = await _copy_one_to_db(client, source_channel_id, mid)
                    copied_ids.append(copied)
                except Exception:
                    continue
    return copied_ids


async def get_db_channels_info(client):
    """Get formatted database channels information with links"""
    db_channels = getattr(client, 'db_channels', {})
    primary_db = getattr(client, 'primary_db_channel', client.db)

    if not db_channels:
        # If no additional DB channels, show primary only
        try:
            primary_chat = await client.get_chat(primary_db)
            if hasattr(primary_chat, 'invite_link') and primary_chat.invite_link:
                return f"<blockquote>✦ ᴘʀɪᴍᴀʀʏ ᴅʙ ᴄʜᴀɴɴᴇʟ: <a href='{primary_chat.invite_link}'>{primary_chat.title}</a></blockquote>"
            else:
                return f"<blockquote>✦ ᴘʀɪᴍᴀʀʏ ᴅʙ ᴄʜᴀɴɴᴇʟ: {primary_chat.title} (`{primary_db}`)</blockquote>"
        except Exception:
            return f"<blockquote>✦ ᴘʀɪᴍᴀʀʏ ᴅʙ ᴄʜᴀɴɴᴇʟ: `{primary_db}`</blockquote>"

    # Format all DB channels with links
    channels_info = ["<blockquote>✦ ᴀᴠᴀɪʟᴀʙʟᴇ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs:</blockquote>"]
    for channel_id_str, channel_data in db_channels.items():
        channel_name = channel_data.get('name', 'ᴜɴᴋɴᴏᴡɴ')
        is_primary_text = "✦ ᴘʀɪᴍᴀʀʏ" if channel_data.get('is_primary', False) else "• sᴇᴄᴏɴᴅᴀʀʏ"

        try:
            chat = await client.get_chat(int(channel_id_str))
            if hasattr(chat, 'invite_link') and chat.invite_link:
                channels_info.append(f"{is_primary_text}: <a href='{chat.invite_link}'>{channel_name}</a>")
            else:
                channels_info.append(f"{is_primary_text}: {channel_name} (`{channel_id_str}`)")
        except Exception:
            channels_info.append(f"{is_primary_text}: {channel_name} (`{channel_id_str}`)")

    return "\n".join(channels_info)


@Client.on_message(filters.private & filters.command('batch'))
async def batch(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)

    db_channels_info = await get_db_channels_info(client)

    while True:
        try:
            first_message = await client.ask(
                text=f"""<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴛʜᴇ ꜰɪʀsᴛ ꜰɪʟᴇ/ᴍᴇssᴀɢᴇ ᴛᴏ sᴛᴏʀᴇ ɪɴ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ.</blockquote>
{db_channels_info}

<blockquote>ᴏʀ sᴇɴᴅ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛ ʟɪɴᴋ, ᴏʀ ᴊᴜsᴛ ᴛʜᴇ ᴍᴇssᴀɢᴇ ID ɪғ ɪᴛ's ᴀʟʀᴇᴀᴅʏ ɪɴ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ</blockquote>""",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except Exception:
            return
        source_channel_id, first_id = await _get_source_message(client, first_message)
        if source_channel_id and first_id and not _is_db_channel(client, source_channel_id):
            await first_message.reply(
                "<blockquote>✗ ɴᴏᴛ ᴀ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛ</blockquote>\n\n"
                "/batch only works for files already stored in a DB channel. "
                "Use /genlink first to store files from other channels.",
                
            )
            continue
        if source_channel_id and first_id:
            break
        await first_message.reply("<blockquote>✗ ɪɴᴠᴀʟɪᴅ</blockquote>\n\nForward a valid channel post or send its t.me message link.")

    while True:
        try:
            second_message = await client.ask(
                text="<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴛʜᴇ ʟᴀsᴛ ꜰɪʟᴇ/ᴍᴇssᴀɢᴇ ᴛᴏ sᴛᴏʀᴇ ɪɴ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ, ᴏʀ ᴊᴜsᴛ ɪᴛs ᴍᴇssᴀɢᴇ ID.</blockquote>",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except Exception:
            return
        second_source, last_id = await _get_source_message(client, second_message)
        if second_source == source_channel_id and last_id:
            break
        await second_message.reply("<blockquote>✗ ɪɴᴠᴀʟɪᴅ</blockquote>\n\nThe first and last messages must be from the same source channel.")

    # source_channel_id is guaranteed to already be a DB channel at this
    # point (enforced above), so we only ever reuse existing message IDs -
    # /batch never copies/re-uploads files from outside channels.
    lo, hi = min(first_id, last_id), max(first_id, last_id)
    copied_ids = list(range(lo, hi + 1))
    multiplier_channel = source_channel_id

    if not copied_ids:
        return await second_message.reply("<blockquote>✗ ɴᴏ ᴍᴇssᴀɢᴇs ᴄᴏᴜʟᴅ ʙᴇ sᴛᴏʀᴇᴅ.</blockquote>")

    copied_start, copied_end = min(copied_ids), max(copied_ids)
    string = f"get-{copied_start * abs(multiplier_channel)}-{copied_end * abs(multiplier_channel)}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[styled_button("🔁 sʜᴀʀᴇ ᴜʀʟ", style="primary", url=f'https://telegram.me/share/url?url={link}')]])
    await second_message.reply_text(
        f"<blockquote>✓ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʙᴀᴛᴄʜ ʟɪɴᴋ</blockquote>\n\n<code>{link}</code>",
        reply_markup=reply_markup
    )


#===============================================================#

@Client.on_message(filters.private & filters.command('genlink'))
async def link_generator(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)

    db_channels_info = await get_db_channels_info(client)
    try:
        channel_message = await client.ask(
            text=f"""<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴛʜᴇ ꜰɪʟᴇ/ᴍᴇssᴀɢᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴛᴏʀᴇ ᴀɴᴅ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ʟɪɴᴋ ꜰᴏʀ.</blockquote>

{db_channels_info}

<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴏɴʟʏ — ʟɪɴᴋs / ᴍᴇssᴀɢᴇ IDs ᴀʀᴇ ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ.</blockquote>""",
            chat_id=message.from_user.id,
            filters=filters.forwarded,
            timeout=60
        )
    except Exception:
        return

    primary_db = getattr(client, 'primary_db_channel', client.db)
    source_channel_id, source_msg_id = get_forward_info(channel_message)

    # Already in a DB channel → reuse that post ID.
    # Edits you make later (caption / "CLICK HERE" button) are sent live.
    if source_channel_id and source_msg_id and _is_db_channel(client, source_channel_id):
        db_message_id = source_msg_id
        db_chat = source_channel_id
        note = (
            "Linked to existing DB post.\n"
            "Edit caption or buttons on that same post — users always get the latest."
        )
    else:
        # Non-DB forward → copy into primary DB (keeps any changes on the forward)
        try:
            db_message_id = await _copy_forward_to_db(client, channel_message)
            db_chat = primary_db
            note = (
                f"Stored as new DB post (ID <code>{db_message_id}</code>).\n"
                "Edit caption or buttons on that DB post — users always get the latest."
            )
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Failed to store forwarded message in DB: {e}")
            return await channel_message.reply(
                "<blockquote>✗ Failed to store the file in the DB channel.</blockquote>"
            )

    base64_string = await encode(f"get-{db_message_id * abs(db_chat)}")
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup(
        [[styled_button("🔁 Share URL", style="primary", url=f"https://telegram.me/share/url?url={link}")]]
    )
    await channel_message.reply_text(
        f"<blockquote>✓ Here is your link</blockquote>\n\n"
        f"<code>{link}</code>\n\n"
        f"DB channel: <code>{db_chat}</code>\n"
        f"DB message ID: <code>{db_message_id}</code>\n"
        f"<i>{note}</i>",
        reply_markup=reply_markup,
    )

#===============================================================#
