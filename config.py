import os
import logging
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FILE_NAME = "bot.log"
PORT = int(os.getenv("PORT", "5010"))

# ---------------------------------------------------------------------------
# Ownership / admins
# ---------------------------------------------------------------------------
OWNER_ID = int(os.getenv("OWNER_ID", "8771195193"))
MSG_EFFECT = 5046509860389126442

def _split_ids(raw: str) -> list:
    ids = []
    for chunk in (raw or "").split(","):
        chunk = chunk.strip()
        if chunk.lstrip("-").isdigit():
            ids.append(int(chunk))
    return ids

ADMINS = _split_ids(os.getenv("ADMINS", os.getenv("ADMIN_IDS", "8771195193")))
if OWNER_ID not in ADMINS:
    ADMINS.append(OWNER_ID)

# ---------------------------------------------------------------------------
# Shortener
# ---------------------------------------------------------------------------
SHORT_URL = os.getenv("SHORT_URL", "")
SHORT_API = os.getenv("SHORT_API", "")
SHORT_TUT = os.getenv("SHORT_TUT", "")

# ---------------------------------------------------------------------------
# Telegram (Pyrogram / MTProto)
# ---------------------------------------------------------------------------
SESSION = os.getenv("SESSION", "Kaya")
TOKEN = os.getenv("TOKEN", os.getenv("BOT_TOKEN", ""))
BOT_TOKEN = TOKEN  # alias used by mini-app / initData verification
API_ID = int(os.getenv("API_ID", "29245477") or 0)
API_HASH = os.getenv("API_HASH", "0abc83883262245c90ca337b7a0375c4")
WORKERS = int(os.getenv("WORKERS", "5"))

# ---------------------------------------------------------------------------
# MongoDB (shared by file-store + anime index)
# ---------------------------------------------------------------------------
DB_URI = os.getenv("DB_URI", os.getenv("MONGODB_URL", "mongodb://localhost:27017"))
DB_NAME = os.getenv("DB_NAME", os.getenv("MONGODB_NAME", "cluster0"))
MONGODB_URL = DB_URI
MONGODB_NAME = DB_NAME

# ---------------------------------------------------------------------------
# Force Subscribe / DB channel (file-store)
# ---------------------------------------------------------------------------
_FSUB_RAW = os.getenv("FSUBS", "")
if _FSUB_RAW:
    import json
    try:
        FSUBS = json.loads(_FSUB_RAW)
    except Exception:
        FSUBS = [[-1002369123167, True, 5]]
else:
    FSUBS = [[-1002369123167, True, 5]]

DB_CHANNEL = int(os.getenv("DB_CHANNEL", "-1002497924209"))
AUTO_DEL = int(os.getenv("AUTO_DEL", "300") or 0)
DISABLE_BTN = os.getenv("DISABLE_BTN", "False").lower() == "true"
PROTECT = os.getenv("PROTECT", "False").lower() == "true"

# ---------------------------------------------------------------------------
# Anime Index / Mini App
# ---------------------------------------------------------------------------
BRAND_NAME = os.getenv("BRAND_NAME", "Ecchi Dex")
BRAND_HANDLE = os.getenv("BRAND_HANDLE", "ECCHI_DEX")
BANNER_IMAGE_URL = os.getenv("BANNER_IMAGE_URL", "")
SUPPORT_CHAT_URL = os.getenv("SUPPORT_CHAT_URL", "https://t.me/EternalsHelplineBot").strip()
START_MSG = os.getenv(
    "START_MSG",
    "ᴛʜɪs ɪs ᴇᴄᴄʜɪ ᴅᴇx — ʙʀᴏᴡsᴇ, sᴇᴀʀᴄʜ & ʀᴇǫᴜᴇsᴛ ʏᴏᴜʀ ғᴀᴠᴏᴜʀɪᴛᴇ ᴛɪᴛʟᴇs",
).replace("\\n", "\n")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me")
WEBAPP_URL = os.getenv("WEBAPP_URL", "").rstrip("/")
_log_ch = os.getenv("LOG_CHANNEL_ID", "")
try:
    LOG_CHANNEL_ID = int(_log_ch) if _log_ch else None
except ValueError:
    LOG_CHANNEL_ID = None

ADMIN_IDS = ADMINS  # mini-app admin checks use ADMIN_IDS
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-nexus-ecchi")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
CATALOG_CACHE_TTL = int(os.getenv("CATALOG_CACHE_TTL", "600"))
NEWS_CACHE_TTL = int(os.getenv("NEWS_CACHE_TTL", "900"))

