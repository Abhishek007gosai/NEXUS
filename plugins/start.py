import asyncio
import os
import random
import sys
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, ChatInviteLink, ChatPrivileges
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant
from bot import Bot
from config import *
from helper_func import *
from database.database import *

BAN_SUPPORT = f"{BAN_SUPPORT}"

@Bot.on_message(filters.command('start') & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id

    # Add user if not already present
    if not await db.present_user(user_id):
        try:
            await db.add_user(user_id)
        except:
            pass

    # Check if user is banned
    banned_users = await db.get_ban_users()
    if user_id in banned_users:
        return await message.reply_text(
            "<b>⛔️ You are Bᴀɴɴᴇᴅ from using this bot.</b>\n\n"
            "<i>Contact support if you think this is a mistake.</i>",
            reply_markup=InlineKeyboardMarkup(
                [[styled_button("Contact Support", style="primary", url=BAN_SUPPORT)]]
            )
        )
    # ✅ Check Force Subscription
    if not await is_subscribed(client, user_id):
        #await temp.delete()
        return await not_joined(client, message)

    # File auto-delete time in seconds (Set your desired time in seconds here)
    FILE_AUTO_DELETE = await db.get_del_timer()  # Example: 3600 seconds (1 hour)

    # Handle normal message flow
    text = message.text
    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except IndexError:
            return

        string = await decode(base64_string)
        argument = string.split("-")

        ids = []
        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[2]) / abs(client.db_channel.id))
                ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))
            except Exception as e:
                print(f"Error decoding IDs: {e}")
                return

        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except Exception as e:
                print(f"Error decoding ID: {e}")
                return

        temp_msg = await message.reply("<b>Please wait...</b>")
        try:
            messages = await get_messages(client, ids)
        except Exception as e:
            await message.reply_text("Something went wrong!")
            print(f"Error getting messages: {e}")
            return
        finally:
            await temp_msg.delete()
 
        codeflix_msgs = []
        for msg in messages:
            caption = (CUSTOM_CAPTION.format(previouscaption="" if not msg.caption else msg.caption.html, 
                                             filename=msg.document.file_name) if bool(CUSTOM_CAPTION) and bool(msg.document)
                       else ("" if not msg.caption else msg.caption.html))
            # Pass through DB-channel buttons but strip "Share URL" / share links
            reply_markup = _strip_share_buttons(msg.reply_markup)
            try:
                copied_msg = await msg.copy(
                    chat_id=message.from_user.id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=PROTECT_CONTENT
                )
                await asyncio.sleep(0.1)
                codeflix_msgs.append(copied_msg)
            except Exception as e:
                print(f"Failed to send message: {e}")

        if FILE_AUTO_DELETE > 0:
            notification_msg = await message.reply(
                f"<b>»ᴛʜɪs ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ {get_exp_time(FILE_AUTO_DELETE)}<blockquote>ᴘʟᴇᴀsᴇ sᴀᴠᴇ ᴏʀ ғᴏʀᴡᴀʀᴅ ɪᴛ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ʙᴇғᴏʀᴇ ɪᴛ ɢᴇᴛs ᴅᴇʟᴇᴛᴇᴅ.</blockquote></b>"
            )
            reload_url = (
                f"https://t.me/{client.username}?start={message.command[1]}"
                if message.command and len(message.command) > 1
                else None
            )
            asyncio.create_task(
                schedule_auto_delete(client, codeflix_msgs, notification_msg, FILE_AUTO_DELETE, reload_url)
            )
    else:
        reply_markup = InlineKeyboardMarkup(
            [
                [styled_button("• ᴍᴏʀᴇ ᴄʜᴀɴɴᴇʟs •", style="primary", url="https://t.me/AnimeNexusNetwork/158")],
                [
                    styled_button("• ᴀʙᴏᴜᴛ", style="primary", callback_data="about"),
                    styled_button("ʜᴇʟᴘ •", style="primary", callback_data="help"),
                ],
            ]
        )
        await message.reply_photo(
            photo=START_PIC,
            caption=START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=reply_markup
        )
        
        return



#=====================================================================================##
# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport



# Create a global dictionary to store chat data
chat_data_cache = {}

def _strip_share_buttons(reply_markup):
    """Remove Share URL / telegram.me/share buttons; keep other keyboards (e.g. seasons)."""
    if not reply_markup or not getattr(reply_markup, "inline_keyboard", None):
        return None
    cleaned = []
    for row in reply_markup.inline_keyboard:
        new_row = []
        for btn in row:
            url = (getattr(btn, "url", None) or "").lower()
            label = (getattr(btn, "text", None) or "").lower()
            if "share" in label or "telegram.me/share" in url or "t.me/share" in url:
                continue
            new_row.append(btn)
        if new_row:
            cleaned.append(new_row)
    if not cleaned:
        return None
    return InlineKeyboardMarkup(cleaned)




