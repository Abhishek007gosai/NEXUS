import asyncio
from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest
from pyrogram.errors import FloodWait, UserNotParticipant, UserAlreadyParticipant

# Auto-approve is enabled and intentionally sends text only: no photo and no buttons.
@Client.on_chat_join_request(filters.channel | filters.group)
async def auto_approve(client, request: ChatJoinRequest):
    chat = request.chat
    user = request.from_user

    await asyncio.sleep(2)

    try:
        member = await client.get_chat_member(chat.id, user.id)
        if str(member.status) in {"member", "administrator", "owner", "creator"}:
            return
    except UserNotParticipant:
        pass
    except Exception:
        return

    try:
        await client.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
    except UserAlreadyParticipant:
        return
    except FloodWait as e:
        await asyncio.sleep(e.value)
        try:
            await client.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
        except Exception:
            return
    except Exception:
        return

    try:
        await client.send_message(
            chat_id=user.id,
            text=(
                f"<b><blockquote>ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ᴛᴏ ᴊᴏɪɴ {chat.title} "
                "ʜᴀs ʙᴇᴇɴ ᴀᴘᴘʀᴏᴠᴇᴅ.</blockquote></b>"
            ),
            protect_content=True
        )
    except Exception:
        pass
