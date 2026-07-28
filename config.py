import os
import logging
from logging.handlers import RotatingFileHandler

# Logging
LOG_FILE_NAME = "bot.log"
PORT = 5010

OWNER_ID = int(os.getenv("OWNER_ID", "8771195193"))
MSG_EFFECT =  5046509860389126442

# Shortener
SHORT_URL = os.getenv("SHORT_URL", "")
SHORT_API = os.getenv("SHORT_API", "")
SHORT_TUT = os.getenv("SHORT_TUT", "")

# Telegram
SESSION = os.getenv("SESSION", "Kaya")
TOKEN = os.getenv("TOKEN", "")
API_ID = int(os.getenv("API_ID", "29245477"))
API_HASH = os.getenv("API_HASH", "0abc83883262245c90ca337b7a0375c4")
WORKERS = int(os.getenv("WORKERS", "5"))

# MongoDB
DB_URI = os.getenv("DB_URI", "")
DB_NAME = "cluster0"
# Force Subscribe
FSUBS = [[-1002369123167, True, 5]] 
# Channels
DB_CHANNEL =  -1002497924209

# Auto Delete
AUTO_DEL = "300"

# Admins
ADMINS = [8771195193]

# Bot Settings
DISABLE_BTN = os.getenv("DISABLE_BTN", "True").lower() == "true"
PROTECT = os.getenv("PROTECT", "False").lower() == "true"

# Messages
MESSAGES = {
"START": "<b>ʜᴇʏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴄᴏᴍᴍᴜɴɪᴛʏ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴜᴘᴘᴏʀᴛ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ʏᴏᴜ ᴄᴀɴ ᴅᴏ sᴏ ʙʏ sᴜʙsᴄʀɪʙɪɴɢ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ\nᴛʜᴀɴᴋs ғᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ</b>",
"FSUB": "<b><blockquote>ʜᴇʟʟᴏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ <a href='https://t.me/Ecchi_Dex'>ᴇᴄᴄʜɪ ᴅᴇx</a></blockquote>ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ/ɢʀᴏᴜᴘ ғɪʀsᴛ, ᴘʟᴇᴀsᴇ sᴜʙsᴄʀɪʙᴇ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ᴛʜʀᴏᴜɢʜ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴀɴᴅ sᴛᴀʀᴛ ʙᴏᴛ ᴀɢᴀɪɴ<blockquote>ʜᴏᴡ ᴛᴏ ᴜsᴇ ʙᴏᴛ <a href=https://t.me/NexusTutorial/6>ᴛᴜᴛᴏʀɪᴀʟ ᴄʟɪᴄᴋ ʜᴇʀᴇ</a></blockquote></b>",
"ABOUT": "<b>ʜᴇʏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴜᴘᴘᴏʀᴛ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ʏᴏᴜ ᴄᴀɴ ᴅᴏ sᴏ ʙʏ sᴜʙsᴄʀɪʙɪɴɢ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴛʜᴀɴᴋs Fᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ\n❏ ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅs\n├/start : sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ\nsɪᴍᴘʟʏ ᴄʟɪᴄᴋ ᴏɴ ʟɪɴᴋ ᴀɴᴅ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ᴊᴏɪɴ ʙᴏᴛʜ ᴄʜᴀɴɴᴇʟs ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ ᴛʜᴀᴛs ɪᴛ.</b>",
"REPLY": "<b>ᴡʀᴏɴɢ ᴄᴏᴍᴍᴀɴᴅ</b>",
"SHORT_MSG": "<b><blockquote>ʏᴏᴜʀ ᴀᴅs ᴛᴏᴋᴇɴ ɪs ᴇxᴘɪʀᴇᴅ ᴘʟᴇᴀsᴇ ᴠᴇʀɪғʏ ᴛᴏ ʀᴇɢᴀɪɴ ᴀᴄᴄᴇss ᴛᴏ ᴛʜᴇ ʙᴏᴛs</blockquote>ᴡʜᴀᴛ ɪs ᴛʜᴇ ᴛᴏᴋᴇɴ?ᴛʜɪs ɪs ᴀɴ ᴀᴅs ᴛᴏᴋᴇɴ. ᴘᴀssɪɴɢ ᴏɴᴇ ᴀᴅ ᴀʟʟᴏᴡs ʏᴏᴜ ᴛᴏ ᴜsᴇ ᴛʜᴇ ᴏᴜʀ ʙᴏᴛs</b>",
"START_PHOTO": "https://i.ibb.co/0R9k9x4M/tmpbtpr7q0.jpg",
"FSUB_PHOTO": "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg",
"SHORT_PIC": "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg",
"SHORT": "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg",}


def LOGGER(name: str, client_name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    formatter = logging.Formatter(
        f"[%(asctime)s - %(levelname)s] - {client_name} - %(name)s - %(message)s",
        datefmt="%d-%b-%y %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE_NAME,
        maxBytes=50_000_000,
        backupCount=10,
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.setLevel(logging.INFO)

    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger
