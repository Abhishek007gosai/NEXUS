# Multiple Database Channel management
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup
from pyrogram.enums import ChatMemberStatus, ChatType
from bot import Bot
from config import *
from helper_func import admin, styled_button
from database.database import db


@Bot.on_message(filters.command(["cmd", "cmds", "commands"]) & filters.private)
async def show_commands(client: Client, message: Message):
    """Show all available commands. Admins see full list."""
    user_id = message.from_user.id
    is_admin = user_id == OWNER_ID or await db.admin_exist(user_id)

    text = USER_CMD_TXT
    if is_admin:
        text = USER_CMD_TXT + "\n" + CMD_TXT

    await message.reply(
        text,
        reply_markup=InlineKeyboardMarkup(
            [[styled_button("• ᴄʟᴏsᴇ •", style="danger", callback_data="close")]]
        ),
        quote=True,
        disable_web_page_preview=True,
    )


@Bot.on_message(filters.command("adddbchnl") & filters.private & admin)
async def add_db_channel(client: Client, message: Message):
    temp = await message.reply("<b><i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i></b>", quote=True)
    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        return await temp.edit(
            "<b>Usage:</b> <code>/adddbchnl -100xxxxxxxxxx</code>\n\n"
            "Bot must be admin in that channel."
        )
    try:
        chat_id = int(args[1])
    except ValueError:
        return await temp.edit("❌ Invalid channel ID")

    existing = await db.get_db_channels()
    if str(chat_id) in existing:
        return await temp.edit(f"Already added:\n<code>{chat_id}</code>")

    try:
        chat = await client.get_chat(chat_id)
        if chat.type not in [ChatType.CHANNEL, ChatType.SUPERGROUP]:
            return await temp.edit("❌ Only channels/supergroups allowed.")
        member = await client.get_chat_member(chat.id, "me")
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await temp.edit("❌ Bot must be admin in that channel.")

        # quick write test
        try:
            t = await client.send_message(chat.id, "DB Channel test")
            await t.delete()
        except Exception as e:
            return await temp.edit(f"❌ Cannot post in channel:\n<code>{e}</code>")

        is_primary = len(existing) == 0
        await db.add_db_channel(chat_id, title=chat.title or str(chat_id), is_primary=is_primary)

        # hot-reload into client
        client.db_channels[chat_id] = chat
        if is_primary:
            client.db_channel = chat
            client.primary_db_channel_id = chat_id

        return await temp.edit(
            f"✅ DB channel added!\n\n"
            f"<b>Name:</b> {chat.title}\n"
            f"<b>ID:</b> <code>{chat_id}</code>\n"
            f"<b>Primary:</b> {'Yes' if is_primary else 'No'}\n\n"
            f"Use /setdbchnl to change primary."
        )
    except Exception as e:
        return await temp.edit(f"❌ Failed:\n<code>{e}</code>")


@Bot.on_message(filters.command("deldbchnl") & filters.private & admin)
async def del_db_channel(client: Client, message: Message):
    temp = await message.reply("<b><i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i></b>", quote=True)
    args = message.text.split(maxsplit=1)
    channels = await db.get_db_channels()
    if len(args) != 2:
        return await temp.edit("<b>Usage:</b> <code>/deldbchnl &lt;channel_id&gt;</code>")
    try:
        chat_id = int(args[1])
    except ValueError:
        return await temp.edit("❌ Invalid channel ID")
    if str(chat_id) not in channels:
        return await temp.edit(f"❌ Not in DB channel list:\n<code>{chat_id}</code>")
    if len(channels) <= 1:
        return await temp.edit("❌ Cannot remove the last DB channel.")

    await db.remove_db_channel(chat_id)
    client.db_channels.pop(chat_id, None)
    primary = await db.get_primary_db_channel()
    if primary and primary in client.db_channels:
        client.db_channel = client.db_channels[primary]
        client.primary_db_channel_id = primary
    return await temp.edit(f"✅ Removed DB channel:\n<code>{chat_id}</code>")


@Bot.on_message(filters.command("listdbchnl") & filters.private & admin)
async def list_db_channels(client: Client, message: Message):
    temp = await message.reply("<b><i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i></b>", quote=True)
    channels = await db.get_db_channels()
    if not channels:
        return await temp.edit("❌ No DB channels configured.")
    lines = ["<b>⚡ Database Channels:</b>\n"]
    for cid, meta in channels.items():
        mark = "⭐ PRIMARY" if meta.get("is_primary") else ""
        active = "🟢" if meta.get("is_active", True) else "🔴"
        title = meta.get("title", cid)
        lines.append(f"{active} <b>{title}</b> [<code>{cid}</code>] {mark}")
    await temp.edit(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            [[styled_button("• ᴄʟᴏsᴇ •", style="danger", callback_data="close")]]
        ),
    )


@Bot.on_message(filters.command("setdbchnl") & filters.private & admin)
async def set_primary_db_channel(client: Client, message: Message):
    temp = await message.reply("<b><i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i></b>", quote=True)
    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        return await temp.edit("<b>Usage:</b> <code>/setdbchnl &lt;channel_id&gt;</code>")
    try:
        chat_id = int(args[1])
    except ValueError:
        return await temp.edit("❌ Invalid channel ID")
    ok = await db.set_primary_db_channel(chat_id)
    if not ok:
        return await temp.edit("❌ Channel not in DB list. Add it with /adddbchnl first.")
    if chat_id in client.db_channels:
        client.db_channel = client.db_channels[chat_id]
    else:
        try:
            chat = await client.get_chat(chat_id)
            client.db_channels[chat_id] = chat
            client.db_channel = chat
        except Exception as e:
            return await temp.edit(f"❌ Cannot access channel:\n<code>{e}</code>")
    client.primary_db_channel_id = chat_id
    return await temp.edit(f"✅ Primary DB channel set to:\n<code>{chat_id}</code>")
