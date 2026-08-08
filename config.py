import os
import logging
from logging.handlers import RotatingFileHandler

# ──────────────────────────────────────────────
# Logging / Server
# ──────────────────────────────────────────────
LOG_FILE_NAME = "bot.log"
PORT = int(os.getenv("PORT", "5010"))

# ──────────────────────────────────────────────
# Telegram
# ──────────────────────────────────────────────
SESSION = os.getenv("SESSION", "ECCHI")
TOKEN = os.getenv("TOKEN", "")
API_ID = int(os.getenv("API_ID", "0") or "0")
API_HASH = os.getenv("API_HASH", "")
WORKERS = int(os.getenv("WORKERS", "5"))
OWNER_ID = int(os.getenv("OWNER_ID", "0") or "0")
MSG_EFFECT = 5046509860389126442

ADMINS = [8771195193]

# ──────────────────────────────────────────────
# MongoDB — single DB for everything (bot + web)
# ──────────────────────────────────────────────
# For Multiple Database URL Use One Space Between Each
DB_URI = [u for u in os.getenv("DB_URI", "").split() if u.strip()]
DB_NAME = os.getenv("DB_NAME", "cluster0")

# ──────────────────────────────────────────────
# Anime Index branding
# ──────────────────────────────────────────────
BRAND_NAME = os.getenv("BRAND_NAME", "Anime Index")
BRAND_HANDLE = os.getenv("BRAND_HANDLE", "ANIME_INDEX")
SUPPORT_CHAT_URL = os.getenv("SUPPORT_CHAT_URL", "").strip()
WEBAPP_URL = os.getenv("WEBAPP_URL", "").rstrip("/")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID", "")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
CATALOG_CACHE_TTL = int(os.getenv("CATALOG_CACHE_TTL", "600"))
ANILIST_ENDPOINT = "https://graphql.anilist.co"

# ──────────────────────────────────────────────
# Shortener
# ──────────────────────────────────────────────
SHORT_URL = os.getenv("SHORT_URL", "")
SHORT_API = os.getenv("SHORT_API", "")
SHORT_TUT = os.getenv("SHORT_TUT", "")

# ──────────────────────────────────────────────
# Channels / Force Sub / Bot settings
# ──────────────────────────────────────────────
DB_CHANNEL = int(os.getenv("DB_CHANNEL", "-1002497924209"))
FSUBS = [[-1001457313028, True, 5]]
AUTO_DEL = os.getenv("AUTO_DEL", "300")
DISABLE_BTN = os.getenv("DISABLE_BTN", "False").lower() == "true"
PROTECT = os.getenv("PROTECT", "False").lower() == "true"

# ──────────────────────────────────────────────
# Messages
# ──────────────────────────────────────────────
MESSAGES = {
    "INDEX": "<b>ᴛʜɪs ɪs ᴀɴɪᴍᴇ ɪɴᴅᴇx ʜᴇʀᴇ ʏᴏᴜ ᴄᴀɴ ʙʀᴏᴡsᴇ, sᴇᴀʀᴄʜ ʏᴏᴜ ғᴀᴠᴏᴜʀɪᴛᴇ ᴀɴɪᴍᴇ</b>",
    "START": "<b>ʜᴇʏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴄᴏᴍᴍᴜɴɪᴛʏ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴜᴘᴘᴏʀᴛ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ʏᴏᴜ ᴄᴀɴ ᴅᴏ sᴏ ʙʏ sᴜʙsᴄʀɪʙɪɴɢ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ\nᴛʜᴀɴᴋs ғᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ</b>",
    "FSUB": "<b><blockquote>ʜᴇʟʟᴏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ <a href='https://t.me/Ecchi_Dex'>ᴇᴄᴄʜɪ ᴅᴇx</a></blockquote>ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ/ɢʀᴏᴜᴘ ғɪʀsᴛ, ᴘʟᴇᴀsᴇ sᴜʙsᴄʀɪʙᴇ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ᴛʜʀᴏᴜɢʜ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴀɴᴅ sᴛᴀʀᴛ ʙᴏᴛ ᴀɢᴀɪɴ<blockquote>ʜᴏᴡ ᴛᴏ ᴜsᴇ ʙᴏᴛ <a href=https://t.me/NexusTutorial/6>ᴛᴜᴛᴏʀɪᴀʟ ᴄʟɪᴄᴋ ʜᴇʀᴇ</a></blockquote></b>",
    "ABOUT": "<b>ʜᴇʏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴜᴘᴘᴏʀᴛ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ʏᴏᴜ ᴄᴀɴ ᴅᴏ sᴏ ʙʏ sᴜʙsᴄʀɪʙɪɴɢ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴛʜᴀɴᴋs Fᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ\n❏ ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅs\n├/start : sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ\nsɪᴍᴘʟʏ ᴄʟɪᴄᴋ ᴏɴ ʟɪɴᴋ ᴀɴᴅ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ᴊᴏɪɴ ʙᴏᴛʜ ᴄʜᴀɴɴᴇʟs ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ ᴛʜᴀᴛs ɪᴛ.</b>",
    "REPLY": "<b>ᴡʀᴏɴɢ ᴄᴏᴍᴍᴀɴᴅ</b>",
    "SHORT_MSG": "<b><blockquote>ʏᴏᴜʀ ᴀᴅs ᴛᴏᴋᴇɴ ɪs ᴇxᴘɪʀᴇᴅ ᴘʟᴇᴀsᴇ ᴠᴇʀɪғʏ ᴛᴏ ʀᴇɢᴀɪɴ ᴀᴄᴄᴇss ᴛᴏ ᴛʜᴇ ʙᴏᴛs</blockquote>ᴡʜᴀᴛ ɪs ᴛʜᴇ ᴛᴏᴋᴇɴ?ᴛʜɪs ɪs ᴀɴ ᴀᴅs ᴛᴏᴋᴇɴ. ᴘᴀssɪɴɢ ᴏɴᴇ ᴀᴅ ᴀʟʟᴏᴡs ʏᴏᴜ ᴛᴏ ᴜsᴇ ᴛʜᴇ ᴏᴜʀ ʙᴏᴛs</b>",
    "START_PHOTO": "https://i.ibb.co/0R9k9x4M/tmpbtpr7q0.jpg",
    "FSUB_PHOTO": "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg",
    "SHORT_PIC": "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg",
    "SHORT": "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg",
    "SEARCH_PHOTO": "",
    "BANNER_IMAGE_URL": os.getenv("BANNER_IMAGE_URL", "https://i.ibb.co/0R9k9x4M/tmpbtpr7q0.jpg"),
}



def LOGGER(name: str, client_name: str = ""):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            f"%(asctime)s - %(name)s - [{client_name}] - %(levelname)s - %(message)s"
        )
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        logger.addHandler(stream)
        try:
            fh = RotatingFileHandler(LOG_FILE_NAME, maxBytes=10 * 1024 * 1024, backupCount=3)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception:
            pass
    return logger
