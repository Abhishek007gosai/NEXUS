from pyrogram import Client, filters
from pyrogram.raw.types import MessageActionPinMessage
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant, Forbidden, PeerIdInvalid, ChatAdminRequired
import asyncio
from helper.helper_func import retry_on_flood, sleep_on_flood, safe_delete

#===============================================================#

@Client.on_message(filters.command('users'))
async def user_count(client, message):
    if not message.from_user.id in client.admins:
        return await client.send_message(message.from_user.id, client.reply_text)
    total_users = await client.mongodb.full_userbase()
    await message.reply(f"**{len(total_users)} Users are using this bot currently!**")

#===============================================================#

@Client.on_message(filters.private & filters.command('broadcast'))
async def send_text(client, message):
    admin_ids = client.admins
    user_id = message.from_user.id
    if user_id in admin_ids:

        if message.reply_to_message:
            query = await client.mongodb.full_userbase()
            broadcast_msg = message.reply_to_message
            total = 0
            successful = 0
            blocked = 0
            deleted = 0
            unsuccessful = 0

            pls_wait = await message.reply("<blockquote><i>Broadcasting Message.. This will Take Some Time</i></blockquote>")
            for chat_id in query:
                try:
                    await retry_on_flood(
                        lambda cid=chat_id: broadcast_msg.copy(cid),
                        max_retries=5,
                        label=f"broadcast:{chat_id}",
                    )
                    successful += 1
                except UserIsBlocked:
                    await client.mongodb.del_user(chat_id)
                    blocked += 1
                except InputUserDeactivated:
                    await client.mongodb.del_user(chat_id)
                    deleted += 1
                except Exception as e:
                    print(f"Failed to send message to {chat_id}: {e}")
                    unsuccessful += 1
                total += 1
                # Light pacing to reduce mass flood
                await asyncio.sleep(0.05)

            status = f"""<blockquote><b><u>Broadcast Completed</u></b></blockquote>
    <blockquote expandable><b>Total Users :</b> <code>{total}</code>
    <b>Successful :</b> <code>{successful}</code>
    <b>Blocked Users :</b> <code>{blocked}</code>
    <b>Deleted Accounts :</b> <code>{deleted}</code>
    <b>Unsuccessful :</b> <code>{unsuccessful}</code><blockquote>"""

            return await pls_wait.edit(status)

        else:
            msg = await message.reply(f"Use This Command As A Reply To Any Telegram Message Without Any Spaces.")
            await asyncio.sleep(8)
            try:
                await safe_delete(msg)
            except Exception:
                pass

#===============================================================#

@Client.on_message(filters.private & filters.command('pbroadcast'))
async def pin_bdcst_text(client, message):
    admin_ids = client.admins
    user_id = message.from_user.id
    if user_id in admin_ids:
        if message.reply_to_message:
            query = await client.mongodb.full_userbase()
            broadcast_msg = message.reply_to_message
            total = 0
            successful = 0
            blocked = 0
            deleted = 0
            unsuccessful = 0

            pls_wait = await message.reply("<blockquote><i>Broadcasting Message.. This will Take Some Time</i></blockquote>")

            for chat_id in query:
                try:
                    sent_msg = await retry_on_flood(
                        lambda cid=chat_id: broadcast_msg.copy(cid),
                        max_retries=5,
                        label=f"pbroadcast:{chat_id}",
                    )
                    successful += 1
                    try:
                        await retry_on_flood(
                            lambda: client.pin_chat_message(
                                chat_id=chat_id, message_id=sent_msg.id, both_sides=True
                            ),
                            max_retries=3,
                            label=f"pin:{chat_id}",
                        )
                    except Exception:
                        pass
                except UserIsBlocked:
                    await client.mongodb.del_user(chat_id)
                    blocked += 1
                except InputUserDeactivated:
                    await client.mongodb.del_user(chat_id)
                    deleted += 1
                except Exception as e:
                    print(f"Failed to send message to {chat_id}: {e}")
                    unsuccessful += 1
                total += 1
                await asyncio.sleep(0.05)

            status = f"""<blockquote><b><u>Broadcast Completed</u></b></blockquote>
    <b>Total Users :</b> <code>{total}</code>
    <b>Successful :</b> <code>{successful}</code>
    <b>Blocked Users :</b> <code>{blocked}</code>
    <b>Deleted Accounts :</b> <code>{deleted}</code>
    <b>Unsuccessful :</b> <code>{unsuccessful}</code>"""

            return await pls_wait.edit(status)

        else:
            msg = await message.reply("Use This Command As A Reply To Any Telegram Message Without Any Spaces.")
            await asyncio.sleep(8)
            await safe_delete(msg)
    