import asyncio
from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest
from pyrogram.errors import FloodWait, UserNotParticipant, UserAlreadyParticipant
from helper.helper_func import retry_on_flood

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
        await retry_on_flood(
            lambda: client.approve_chat_join_request(chat_id=chat.id, user_id=user.id),
            max_retries=3,
            label=f"approve:{chat.id}:{user.id}",
        )
    except UserAlreadyParticipant:
        return
    except Exception:
        return

    try:
        await retry_on_flood(
            lambda: client.send_message(
                chat_id=user.id,
                text=(
                    f"<b><blockquote>ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ᴛᴏ ᴊᴏɪɴ {chat.title} "
                    "ʜᴀs ʙᴇᴇɴ ᴀᴘᴘʀᴏᴠᴇᴅ.</blockquote></b>"
                ),
                protect_content=True,
            ),
            max_retries=2,
            label=f"approve_dm:{user.id}",
        )
    except Exception:
        pass
