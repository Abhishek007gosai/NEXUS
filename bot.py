# made by botifyx-bots 
# support @BotifyX_Pro_Botz

import os
from threading import Thread
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime
from collections import OrderedDict
from config import LOGGER, PORT, OWNER_ID, SHORT_URL, SHORT_API, SHORT_TUT
from helper import MongoDB

version = "v2.0.0"

# ──────────────────────────────
# Flask = Anime Index mini app (Touka) + health endpoint
# ──────────────────────────────

from app import app as flask_app, set_bot_client


@flask_app.route("/bot-health")
def bot_health():
    return "Bot is running!", 200


def run_flask():
    import logging
    import sys

    class _Quiet(logging.Filter):
        def filter(self, record):
            msg = record.getMessage()
            if "Serving Flask app" in msg or "Debug mode" in msg or "Running on" in msg:
                return False
            return True

    for name in ("werkzeug", "flask", "flask.app"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.ERROR)
        lg.addFilter(_Quiet())

    # Also quiet the root handler that werkzeug attaches
    logging.getLogger("werkzeug").disabled = True

    port = int(os.environ.get("PORT", PORT or 10000))
    # flask/werkzeug still write the banner via click to stderr in some versions
    _real_stderr = sys.stderr

    class _StderrFilter:
        def __init__(self, real):
            self._real = real
        def write(self, s):
            if not s:
                return 0
            if "Serving Flask app" in s or "Debug mode" in s or "Running on" in s or "Press CTRL" in s:
                return len(s)
            return self._real.write(s)
        def flush(self):
            return self._real.flush()
        def __getattr__(self, name):
            return getattr(self._real, name)

    sys.stderr = _StderrFilter(_real_stderr)
    try:
        flask_app.run(
            host="0.0.0.0",
            port=port,
            threaded=True,
            use_reloader=False,
        )
    finally:
        sys.stderr = _real_stderr


#================================================

