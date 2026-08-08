from helper.helper_func import *
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import humanize
from config import OWNER_ID, WEBAPP_URL, INDEX_URL
from plugins.shortner import get_short
from helper.helper_func import (
    get_messages,
    force_sub,
    decode,
    batch_auto_del_notification,
    retry_on_flood,
    paced_copy,
)
import asyncio
from datetime import datetime, timedelta
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait

#===============================================================#

# Markers that identify anime info-card posts (title / synopsis / season buttons)
# Match both ASCII hyphen and common unicode dashes
_INFO_CARD_MARKERS = (
    "SYNOPSIS",
    "EPISODE",
    "SEASON",
    "SCORE",
    "AUDIO",
)

_FILE_MEDIA_ATTRS = (
    "video",
    "document",
    "audio",
    "animation",
    "voice",
    "video_note",
)


def _is_info_card(msg) -> bool:
    """True for text/photo info cards (anime synopsis + season buttons).

    These posts skip the shortener so anyone can open them directly.
    Actual downloadable files (video / document / audio / animation) still
    go through the shortener for non-pro users.
    """
    if msg is None or getattr(msg, "empty", False):
        return False

    # 1) Caption / text markers (SYNOPSIS, EPISODE, SEASON, SCORE, AUDIO)
    text = (msg.caption or msg.text or "") or ""
    upper = text.upper()
    if any(m in upper for m in _INFO_CARD_MARKERS):
        return True

    # 2) Season-style navigation: 2+ URL buttons (S1/4, MOVIES, etc.)
    markup = getattr(msg, "reply_markup", None)
    if markup and getattr(markup, "inline_keyboard", None):
        url_btns = 0
        for row in markup.inline_keyboard:
            for btn in row:
                if getattr(btn, "url", None):
                    url_btns += 1
        if url_btns >= 2:
            # URL-button grid + no file media → info card
            has_file = any(getattr(msg, attr, None) for attr in _FILE_MEDIA_ATTRS)
            if not has_file:
                return True

    # 3) No downloadable media at all → text or photo only = info card
    for attr in _FILE_MEDIA_ATTRS:
        if getattr(msg, attr, None):
            return False
    return True


async def _send_shortener_gate(client: Client, message: Message, base64_string: str):
    """Send the ads-token / shortener verification message and stop."""
    try:
        short_link = get_short(
            f"https://t.me/{client.username}?start=yu3elk{base64_string}7",
            client,
        )
    except Exception as e:
        client.LOGGER(__name__, client.name).warning(f"Shortener failed: {e}")
        return await message.reply("Couldn't generate short link.")

    short_photo = client.messages.get("SHORT_PIC", "")
    short_caption = client.messages.get("SHORT_MSG", "")
    tutorial_link = getattr(client, "tutorial_link", "https://t.me/+wekKcN1tjbAxY2U1")

    await client.send_photo(
        chat_id=message.chat.id,
        photo=short_photo,
        caption=short_caption,
        reply_markup=InlineKeyboardMarkup(
            [
                [styled_button("»ᴄʟɪᴄᴋ ʜᴇʀᴇ«", style="primary", url=short_link)],
                [
                    styled_button(
                        "»ʜᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ ᴠɪᴅᴇᴏ ᴛᴜᴛᴏʀɪᴀʟ«",
                        style="primary",
                        url=tutorial_link,
                    )
                ],
            ]
        ),
        protect_content=True,
    )


#===============================================================#

