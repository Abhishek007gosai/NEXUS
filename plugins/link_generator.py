import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helper.helper_func import encode, get_message_id
from config import LOGGER

async def _delete_after(message, seconds):
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except Exception:
        pass


def _strip_share_button(reply_markup):
    """Remove only the 'Share URL' button from a reply markup, keeping every
    other button (season/episode nav, etc.) untouched.
    Returns (changed, new_markup)."""
    if not reply_markup or not getattr(reply_markup, "inline_keyboard", None):
        return False, reply_markup
    changed = False
    new_rows = []
    for row in reply_markup.inline_keyboard:
        new_row = [btn for btn in row if not (btn.url and "telegram.me/share/url" in btn.url)]
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
    if user_message.forward_from_chat and user_message.forward_from_message_id:
        return user_message.forward_from_chat.id, user_message.forward_from_message_id
    if user_message.forward_sender_name:
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
    original source channel, unlike copy_message(from_chat_id=...)."""
    copied = await message.copy(chat_id=client.primary_db_channel, disable_notification=True)
    await _strip_share_button_from_copy(client, client.primary_db_channel, copied)
    return copied.id


async def _copy_one_to_db(client, source_channel_id, source_message_id):
    """Copy one explicitly selected source message into the configured DB channel."""
    copied = await client.copy_message(
        chat_id=client.primary_db_channel,
        from_chat_id=source_channel_id,
        message_id=source_message_id,
        disable_notification=True
    )
    await _strip_share_button_from_copy(client, client.primary_db_channel, copied)
    return copied.id


async def _copy_range_to_db(client, source_channel_id, first_id, last_id):
    """Copy an explicitly selected message range into the DB channel."""
    if first_id > last_id:
        first_id, last_id = last_id, first_id
    ids = list(range(first_id, last_id + 1))
    copied_ids = []
    # Keep requests reasonably sized to avoid Telegram limits.
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        try:
            copied = await client.copy_messages(
                chat_id=client.primary_db_channel,
                from_chat_id=source_channel_id,
                message_ids=chunk,
                disable_notification=True
            )
            if copied:
                for m in copied:
                    if not m:
                        continue
                    await _strip_share_button_from_copy(client, client.primary_db_channel, m)
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
        except:
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
        except:
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
                quote=True
            )
            continue
        if source_channel_id and first_id:
            break
        await first_message.reply("<blockquote>✗ ɪɴᴠᴀʟɪᴅ</blockquote>\n\nForward a valid channel post or send its t.me message link.", quote=True)

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
        await second_message.reply("<blockquote>✗ ɪɴᴠᴀʟɪᴅ</blockquote>\n\nThe first and last messages must be from the same source channel.", quote=True)

    # source_channel_id is guaranteed to already be a DB channel at this
    # point (enforced above), so we only ever reuse existing message IDs -
    # /batch never copies/re-uploads files from outside channels.
    lo, hi = min(first_id, last_id), max(first_id, last_id)
    copied_ids = list(range(lo, hi + 1))
    multiplier_channel = source_channel_id

    if not copied_ids:
        return await second_message.reply("<blockquote>✗ ɴᴏ ᴍᴇssᴀɢᴇs ᴄᴏᴜʟᴅ ʙᴇ sᴛᴏʀᴇᴅ.</blockquote>", quote=True)

    copied_start, copied_end = min(copied_ids), max(copied_ids)
    string = f"get-{copied_start * abs(multiplier_channel)}-{copied_end * abs(multiplier_channel)}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 sʜᴀʀᴇ ᴜʀʟ", url=f'https://telegram.me/share/url?url={link}')]])
    sent = await second_message.reply_text(
        f"<blockquote>✓ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʙᴀᴛᴄʜ ʟɪɴᴋ</blockquote>\n\n<code>{link}</code>",
        quote=True, reply_markup=reply_markup
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

<blockquote>ᴏʀ sᴇɴᴅ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛ ʟɪɴᴋ</blockquote>""",
            chat_id=message.from_user.id,
            filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
            timeout=60
        )
    except Exception:
        return

    if channel_message.forward_date:
        # Forwarded post/file: copy straight from what was forwarded to the
        # bot. No need for the bot to have access to the original channel.
        try:
            db_message_id = await _copy_forward_to_db(client, channel_message)
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Failed to store forwarded message in DB: {e}")
            return await channel_message.reply("<blockquote>✗ ꜰᴀɪʟᴇᴅ ᴛᴏ sᴛᴏʀᴇ ᴛʜᴇ ꜰɪʟᴇ ɪɴ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ.</blockquote>", quote=True)
    else:
        # Plain text input: must be a t.me post link, which requires the
        # bot to have access to that source channel to fetch the message.
        source_channel_id, source_message_id = await _get_source_message(client, channel_message)
        if not source_channel_id or not source_message_id:
            return await channel_message.reply("<blockquote>✗ ɪɴᴠᴀʟɪᴅ</blockquote>\n\nForward a valid channel post or send its t.me message link.", quote=True)

        try:
            db_message_id = await _copy_one_to_db(client, source_channel_id, source_message_id)
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Failed to store selected message in DB: {e}")
            return await channel_message.reply("<blockquote>✗ ꜰᴀɪʟᴇᴅ ᴛᴏ sᴛᴏʀᴇ ᴛʜᴇ ꜰɪʟᴇ ɪɴ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ. ᴍᴀᴋᴇ sᴜʀᴇ ᴛʜᴇ ʙᴏᴛ ᴄᴀɴ ᴀᴄᴄᴇss ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ, ᴏʀ ꜰᴏʀᴡᴀʀᴅ ᴛʜᴇ ᴘᴏsᴛ ɪɴsᴛᴇᴀᴅ ᴏꜰ sᴇɴᴅɪɴɢ ɪᴛs ʟɪɴᴋ.</blockquote>", quote=True)

    base64_string = await encode(f"get-{db_message_id * abs(client.primary_db_channel)}")
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 sʜᴀʀᴇ ᴜʀʟ", url=f'https://telegram.me/share/url?url={link}')]])
    sent = await channel_message.reply_text(
        f"<blockquote>✓ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ</blockquote>\n\n<code>{link}</code>",
        quote=True, reply_markup=reply_markup
    )

#===============================================================#