# ---------------------------------------------------------------------------
# File-store start / fsub messages
# ---------------------------------------------------------------------------
MESSAGES = {
    "START": os.getenv(
        "MSG_START",
        "<b>ʜᴇʏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴇᴄᴄʜɪ ᴅᴇx\nɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴜᴘᴘᴏʀᴛ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ sᴜʙsᴄʀɪʙᴇ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ\nᴛʜᴀɴᴋs ғᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ</b>",
    ),
    "FSUB": os.getenv(
        "MSG_FSUB",
        "<b><blockquote>ʜᴇʟʟᴏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ <a href='https://t.me/Ecchi_Dex'>ᴇᴄᴄʜɪ ᴅᴇx</a></blockquote>"
        "ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ/ɢʀᴏᴜᴘ ғɪʀsᴛ, ᴘʟᴇᴀsᴇ sᴜʙsᴄʀɪʙᴇ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs "
        "ᴛʜʀᴏᴜɢʜ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴀɴᴅ sᴛᴀʀᴛ ʙᴏᴛ ᴀɢᴀɪɴ"
        "<blockquote>ʜᴏᴡ ᴛᴏ ᴜsᴇ ʙᴏᴛ <a href=https://t.me/NexusTutorial/6>ᴛᴜᴛᴏʀɪᴀʟ ᴄʟɪᴄᴋ ʜᴇʀᴇ</a></blockquote></b>",
    ),
    "ABOUT": os.getenv(
        "MSG_ABOUT",
        "<b>ᴇᴄᴄʜɪ ᴅᴇx — ғɪʟᴇ sᴛᴏʀᴇ + ᴀɴɪᴍᴇ ɪɴᴅᴇx\n"
        "├ /start — sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ\n"
        "├ /anidex — ᴏᴘᴇɴ ᴍɪɴɪ ᴀᴘᴘ\n"
        "└ sᴇɴᴅ ᴀɴʏ ᴛɪᴛʟᴇ ɴᴀᴍᴇ ᴛᴏ sᴇᴀʀᴄʜ ᴛʜᴇ ʟɪʙʀᴀʀʏ</b>",
    ),
    "REPLY": "<b>ᴡʀᴏɴɢ ᴄᴏᴍᴍᴀɴᴅ</b>",
    "SHORT_MSG": "<b><blockquote>ʏᴏᴜʀ ᴀᴅs ᴛᴏᴋᴇɴ ɪs ᴇxᴘɪʀᴇᴅ ᴘʟᴇᴀsᴇ ᴠᴇʀɪғʏ ᴛᴏ ʀᴇɢᴀɪɴ ᴀᴄᴄᴇss</blockquote>"
                 "ᴡʜᴀᴛ ɪs ᴛʜᴇ ᴛᴏᴋᴇɴ? ᴛʜɪs ɪs ᴀɴ ᴀᴅs ᴛᴏᴋᴇɴ. ᴘᴀssɪɴɢ ᴏɴᴇ ᴀᴅ ᴀʟʟᴏᴡs ʏᴏᴜ ᴛᴏ ᴜsᴇ ᴛʜᴇ ʙᴏᴛ</b>",
    "START_PHOTO": os.getenv("START_PHOTO", "https://i.ibb.co/0R9k9x4M/tmpbtpr7q0.jpg"),
    "FSUB_PHOTO": os.getenv("FSUB_PHOTO", "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg"),
    "SHORT_PIC": os.getenv("SHORT_PIC", "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg"),
    "SHORT": os.getenv("SHORT_PIC", "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg"),
}


# Compatibility shim: EcchiDex code expects Config.X
class Config:
    BRAND_NAME = BRAND_NAME
    BRAND_HANDLE = BRAND_HANDLE
    BANNER_IMAGE_URL = BANNER_IMAGE_URL
    SUPPORT_CHAT_URL = SUPPORT_CHAT_URL
    START_MSG = START_MSG
    BOT_TOKEN = BOT_TOKEN
    WEBHOOK_SECRET = WEBHOOK_SECRET
    WEBAPP_URL = WEBAPP_URL
    LOG_CHANNEL_ID = LOG_CHANNEL_ID
    ADMIN_IDS = ADMIN_IDS
    API_ID = str(API_ID)
    API_HASH = API_HASH
    SECRET_KEY = SECRET_KEY
    PORT = PORT
    DEBUG = DEBUG
    CATALOG_CACHE_TTL = CATALOG_CACHE_TTL
    NEWS_CACHE_TTL = NEWS_CACHE_TTL
    MONGODB_URL = MONGODB_URL
    MONGODB_NAME = MONGODB_NAME


def LOGGER(name: str, client_name: str) -> logging.Logger:
    logger = logging.getLogger(f"{name}:{client_name}")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "[%(asctime)s - %(name)s] - %(levelname)s - %(message)s"
        )
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        logger.addHandler(stream)
        try:
            file_handler = RotatingFileHandler(
                LOG_FILE_NAME, maxBytes=10 * 1024 * 1024, backupCount=3
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception:
            pass
    return logger
