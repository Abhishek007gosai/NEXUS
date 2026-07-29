import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait

# Automatic File Store link generation is intentionally disabled.
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

    status = await message.reply_text("Please Wait...!", quote=True)
    try:
        await message.copy(chat_id=client.db, disable_notification=True)
        await status.edit_text(
            "<b>✓ File stored successfully.</b>\n\n"
            "Automatic File Store link generation is disabled.\n"
            "Use <code>/genlink</code> or <code>/batch</code> to generate a link manually."
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
        try:
            await message.copy(chat_id=client.db, disable_notification=True)
            await status.edit_text(
                "<b>✓ File stored successfully.</b>\n\n"
                "Use <code>/genlink</code> or <code>/batch</code> to generate a link manually."
            )
        except Exception:
            await status.edit_text("Something went Wrong..!")
    except Exception as e:
        print(e)
        await status.edit_text("Something went Wrong..!")