@Client.on_message(filters.command('start') & filters.private)
@force_sub
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id

    # 1. Add user if not present
    present = await client.mongodb.present_user(user_id)
    if not present:
        try:
            await client.mongodb.add_user(user_id)
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Error adding a user:\n{e}")

    # 2. Check if banned
    is_banned = await client.mongodb.is_banned(user_id)
    if is_banned:
        return await message.reply("**You have been banned from using this bot!**")

    text = message.text
    if len(text) > 7:
        try:
            original_payload = text.split(" ", 1)[1]
            base64_string = original_payload

            is_short_link = False
            if base64_string.startswith("yu3elk"):
                base64_string = base64_string[6:-1]
                is_short_link = True

        except IndexError:
            return await message.reply("Invalid command format.")

        # 3. Check premium status (used later for shortener gate)
        is_user_pro = await client.mongodb.is_pro(user_id)
        shortner_enabled = getattr(client, "shortner_enabled", True)

        # 4. Decode and prepare file IDs
        try:
            string = await decode(base64_string)
            argument = string.split("-")
            ids = []
            source_channel_id = None

            if len(argument) == 3:
                # Try to determine source channel from encoded multiplier
                encoded_start = int(argument[1])
                encoded_end = int(argument[2])
                
                # Try primary channel first
                primary_multiplier = abs(client.db)
                start_primary = int(encoded_start / primary_multiplier)
                end_primary = int(encoded_end / primary_multiplier)
                
                # Check if the division results in clean integers (meaning this channel was used for encoding)
                if encoded_start % primary_multiplier == 0 and encoded_end % primary_multiplier == 0:
                    source_channel_id = client.db
                    start = start_primary
                    end = end_primary
                    client.LOGGER(__name__, client.name).info(f"Decoded batch from primary channel {source_channel_id}: {start}-{end}")
                else:
                    # Try secondary channels
                    db_channels = getattr(client, 'db_channels', {})
                    for channel_id_str in db_channels.keys():
                        channel_id = int(channel_id_str)
                        channel_multiplier = abs(channel_id)
                        start_test = int(encoded_start / channel_multiplier)
                        end_test = int(encoded_end / channel_multiplier)
                        
                        if encoded_start % channel_multiplier == 0 and encoded_end % channel_multiplier == 0:
                            source_channel_id = channel_id
                            start = start_test
                            end = end_test
                            client.LOGGER(__name__, client.name).info(f"Decoded batch from secondary channel {source_channel_id}: {start}-{end}")
                            break
                    
                    # Fallback to primary if no match found
                    if source_channel_id is None:
                        source_channel_id = client.db
                        start = start_primary
                        end = end_primary
                
                ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))

            elif len(argument) == 2:
                # Single message
                encoded_msg = int(argument[1])
                
                # Try primary channel first
                if hasattr(client, 'db_channel') and client.db_channel:
                    primary_multiplier = abs(client.db_channel.id)
                    msg_id_primary = int(encoded_msg / primary_multiplier)
                    
                    if encoded_msg % primary_multiplier == 0:
                        source_channel_id = client.db_channel.id
                        ids = [msg_id_primary]
                    else:
                        # Try secondary channels
                        db_channels = getattr(client, 'db_channels', {})
                        for channel_id_str in db_channels.keys():
                            channel_id = int(channel_id_str)
                            channel_multiplier = abs(channel_id)
                            msg_id_test = int(encoded_msg / channel_multiplier)
                            
                            if encoded_msg % channel_multiplier == 0:
                                source_channel_id = channel_id
                                ids = [msg_id_test]
                                break
                        
                        # Fallback to primary
                        if source_channel_id is None:
                            source_channel_id = client.db_channel.id if hasattr(client, 'db_channel') else client.db
                            ids = [msg_id_primary]
                else:
                    # Fallback for legacy compatibility
                    source_channel_id = client.db
                    ids = [int(encoded_msg / abs(client.db))]

        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Error decoding base64: {e}")
            return await message.reply("⚠️ Invalid or expired link.")

        # 7. Get messages from the specific source channel first
        temp_msg = await message.reply("Wait A Sec..")
        messages = []
        log = client.LOGGER(__name__, client.name)

        try:
            # Try to get messages from the identified source channel first
            if source_channel_id:
                log.info(f"Trying to get messages from source channel: {source_channel_id}")
                try:
                    msgs = await retry_on_flood(
                        lambda: client.get_messages(
                            chat_id=source_channel_id,
                            message_ids=list(ids),
                        ),
                        max_retries=5,
                        logger=log,
                        label=f"get_messages src:{source_channel_id}",
                    )
                    # Pyrogram may return a single Message or a list
                    if msgs is None:
                        msgs = []
                    elif not isinstance(msgs, (list, tuple)):
                        msgs = [msgs]
                    # Filter out None / empty messages (deleted/not found)
                    valid_msgs = [
                        msg for msg in msgs
                        if msg is not None and not getattr(msg, "empty", False)
                    ]
                    messages.extend(valid_msgs)
                    log.info(f"Found {len(valid_msgs)} messages from source channel {source_channel_id}")

                    if len(valid_msgs) < len(list(ids)):
                        missing_ids = [mid for mid in ids if mid not in {msg.id for msg in valid_msgs}]
                        if missing_ids:
                            log.info(f"Missing {len(missing_ids)} messages, trying fallback system")
                            additional_messages = await get_messages(client, missing_ids)
                            messages.extend(
                                m for m in additional_messages
                                if m is not None and not getattr(m, "empty", False)
                            )
                            log.info(f"Found {len(additional_messages)} additional messages from fallback")
                except Exception as e:
                    log.warning(f"Error getting messages from source channel {source_channel_id}: {e}")
                    messages = await get_messages(client, ids)
            else:
                log.info("No specific source channel identified, using multi-channel fallback")
                messages = await get_messages(client, ids)
        except Exception as e:
            await temp_msg.edit_text("Something went wrong!")
            log.warning(f"Error getting messages: {e}")
            return

        # Final filter: drop None / empty service messages
        messages = [
            m for m in messages
            if m is not None and not getattr(m, "empty", False)
        ]

        if not messages:
            return await temp_msg.edit("Couldn't find the files in the database.")

        # ── Shortener gate (skipped for info-card posts) ──────────────
        # Info cards (synopsis + season buttons like the screenshot) are
        # delivered to everyone without verification. Actual file posts
        # still require the shortener for non-pro users.
        all_info_cards = all(_is_info_card(m) for m in messages)
        needs_shortener = (
            not is_user_pro
            and user_id != OWNER_ID
            and not is_short_link
            and shortner_enabled
            and not all_info_cards
        )
        if needs_shortener:
            try:
                await temp_msg.delete()
            except Exception:
                pass
            await _send_shortener_gate(client, message, base64_string)
            return  # prevent sending actual files

        try:
            await temp_msg.delete()
        except Exception:
            pass

        yugen_msgs = []
        # Channel to re-fetch from so caption/button edits are always current
        live_chat = source_channel_id or getattr(client, "primary_db_channel", client.db)

        for msg in messages:
            # Re-fetch THIS message right before send so any edit you made
            # on the DB post (caption text OR "CLICK HERE" button) is used.
            try:
                fresh = await retry_on_flood(
                    lambda mid=msg.id: client.get_messages(chat_id=live_chat, message_ids=mid),
                    max_retries=3,
                    logger=log,
                    label=f"live_fetch:{msg.id}",
                )
                if fresh is not None and not getattr(fresh, "empty", False):
                    msg = fresh
            except Exception as e:
                log.warning(f"Live re-fetch failed for {msg.id}, using cached: {e}")

            # Caption: prefer live HTML caption from the DB post
            if msg.caption:
                try:
                    live_caption = msg.caption.html
                except Exception:
                    live_caption = msg.caption
            else:
                live_caption = None

            file_name = ""
            if getattr(msg, "document", None) and msg.document:
                file_name = msg.document.file_name or ""

            caption_tpl = (client.messages.get("CAPTION") or "").strip()
            if caption_tpl and "{previouscaption}" in caption_tpl and getattr(msg, "document", None):
                try:
                    caption = caption_tpl.format(previouscaption=live_caption or file_name or "")
                except Exception:
                    caption = live_caption or ""
            else:
                # No template override → send exactly what is on the DB post
                caption = live_caption if live_caption is not None else ""

            # Buttons: always from the live DB post (unless globally disabled)
            reply_markup = None if client.disable_btn else msg.reply_markup
            protect_this = True if reply_markup else client.protect

            try:
                copy_kwargs = {
                    "chat_id": message.from_user.id,
                    "protect_content": protect_this,
                    "caption": caption,
                }
                # Always pass reply_markup so button edits apply (or clear)
                if not client.disable_btn:
                    copy_kwargs["reply_markup"] = reply_markup

                copied_msg = await paced_copy(msg, **copy_kwargs)
                if copied_msg is not None:
                    yugen_msgs.append(copied_msg)
            except Exception as e:
                err = str(e).lower()
                if "empty" in err:
                    log.info(f"Skipping empty message {getattr(msg, 'id', '?')}")
                else:
                    log.warning(f"Failed to send message {getattr(msg, 'id', '?')}: {e}")
                continue

        # 8. Auto delete timer
        try:
            auto_del_seconds = int(client.auto_del or 0)
        except (TypeError, ValueError):
            auto_del_seconds = 0
            client.auto_del = 0

        if messages and auto_del_seconds > 0:
            # Create transfer link for getting files again (original base64_string)
            transfer_link = original_payload
            
            # Start batch auto delete notification - single notification for all files
            asyncio.create_task(batch_auto_del_notification(
                bot_username=client.username,
                messages=yugen_msgs,
                delay_time=auto_del_seconds,
                transfer_link=transfer_link,
                chat_id=message.from_user.id,
                client=client
            ))
        return

    # 9. Normal start message
    else:
        # Layout matches Touka-style start:
        # [OPEN INDEX]  (green web-app, full width)
        # [HELP] [CLOSE]
        # (+ SETTINGS for admins)
        buttons = []

        # Open Index button — INDEX_URL preferred (normal url link), else WEBAPP_URL (mini app)
        index_url = (INDEX_URL or "").strip()
        webapp_url = (WEBAPP_URL or "").strip()
        if index_url.startswith(("https://", "http://")):
            buttons.append([
                styled_button("ᴏᴘᴇɴ ɪɴᴅᴇx", style="success", url=index_url)
            ])
        elif webapp_url.startswith("https://"):
            buttons.append([
                styled_button("ᴏᴘᴇɴ ɪɴᴅᴇx", style="success", web_app=WebAppInfo(url=webapp_url))
            ])
        elif webapp_url.startswith("http://"):
            buttons.append([
                styled_button("ᴏᴘᴇɴ ɪɴᴅᴇx", style="success", url=webapp_url)
            ])

        buttons.append([
            styled_button("ʜᴇʟᴘ", style="danger", callback_data="about"),
            styled_button("ᴄʟᴏsᴇ", style="danger", callback_data="close"),
        ])

        if user_id in client.admins:
            buttons.insert(0, [styled_button("⛩️ ꜱᴇᴛᴛɪɴɢꜱ ⛩️", style="danger", callback_data="settings")])

        photo = client.messages.get("START_PHOTO", "")
        start_caption = client.messages.get('START', 'Welcome, {mention}').format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        )

        async def _send_start(markup):
            if photo:
                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=photo,
                    caption=start_caption,
                    reply_markup=markup,
                )
            else:
                await client.send_message(
                    chat_id=message.chat.id,
                    text=start_caption,
                    reply_markup=markup,
                )

        try:
            await _send_start(InlineKeyboardMarkup(buttons))
        except Exception as e:
            # BUTTON_URL_INVALID — drop URL/web_app buttons and retry so /start never crashes
            if "BUTTON_URL" in str(e).upper() or "URL_INVALID" in str(e).upper():
                safe_buttons = [
                    row for row in buttons
                    if all(
                        getattr(btn, "url", None) is None
                        and getattr(btn, "web_app", None) is None
                        for btn in row
                    )
                ]
                if not safe_buttons:
                    safe_buttons = [[
                        styled_button("ʜᴇʟᴘ", style="danger", callback_data="about"),
                        styled_button("ᴄʟᴏsᴇ", style="danger", callback_data="close"),
                    ]]
                try:
                    await _send_start(InlineKeyboardMarkup(safe_buttons))
                except Exception:
                    await client.send_message(chat_id=message.chat.id, text=start_caption)
            else:
                raise
        return

