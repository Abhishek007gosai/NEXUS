import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait

# Automatic File Store link generation is disabled.
# Files/messages are still copied into the database channel. Use /genlink or /batch
# to manually generate File Store links.

@Client.on_message(filters.private & ~filters.command([
    'start', 'shortner', 'users', 'broadcast', 'batch', 'genlink', 'stats',
    'pbroadcast', 'db', 'adddb', 'add_db', 'removedb', 'rm_db', 'ban', 'unban',
    'addpremium', 'delpremium', 'premiumusers', 'request', 'profile'
]))
async def channel_post(client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)

    try:
        await message.copy(chat_id=client.db, disable_notification=True)
        # No success/automatic-link-generation message is sent.
    except FloodWait as e:
        await asyncio.sleep(e.value)
        try:
            await message.copy(chat_id=client.db, disable_notification=True)
        except Exception:
            pass
    except Exception as e:
        print(e)
