import asyncio
import re
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError, UserNotParticipant
from helper.helper_func import encode

LINK_SHARE_PREFIX = "ls_"
LINK_SHARE_EXPIRY = 300


def is_admin(client, user_id):
    return user_id in client.admins


async def revoke_link_later(client, channel_id, invite_link):
    await asyncio.sleep(LINK_SHARE_EXPIRY)
    try:
        await client.revoke_chat_invite_link(channel_id, invite_link)
    except Exception as e:
        client.LOGGER(__name__, client.name).warning(f"Failed to revoke invite for {channel_id}: {e}")


@Client.on_callback_query(filters.regex(r"^link_share$"))
async def link_share_menu(client, query):
    if not is_admin(client, query.from_user.id):
        return await query.answer("Only admins can access this!", show_alert=True)
    buttons = [
        [InlineKeyboardButton("Aᴅᴅ Cʜᴀɴɴᴇʟ", callback_data="ls_add"), InlineKeyboardButton("Dᴇʟᴇᴛᴇ Cʜᴀɴɴᴇʟ", callback_data="ls_delete")],
        [InlineKeyboardButton("Nᴏʀᴍᴀʟ Lɪɴᴋs", callback_data="ls_normal"), InlineKeyboardButton("Rᴇǫᴜᴇsᴛ Lɪɴᴋs", callback_data="ls_request")],
        [InlineKeyboardButton("Lɪsᴛ Cʜᴀɴɴᴇʟs", callback_data="ls_list")],
        [InlineKeyboardButton("back", callback_data="settings")]
    ]
    await query.message.edit_text("<blockquote><b>In this you can change and view your channels...!!</b></blockquote>", reply_markup=InlineKeyboardMarkup(buttons))
    await query.answer()


@Client.on_callback_query(filters.regex(r"^ls_add$"))
async def link_share_add(client, query):
    if not is_admin(client, query.from_user.id):
        return await query.answer("Only admins can add channels!", show_alert=True)
    back = InlineKeyboardMarkup([[InlineKeyboardButton("back", callback_data="link_share")]])
    await query.message.edit_text("<b>Send the channel ID to add.\n\nExample: <code>-1001234567890</code>\n\n/cancel to cancel.</b>", reply_markup=back)
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
    await client.mongodb.add_link_share_channel(channel_id, {"name": chat.title, "username": chat.username, "added_at": datetime.utcnow(), "is_active": True})
    await msg.reply(f"<b>Channel <code>{chat.title}</code> ({channel_id}) has been added successfully.</b>", reply_markup=back)


@Client.on_callback_query(filters.regex(r"^ls_delete$"))
async def link_share_delete(client, query):
    if not is_admin(client, query.from_user.id):
        return await query.answer("Only admins can delete channels!", show_alert=True)
    channels = await client.mongodb.get_link_share_channels()
    if not channels:
        return await query.message.edit_text("<b>No Link Share channels found.</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("back", callback_data="link_share")]]))
    buttons = [[InlineKeyboardButton(data.get("name", cid), callback_data=f"ls_del:{cid}")] for cid, data in channels.items()]
    buttons.append([InlineKeyboardButton("back", callback_data="link_share")])
    await query.message.edit_text("<b>Select a channel to delete:</b>", reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r"^ls_del:-100\d+$"))
async def link_share_delete_confirm(client, query):
    if not is_admin(client, query.from_user.id):
        return await query.answer("Only admins can delete channels!", show_alert=True)
    channel_id = int(query.data.split(":", 1)[1])
    removed = await client.mongodb.remove_link_share_channel(channel_id)
    await query.answer("Channel deleted." if removed else "Channel not found.", show_alert=True)
    await link_share_menu(client, query)


async def show_link_channels(client, query, request_link=False):
    if not is_admin(client, query.from_user.id):
        return await query.answer("Only admins can access this!", show_alert=True)
    channels = await client.mongodb.get_link_share_channels()
    if not channels:
        return await query.message.edit_text("<b>No Link Share channels found. Add a channel first.</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("back", callback_data="link_share")]]))
    kind = "request" if request_link else "normal"
    buttons = [[InlineKeyboardButton(data.get("name", cid), callback_data=f"ls_gen:{kind}:{cid}")] for cid, data in channels.items()]
    buttons.append([InlineKeyboardButton("back", callback_data="link_share")])
    await query.message.edit_text(f"<b>{'Request Links' if request_link else 'Normal Links'}</b>\n\nSelect a channel:", reply_markup=InlineKeyboardMarkup(buttons))
    await query.answer()


@Client.on_callback_query(filters.regex(r"^ls_normal$"))
async def link_share_normal(client, query):
    await show_link_channels(client, query, False)


@Client.on_callback_query(filters.regex(r"^ls_request$"))
async def link_share_request(client, query):
    await show_link_channels(client, query, True)


@Client.on_callback_query(filters.regex(r"^ls_gen:(normal|request):-100\d+$"))
async def link_share_generate(client, query):
    if not is_admin(client, query.from_user.id):
        return await query.answer("Only admins can generate links!", show_alert=True)
    _, kind, channel_id_text = query.data.split(":", 2)
    channel_id = int(channel_id_text)
    channel = await client.mongodb.get_link_share_channel(channel_id)
    if not channel:
        return await query.answer("Channel no longer exists.", show_alert=True)
    try:
        payload = await encode(str(channel_id))
        if kind == "request":
            payload = "req_" + payload
        bot_link = f"https://t.me/{client.username}?start={LINK_SHARE_PREFIX}{payload}"
        button = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 sʜᴀʀᴇ ᴜʀʟ", url=f"https://telegram.me/share/url?url={bot_link}")]])
        await query.message.edit_text(f"<b>Link generated for {channel.get('name', channel_id)}.</b>\n\n<code>{bot_link}</code>", reply_markup=button)
        await query.answer("Link generated!")
    except Exception as e:
        client.LOGGER(__name__, client.name).error(f"Link generation failed: {e}")
        await query.answer("Failed to generate link.", show_alert=True)


@Client.on_callback_query(filters.regex(r"^ls_list$"))
async def link_share_list(client, query):
    if not is_admin(client, query.from_user.id):
        return await query.answer("Only admins can access this!", show_alert=True)
    channels = await client.mongodb.get_link_share_channels()
    if not channels:
        text = "<b>No Link Share channels configured.</b>"
    else:
        text = "<b>Link Share Channels</b>\n\n" + "\n\n".join(f"• <b>{data.get('name', 'Unknown')}</b>\n  <code>{cid}</code>" for cid, data in channels.items())
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("back", callback_data="link_share")]]))
    await query.answer()