#===============================================================#

@Client.on_message(filters.command('request') & filters.private)
async def request_command(client: Client, message: Message):
    user_id = message.from_user.id
    is_admin = user_id in client.admins  # ✅ Fix this line
    is_user_premium = await client.mongodb.is_pro(user_id)

    if is_admin or user_id == OWNER_ID:
        await message.reply_text("🔹 **You are my sensei!**\nThis command is only for users.")
        return

    if not is_user_premium: 
        BUTTON_URL = "https://t.me/+wekKcN1tjbAxY2U1"
        reply_markup = InlineKeyboardMarkup([
            [styled_button("💎 Upgrade to Premium", style="success", url=BUTTON_URL)]
        ])
        await message.reply(
            "❌ **You are not a premium user.**\nUpgrade to premium to access this feature.",
            reply_markup=reply_markup
        )
        return

    if len(message.command) < 2:
        await message.reply("⚠️ **Send me your request in this format:**\n`/request Your_Request_Here`")
        return

    requested = " ".join(message.command[1:])

    owner_message = (
        f"📩 **New Request from {message.from_user.mention}**\n\n"
        f"🆔 User ID: `{user_id}`\n"
        f"📝 Request: `{requested}`"
    )

    await client.send_message(OWNER_ID, owner_message)
    await message.reply("✅ **Thanks for your request!**\nYour request will be reviewed soon. Please wait.")

#===============================================================#

@Client.on_message(filters.command('profile') & filters.private)
async def my_plan(client: Client, message: Message):
    user_id = message.from_user.id
    is_admin = user_id in client.admins  # ✅ Fix here

    if is_admin or user_id == OWNER_ID:
        await message.reply_text("🔹 You're my sensei! This command is only for users.")
        return
    
    is_user_premium = await client.mongodb.is_pro(user_id)

    if is_user_premium:
        await message.reply_text(
            "**👤 Profile Information:**\n\n"
            "🔸 Ads: Disabled\n"
            "🔸 Plan: Premium\n"
            "🔸 Request: Enabled\n\n"
            "🌟 You're a Premium User!"
        )
    else:
        await message.reply_text(
            "**👤 Profile Information:**\n\n"
            "🔸 Ads: Enabled\n"
            "🔸 Plan: Free\n"
            "🔸 Request: Disabled\n\n"
            "🔓 Unlock Premium to get more benefits\n"
            "Contact: @GetoPro"
        )
