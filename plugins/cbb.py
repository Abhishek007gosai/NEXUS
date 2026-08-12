#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.

from pyrogram import Client
from bot import Bot
from config import *
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import MessageNotModified, MessageIdInvalid, MessageEmpty
from helper_func import styled_button
from database.database import *


async def _safe_edit(message, text, **kwargs):
    """edit_text that ignores MESSAGE_NOT_MODIFIED / gone / empty."""
    try:
        return await message.edit_text(text, **kwargs)
    except (MessageNotModified, MessageIdInvalid, MessageEmpty):
        return message
    except Exception:
        try:
            return await message.edit_text(text, **kwargs)
        except Exception:
            return message


@Bot.on_callback_query()
async def cb_handler(client: Bot, query: CallbackQuery):
    data = query.data

    if data == "help":
        await _safe_edit(
            query.message,
            text=HELP_TXT.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [styled_button('ʜᴏᴍᴇ', style="primary", callback_data='start'),
                 styled_button("ᴄʟᴏꜱᴇ", style="danger", callback_data='close')]
            ])
        )
        try:
            await query.answer()
        except Exception:
            pass

    elif data == "about":
        await _safe_edit(
            query.message,
            text=ABOUT_TXT.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [styled_button('ʜᴏᴍᴇ', style="primary", callback_data='start'),
                 styled_button('ᴄʟᴏꜱᴇ', style="danger", callback_data='close')]
            ])
        )
        try:
            await query.answer()
        except Exception:
            pass

    elif data == "start":
        await _safe_edit(
            query.message,
            text=START_MSG.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [styled_button("ʜᴇʟᴘ", style="primary", callback_data='help'),
                 styled_button("ᴀʙᴏᴜᴛ", style="primary", callback_data='about')]
            ])
        )
        try:
            await query.answer()
        except Exception:
            pass

    elif data == "close":
        try:
            await query.message.delete()
        except Exception:
            pass
        try:
            await query.message.reply_to_message.delete()
        except Exception:
            pass

    elif data.startswith("rfs_ch_"):
        cid = int(data.split("_")[2])
        try:
            chat = await client.get_chat(cid)
            mode = await db.get_channel_mode(cid)
            status = "🟢 ᴏɴ" if mode == "on" else "🔴 ᴏғғ"
            new_mode = "off" if mode == "on" else "on"
            buttons = [
                [styled_button(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", style="primary", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
                [styled_button("‹ ʙᴀᴄᴋ", style="danger", callback_data="fsub_back")]
            ]
            await _safe_edit(
                query.message,
                f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            try:
                await query.answer()
            except Exception:
                pass
        except Exception:
            await query.answer("Failed to fetch channel info", show_alert=True)

    elif data.startswith("rfs_toggle_"):
        cid, action = data.split("_")[2:]
        cid = int(cid)
        mode = "on" if action == "on" else "off"

        await db.set_channel_mode(cid, mode)
        await query.answer(f"Force-Sub set to {'ON' if mode == 'on' else 'OFF'}")

        chat = await client.get_chat(cid)
        status = "🟢 ON" if mode == "on" else "🔴 OFF"
        new_mode = "off" if mode == "on" else "on"
        buttons = [
            [styled_button(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", style="primary", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
            [styled_button("‹ ʙᴀᴄᴋ", style="danger", callback_data="fsub_back")]
        ]
        await _safe_edit(
            query.message,
            f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == "fsub_back":
        channels = await db.show_channels()
        buttons = []
        for cid in channels:
            try:
                chat = await client.get_chat(cid)
                mode = await db.get_channel_mode(cid)
                status = "🟢" if mode == "on" else "🔴"
                buttons.append([styled_button(f"{status} {chat.title}", style="primary", callback_data=f"rfs_ch_{cid}")])
            except Exception:
                continue

        await _safe_edit(
            query.message,
            "sᴇʟᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛᴏɢɢʟᴇ ɪᴛs ғᴏʀᴄᴇ-sᴜʙ ᴍᴏᴅᴇ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        try:
            await query.answer()
        except Exception:
            pass
