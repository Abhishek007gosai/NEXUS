# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport
#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.
#

import os
from os import environ,getenv
import logging
from logging.handlers import RotatingFileHandler

#rohit_1888 on Tg
#--------------------------------------------
#Bot token @Botfather
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
APP_ID = int(os.environ.get("APP_ID", "0") or "0")  # Your API ID from my.telegram.org
API_HASH = os.environ.get("API_HASH", "") #Your API Hash from my.telegram.org
#--------------------------------------------

# Primary DB channel (files stored here). Can also add more via /adddbchnl
_channel_raw = os.environ.get("CHANNEL_ID", "") or "0"
CHANNEL_ID = int(_channel_raw) if str(_channel_raw).lstrip("-").isdigit() else 0

OWNER = os.environ.get("OWNER", "")  # Owner username without @
_owner_raw = os.environ.get("OWNER_ID", "") or "0"
OWNER_ID = int(_owner_raw) if str(_owner_raw).isdigit() else 0
#--------------------------------------------
PORT = os.environ.get("PORT", "8001")
#--------------------------------------------
# For Multiple Database URL Use One Space Between Each
# Example: DB_URI="mongodb://uri1 mongodb://uri2 mongodb://uri3"
# (also accepts DATABASE_URL for backward compatibility)
# The bot will try them in order and use the first one that connects.
# If one database gets full / unreachable, put a working URI first (or remove the full one).
_db_env = os.getenv("DB_URI", "") or os.getenv("DATABASE_URL", "")
DB_URI = [u for u in _db_env.split() if u.strip()]
DB_NAME = os.environ.get("DATABASE_NAME", "") or os.environ.get("DB_NAME", "cluster0")
#--------------------------------------------
FSUB_LINK_EXPIRY = int(os.getenv("FSUB_LINK_EXPIRY", "120"))  # 0 means no expiry
BAN_SUPPORT = os.environ.get("BAN_SUPPORT", "https://t.me/EternalsHelplineBot")
TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "200"))

START_PIC = os.environ.get("START_PIC", "")
FORCE_PIC = os.environ.get("FORCE_PIC", "")
#--------------------------------------------

#--------------------------------------------
HELP_TXT = "<blockquote><b>ʜᴇʏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴜᴘᴘᴏʀᴛ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ʏᴏᴜ ᴄᴀɴ ᴅᴏ sᴏ ʙʏ sᴜʙsᴄʀɪʙɪɴɢ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴛʜᴀɴᴋs Fᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ\n❏ ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅs\n├/start : sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ\n\nsɪᴍᴘʟʏ ᴄʟɪᴄᴋ ᴏɴ ʟɪɴᴋ ᴀɴᴅ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ᴊᴏɪɴ ʙᴏᴛʜ ᴄʜᴀɴɴᴇʟs ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ ᴛʜᴀᴛs ɪᴛ.</b></blockquote></b>"
ABOUT_TXT = "<b>◈sᴜᴘʀᴇᴀᴍ : <a href='https://t.me/AnimeNexusNetwork'>ɴᴇᴛᴡᴏʀᴋ</a>\n◈ᴀɴɪᴍᴇ : <a href='https://t.me/KafkaX_Bot?start=LTEwMDE0NTczMTMwMjg'>ᴇᴛᴇʀɴᴀʟꜱ</a>\n◈ᴏɴɢᴏɪɴɢ: <a href='https://t.me/KafkaX_Bot?start=LTEwMDIxOTA2MTY5ODA'>ᴀɪʀɪɴɢꜱ</a>\n◈ᴇᴄᴄʜɪ : <a href='https://t.me/Ecchi_Dex'>ᴇᴄᴄʜɪ ᴅᴇx</a>\n◈ʜᴇʟᴘʟɪɴᴇ : <a href='https://t.me/EternalsHelplineBot'>ʜᴇʟᴘʟɪɴᴇ</a></b>"
#--------------------------------------------
#--------------------------------------------
START_MSG = os.environ.get("START_MESSAGE", "<b>ʜᴇʏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴜᴘᴘᴏʀᴛ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ʏᴏᴜ ᴄᴀɴ ᴅᴏ sᴏ ʙʏ sᴜʙsᴄʀɪʙɪɴɢ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ\n\nᴛʜᴀɴᴋs ғᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ</b>")
FORCE_MSG = os.environ.get("FORCE_SUB_MESSAGE", "<b><blockquote>ʜᴇʟʟᴏ {mention} ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ <a href='https://t.me/KafkaX_Bot?start=LTEwMDE0NTczMTMwMjg='>ᴇᴛᴇʀɴᴀʟs</a></blockquote>ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ/ɢʀᴏᴜᴘ ғɪʀsᴛ, ᴘʟᴇᴀsᴇ sᴜʙsᴄʀɪʙᴇ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ᴛʜʀᴏᴜɢʜ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴀɴᴅ sᴛᴀʀᴛ ʙᴏᴛ ᴀɢᴀɪɴ<blockquote>ʜᴏᴡ ᴛᴏ ᴜsᴇ ʙᴏᴛ <a href=https://t.me/NexusTutorial/6>ᴛᴜᴛᴏʀɪᴀʟ ᴄʟɪᴄᴋ ʜᴇʀᴇ</a></blockquote></b>")