class Bot(Client):
    def __init__(self, session, workers, db, fsub, token, admins, messages, auto_del, db_uri, db_name, api_id, api_hash, protect, disable_btn):
        super().__init__(
            name=session,
            api_hash=api_hash,
            api_id=api_id,
            plugins={
                "root": "plugins"
            },
            workers=workers,
            bot_token=token
        )
        self.LOGGER = LOGGER
        self.name = session
        self.db = db
        self.fsub = fsub
        self.owner = OWNER_ID
        self.fsub_dict = OrderedDict()  # preserve channel order across restarts
        self.admins = admins + [OWNER_ID] if OWNER_ID not in admins else admins
        self.messages = messages
        self.auto_del = int(auto_del or 0)
        self.protect = protect
        self.req_fsub = {}
        self.disable_btn = disable_btn
        self.reply_text = messages.get('REPLY', 'ғᴜᴄᴋ ᴏғғ ʙɪᴛᴄʜ !!!')
        self.mongodb = MongoDB(db_uri, db_name)
        self.req_channels = []
        self.db_channels = {}
        self.primary_db_channel = db

    async def start(self):
        await super().start()
        # Colored buttons need Kurigram; ask/listen without external pyromod
        try:
            from helper.pyro_listen import install_listen
            install_listen(self)
        except Exception as e:
            self.LOGGER(__name__, self.name).warning(f"install_listen: {e}")
        try:
            import pyrogram
            from pyrogram.enums import ButtonStyle as _BS
            self.LOGGER(__name__, self.name).info(
                f"Library: pyrogram/kurigram {pyrogram.__version__} | ButtonStyle OK ({_BS.DANGER.value})"
            )
        except Exception as e:
            self.LOGGER(__name__, self.name).warning(
                f"ButtonStyle NOT available — buttons will be uncolored: {e}"
            )
        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()

        if len(self.fsub) > 0:
            for channel in self.fsub:
                try:
                    chat = await self.get_chat(channel[0])
                    name = chat.title
                    link = None

                    if not channel[1]:
                        link = chat.invite_link

                    if not link and not channel[2]:
                        chat_link = await self.create_chat_invite_link(
                            channel[0],
                            creates_join_request=channel[1]
                        )
                        link = chat_link.invite_link

                    if not channel[1]:
                        self.fsub_dict[channel[0]] = [name, link, False, 0]

                    if channel[1]:
                        self.fsub_dict[channel[0]] = [name, link, True, 0]
                        self.req_channels.append(channel[0])

                    if channel[2] > 0:
                        self.fsub_dict[channel[0]] = [name, None, channel[1], channel[2]]

                except Exception as e:
                    self.LOGGER(__name__, self.name).warning(
                        "Bot can't Export Invite link from Force Sub Channel!"
                    )
                    self.LOGGER(__name__, self.name).warning("\nBot Stopped.")
                    sys.exit()

        try:
            # Load DB channels in the exact order they were saved (OrderedDict).
            # Config FSUBS were already inserted above in config order; DB-only
            # channels are appended in their stored order so restart layout
            # (join buttons + admin list) stays stable.
            db_fsub_channels = await self.mongodb.get_fsub_channels()

            for channel_id_str, channel_data in db_fsub_channels.items():
                channel_id = int(channel_id_str)

                if channel_id in self.fsub_dict:
                    continue

                try:
                    chat = await self.get_chat(channel_id)
                    name = chat.title
                    channel_data[0] = name
                    self.fsub_dict[channel_id] = channel_data

                    if channel_data[2]:
                        self.req_channels.append(channel_id)

                except Exception as e:
                    self.LOGGER(__name__, self.name).warning(
                        f"Could not load dynamic fsub channel {channel_id}: {e}"
                    )
                    await self.mongodb.remove_fsub_channel(channel_id)

            # Re-save full ordered map so next restart matches current order
            # (migrates legacy dict storage → ordered list on first run).
            if self.fsub_dict:
                await self.mongodb.set_fsub_channels(self.fsub_dict)

        except Exception as e:
            self.LOGGER(__name__, self.name).warning(
                f"Error loading dynamic fsub channels: {e}"
            )

        await self.mongodb.set_channels(self.req_channels)

        try:
            db_channels_data = await self.mongodb.get_db_channels()
            self.db_channels = {}
            self.primary_db_channel = self.db

            for channel_id_str, channel_data in db_channels_data.items():
                channel_id = int(channel_id_str)

                try:
                    chat = await self.get_chat(channel_id)
                    channel_data['name'] = chat.title
                    self.db_channels[channel_id_str] = channel_data

                    if channel_data.get('is_primary', False):
                        self.primary_db_channel = channel_id
                        self.db = channel_id

                except Exception as e:
                    self.LOGGER(__name__, self.name).warning(
                        f"Could not load DB channel {channel_id}: {e}"
                    )
                    await self.mongodb.remove_db_channel(channel_id)

        except Exception as e:
            self.LOGGER(__name__, self.name).warning(
                f"Error loading DB channels: {e}"
            )

        # Load persisted message settings. Custom file captions are stored in MongoDB,
        # so they are not required in config.py.
        try:
            persisted_messages = await self.mongodb.get_messages_settings()
            if persisted_messages:
                self.messages.update(persisted_messages)
        except Exception as e:
            self.LOGGER(__name__, self.name).warning(
                f"Error loading persisted message settings: {e}"
            )

        try:
            shortner_settings = await self.mongodb.get_shortner_settings()

            self.short_url = shortner_settings.get('short_url', SHORT_URL)
            self.short_api = shortner_settings.get('short_api', SHORT_API)
            self.tutorial_link = shortner_settings.get('tutorial_link', SHORT_TUT)
            self.shortner_enabled = shortner_settings.get('enabled', True)

        except Exception as e:
            self.LOGGER(__name__, self.name).warning(
                f"Error loading shortner settings: {e}"
            )

            self.short_url = SHORT_URL
            self.short_api = SHORT_API
            self.tutorial_link = SHORT_TUT
            self.shortner_enabled = True

        try:
            db_channel = await self.get_chat(self.db)
            self.db_channel = db_channel

            test = await self.send_message(
                chat_id=db_channel.id,
                text="Testing Message by @ProYato"
            )

            await test.delete()

            self.LOGGER(__name__, self.name).info(
                f"Primary DB Channel: {self.primary_db_channel}"
            )

            self.LOGGER(__name__, self.name).info(
                f"Total DB Channels: {len(self.db_channels)}"
            )

        except Exception as e:
            self.LOGGER(__name__, self.name).warning(e)

            self.LOGGER(__name__, self.name).warning(
                f"Make Sure bot is Admin in DB Channel, and Double check the database channel Value, Current Value {self.db}"
            )

            self.LOGGER(__name__, self.name).info(
                "\nBot Stopped. Join https://t.me/BotifyX_Pro_Botz for support"
            )

            sys.exit()

        self.LOGGER(__name__, self.name).info("Bot Started!!")

        try:
            restart_message = "<b>›› ʜᴇʏ sᴇɴᴘᴀɪ!!\n ɪ'ᴍ ᴀʟɪᴠᴇ ɴᴏᴡ 🍃...</b>"

            await self.send_message(
                chat_id=self.owner,
                text=restart_message
            )

        except Exception:
            pass

        self.username = usr_bot_me.username

        # Polling mode: clear leftover webhook (silent)
        try:
            import requests as _req
            from config import TOKEN as _tok
            if _tok:
                _req.get(
                    f"https://api.telegram.org/bot{_tok}/deleteWebhook",
                    params={"drop_pending_updates": "true"},
                    timeout=15,
                )
        except Exception:
            pass

        # Share Pyrogram client with the mini-app (invite links / logs)
        try:
            set_bot_client(self)
        except Exception as e:
            self.LOGGER(__name__, self.name).warning(f"set_bot_client: {e}")

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__, self.name).info("Bot stopped.")


# ============================================
# FIXED WEB APP
# ============================================

async def web_app():
    return