async def _silent_delete_later(msg, delay_seconds: int):
    """Delete a message after delay with no notification to the user."""
    try:
        await asyncio.sleep(delay_seconds)
        await msg.delete()
    except Exception:
        pass


async def not_joined(client: Client, message: Message):
    temp = await message.reply("<b><i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i></b>")

    user_id = message.from_user.id
    join_buttons = []  # individual channel buttons
    count = 0

    try:
        all_channels = await db.show_channels()

        for total, chat_id in enumerate(all_channels, start=1):
            mode = await db.get_channel_mode(chat_id)

            await message.reply_chat_action(ChatAction.TYPING)

            if not await is_sub(client, user_id, chat_id):
                try:
                    if chat_id in chat_data_cache:
                        data = chat_data_cache[chat_id]
                    else:
                        data = await client.get_chat(chat_id)
                        chat_data_cache[chat_id] = data

                    if mode == "on" and not data.username:
                        invite = await client.create_chat_invite_link(
                            chat_id=chat_id,
                            creates_join_request=True,
                            expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY)
                            if FSUB_LINK_EXPIRY else None
                        )
                        link = invite.invite_link
                    else:
                        if data.username:
                            link = f"https://t.me/{data.username}"
                        else:
                            invite = await client.create_chat_invite_link(
                                chat_id=chat_id,
                                expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY)
                                if FSUB_LINK_EXPIRY else None
                            )
                            link = invite.invite_link

                    count += 1
                    # Numbered small-caps style + primary (blue) color like KAYA/Shinobu
                    join_buttons.append(
                        styled_button(
                            f"ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ {count}",
                            style="primary",
                            url=link
                        )
                    )
                    await temp.edit(f"<b>{'! ' * count}</b>")

                except Exception as e:
                    print(f"Error with chat {chat_id}: {e}")

        # Arrange buttons: 2 per row when possible (matches your screenshots)
        buttons = []
        for i in range(0, len(join_buttons), 2):
            if i + 1 < len(join_buttons):
                buttons.append([join_buttons[i], join_buttons[i + 1]])
            else:
                buttons.append([join_buttons[i]])

        # Try Again button (full width, primary/blue)
        try:
            buttons.append([
                styled_button(
                    "• ᴛʀʏ ᴀɢᴀɪɴ •",
                    style="primary",
                    url=f"https://t.me/{client.username}?start={message.command[1]}"
                )
            ])
        except IndexError:
            # No deep-link payload — still show a generic try again that restarts the bot
            buttons.append([
                styled_button(
                    "• ᴛʀʏ ᴀɢᴀɪɴ •",
                    style="primary",
                    url=f"https://t.me/{client.username}?start=start"
                )
            ])

        fsub_msg = await message.reply_photo(
            photo=FORCE_PIC,
            caption=FORCE_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
            protect_content=True,  # Prevents forwarding / saving of the fsub message
        )

        await temp.delete()

        # Silently auto-delete fsub message after 15 minutes (no "will be deleted" notice)
        asyncio.create_task(_silent_delete_later(fsub_msg, 15 * 60))

    except Exception as e:
        print(e)
        await temp.edit(str(e))
#=====================================================================================##


async def schedule_auto_delete(client, codeflix_msgs, notification_msg, file_auto_delete, reload_url):
    await asyncio.sleep(file_auto_delete)
    for snt_msg in codeflix_msgs:
        if snt_msg:
            try:
                await snt_msg.delete()
            except Exception as e:
                print(f"Error deleting message {snt_msg.id}: {e}")

    try:
        keyboard = InlineKeyboardMarkup(
            [[
                styled_button("ɢᴇᴛ ᴀɢᴀɪɴ!", style="success", url=reload_url),
                styled_button("ᴄʟᴏꜱᴇ", style="danger", callback_data="close"),
            ]]
        ) if reload_url else None

        await notification_msg.edit(
            "<b>›› ᴘʀᴇᴠɪᴏᴜs ᴍᴇssᴀɢᴇ ᴡᴀs ᴅᴇʟᴇᴛᴇᴅ<blockquote>ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ɢᴇᴛ ᴛʜᴇ ᴀɢᴀɪɴ, ᴛʜᴇɴ ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴅᴇʟᴇᴛᴇᴅ ᴍᴇssᴀɢᴇ. ᴇʟsᴇ ᴄʟᴏsᴇ ᴛʜɪs ᴍᴇssᴀɢᴇ.</blockquote></b>",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error updating notification with 'Get File Again' button: {e}")