USER_CMD_TXT = """<blockquote><b>» ᴜsᴇʀ ᴄᴏᴍᴍᴀɴᴅs:</b></blockquote>

<b>›› /start :</b> sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ
<b>›› /cmd :</b> sʜᴏᴡ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs
<b>›› /help :</b> ʜᴇʟᴘ & ʜᴏᴡ ᴛᴏ ᴜsᴇ
"""

CMD_TXT = """<blockquote><b>» ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs:</b></blockquote>

<b>›› /dlt_time :</b> sᴇᴛ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ
<b>›› /check_dlt_time :</b> ᴄʜᴇᴄᴋ ᴄᴜʀʀᴇɴᴛ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ
<b>›› /broadcast :</b> ʙʀᴏᴀᴅᴄᴀsᴛ ᴍᴇssᴀɢᴇ ᴛᴏ ᴀʟʟ ᴜsᴇʀs
<b>›› /dbroadcast :</b> ʙʀᴏᴀᴅᴄᴀsᴛ ᴅᴏᴄᴜᴍᴇɴᴛ / ᴠɪᴅᴇᴏ
<b>›› /pbroadcast :</b> sᴇɴᴅ ᴘʜᴏᴛᴏ ᴛᴏ ᴀʟʟ ᴜꜱᴇʀs
<b>›› /ban :</b> ʙᴀɴ ᴀ ᴜꜱᴇʀ
<b>›› /unban :</b> ᴜɴʙᴀɴ ᴀ ᴜꜱᴇʀ
<b>›› /banlist :</b> ɢᴇᴛ ʟɪsᴛ ᴏꜰ ʙᴀɴɴᴇᴅ ᴜꜱᴇʀs
<b>›› /users :</b> ᴛᴏᴛᴀʟ ᴜsᴇʀs ᴄᴏᴜɴᴛ
<b>›› /stats :</b> ᴅᴇᴛᴀɪʟᴇᴅ ʙᴏᴛ / ᴅʙ / sᴇʀᴠᴇʀ sᴛᴀᴛs (ᴏᴡɴᴇʀ ᴏɴʟʏ)
<b>›› /addchnl :</b> ᴀᴅᴅ ꜰᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ
<b>›› /delchnl :</b> ʀᴇᴍᴏᴠᴇ ꜰᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ
<b>›› /listchnl :</b> ᴠɪᴇᴡ ꜰᴏʀᴄᴇ-sᴜʙ ᴄʜᴀɴɴᴇʟs
<b>›› /fsub_mode :</b> ᴛᴏɢɢʟᴇ ꜰᴏʀᴄᴇ sᴜʙ ᴍᴏᴅᴇ
<b>›› /delreq :</b> ᴄʟᴇᴀɴ ʟᴇғᴛᴏᴠᴇʀ ᴊᴏɪɴ-ʀᴇǫᴜᴇsᴛ ᴜsᴇʀs
<b>›› /add_admin :</b> ᴀᴅᴅ ᴀɴ ᴀᴅᴍɪɴ
<b>›› /deladmin :</b> ʀᴇᴍᴏᴠᴇ ᴀɴ ᴀᴅᴍɪɴ
<b>›› /admins :</b> ɢᴇᴛ ʟɪsᴛ ᴏꜰ ᴀᴅᴍɪɴs
<b>›› /batch :</b> ɢᴇɴᴇʀᴀᴛᴇ ʙᴀᴛᴄʜ ʟɪɴᴋ
<b>›› /genlink :</b> ɢᴇɴᴇʀᴀᴛᴇ sɪɴɢʟᴇ ʟɪɴᴋ
<b>›› /custom_batch :</b> ᴄᴜsᴛᴏᴍ ʙᴀᴛᴄʜ ʟɪɴᴋ
<blockquote><b>» ᴅʙ ᴄʜᴀɴɴᴇʟ ᴄᴏᴍᴍᴀɴᴅs:</b></blockquote>
<b>›› /adddbchnl :</b> ᴀᴅᴅ ᴀ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟ
<b>›› /deldbchnl :</b> ʀᴇᴍᴏᴠᴇ ᴀ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟ
<b>›› /listdbchnl :</b> ʟɪsᴛ ᴀʟʟ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs
<b>›› /setdbchnl :</b> sᴇᴛ ᴘʀɪᴍᴀʀʏ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟ
"""
#--------------------------------------------
CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", "") #set your Custom Caption here, Keep None for Disable Custom Caption
PROTECT_CONTENT = True if os.environ.get('PROTECT_CONTENT', "False") == "True" else False #set True if you want to prevent users from forwarding files from bot
#--------------------------------------------
BOT_STATS_TEXT = "<b>BOT UPTIME</b>\n{uptime}"
USER_REPLY_TEXT = "Sᴏʀʀʏ... ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴀ sɪɢᴍᴀ"
#--------------------------------------------


LOG_FILE_NAME = "filesharingbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
   
