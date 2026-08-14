from aiohttp import web
from plugins import web_server
import asyncio
import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys, pytz
from datetime import datetime
#rohit_1888 on Tg
from config import *


name ="""
 BY CODEFLIX BOTS
"""

def get_indian_time():
    """Returns the current time in IST."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist)



class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={
                "root": "plugins"
            },
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN
        )
        self.LOGGER = LOGGER

    async def start(self):
        await super().start()
        usr_bot_me = await self.get_me()
        self.uptime = get_indian_time()
        self.username = usr_bot_me.username
        self.db_channels = {}  # id -> chat object / meta
        self.primary_db_channel_id = CHANNEL_ID

        # Load multiple DB channels from Mongo (if any)
        try:
            from database.database import db as mongo_db
            # Ensure env CHANNEL_ID is registered as a DB channel
            if CHANNEL_ID:
                existing = await mongo_db.get_db_channels()
                if str(CHANNEL_ID) not in existing:
                    try:
                        chat = await self.get_chat(CHANNEL_ID)
                        await mongo_db.add_db_channel(CHANNEL_ID, title=getattr(chat, "title", str(CHANNEL_ID)), is_primary=True)
                    except Exception:
                        await mongo_db.add_db_channel(CHANNEL_ID, title=str(CHANNEL_ID), is_primary=True)

            channels = await mongo_db.get_db_channels()
            primary = await mongo_db.get_primary_db_channel()
            if primary:
                self.primary_db_channel_id = primary

            for cid_str, meta in channels.items():
                if not meta.get("is_active", True):
                    continue
                try:
                    cid = int(cid_str)
                    chat = await self.get_chat(cid)
                    self.db_channels[cid] = chat
                    # verify bot can post
                    test = await self.send_message(chat_id=cid, text="Test Message")
                    await test.delete()
                except Exception as e:
                    self.LOGGER(__name__).warning(f"DB channel {cid_str} unavailable: {e}")

            # Primary chat object
            primary_id = self.primary_db_channel_id
            if primary_id in self.db_channels:
                self.db_channel = self.db_channels[primary_id]
            elif CHANNEL_ID:
                db_channel = await self.get_chat(CHANNEL_ID)
                self.db_channel = db_channel
                self.db_channels[CHANNEL_ID] = db_channel
            else:
                raise RuntimeError("No DB channel configured")

            self.LOGGER(__name__).info(
                f"Primary DB Channel: {self.db_channel.id} | Total DB Channels: {len(self.db_channels)}"
            )
        except Exception as e:
            self.LOGGER(__name__).warning(e)
            self.LOGGER(__name__).warning(
                f"Make Sure bot is Admin in DB Channel, and Double check CHANNEL_ID. Current: {CHANNEL_ID}"
            )
            self.LOGGER(__name__).info("\nBot Stopped. Join https://t.me/CodeflixSupport for support")
            sys.exit()

        self.set_parse_mode(ParseMode.HTML)
        self.LOGGER(__name__).info(f"Bot Running..! Made by @Codeflix_Bots")

        # Start Web Server
        try:
            app = web.AppRunner(await web_server())
            await app.setup()
            await web.TCPSite(app, "0.0.0.0", PORT).start()
        except Exception as e:
            self.LOGGER(__name__).warning(f"Web server failed to start: {e}")

        try:
            await self.send_message(OWNER_ID, text="<b><blockquote> Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ</blockquote></b>")
        except Exception:
            pass

        # Start durable auto-delete worker (for /dbroadcast long timers e.g. 1 day)
        try:
            from plugins.broadcast import pending_delete_worker
            asyncio.create_task(pending_delete_worker(self))
            self.LOGGER(__name__).info("Pending-delete worker started (durable /dbroadcast)")
        except Exception as e:
            self.LOGGER(__name__).warning(f"Could not start pending-delete worker: {e}")

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

    def run(self):
        """Run the bot."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        self.LOGGER(__name__).info("Bot is now running. Thanks to @rohit_1888")
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            self.LOGGER(__name__).info("Shutting down...")
        finally:
            loop.run_until_complete(self.stop())

#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.
