import os
import logging
from logging.handlers import RotatingFileHandler

# Logging
LOG_FILE_NAME = "bot.log"
PORT = int(os.getenv("PORT", "5010"))

OWNER_ID = int(os.getenv("OWNER_ID", "8771195193"))
MSG_EFFECT = 5046509860389126442

# Shortener
SHORT_URL = os.getenv("SHORT_URL", "")
SHORT_API = os.getenv("SHORT_API", "")
SHORT_TUT = os.getenv("SHORT_TUT", "")

# Telegram
SESSION = os.getenv("SESSION", "Kaya")
TOKEN = os.getenv("TOKEN", "") or os.getenv("BOT_TOKEN", "")
API_ID = int(os.getenv("API_ID", "29245477"))
API_HASH = os.getenv("API_HASH", "0abc83883262245c90ca337b7a0375c4")
WORKERS = int(os.getenv("WORKERS", "5"))

# MongoDB (file store / core bot data: users, pros, fsub, settings, etc.)
DB_URI = os.getenv("DB_URI", "")
DB_NAME = os.getenv("DB_NAME", "cluster0")

# MongoDB (Link Share store) - separate database/cluster from the file store.
LINKSHARE_DB_URI = os.getenv("LINKSHARE_DB_URI", DB_URI)
LINKSHARE_DB_NAME = os.getenv("LINKSHARE_DB_NAME", "linkshare")

# ---------------------------------------------------------------------------
# Anime Index / Mini App (Touka) — separate MongoDB so catalog data never
# collides with file-store collections.
# Falls back to DB_URI if WEB_DB_URI is not set.
# ---------------------------------------------------------------------------
WEB_DB_URI = os.getenv("WEB_DB_URI", "") or DB_URI
WEB_DB_NAME = os.getenv("WEB_DB_NAME", "anime_index")

# Public HTTPS URL of this deployment (required for Telegram Mini App + deep links)
WEBAPP_URL = os.getenv("WEBAPP_URL", "").rstrip("/")
# Channel/group the bot posts anime request + report notifications to
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID", "")
# Flask secret for session cookies
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
# Branding for the mini app + /anidex
BRAND_NAME = os.getenv("BRAND_NAME", "Anime Index")
BRAND_HANDLE = os.getenv("BRAND_HANDLE", "ANIME_INDEX")
BANNER_IMAGE_URL = os.getenv("BANNER_IMAGE_URL", "")
START_MSG = os.getenv(
    "START_MSG",
    "HELLO {first_name}\\n\\n"
    "I am {brand_name} bot. Use /anidex to browse, search and request anime.\\n\\n"
    "\U0001f4fa Browse trending anime, search for your favorites, and "
    "request anime that isn't available yet.\\n\\n"
    "_Your all-in-one anime station._",
).replace("\\n", "\n")
CATALOG_CACHE_TTL = int(os.getenv("CATALOG_CACHE_TTL", "600"))
ANILIST_ENDPOINT = "https://graphql.anilist.co"

# Force Subscribe
# Format: [[channel_id, request_enabled, timer_minutes], ...]
_fsubs_raw = os.getenv("FSUBS", "")
if _fsubs_raw:
    import ast
    try:
        FSUBS = ast.literal_eval(_fsubs_raw)
    except Exception:
        FSUBS = [[-1002369123167, True, 5]]
else:
    FSUBS = [[-1002369123167, True, 5]]

# Channels
DB_CHANNEL = int(os.getenv("DB_CHANNEL", "-1002497924209"))

# Auto Delete
AUTO_DEL = os.getenv("AUTO_DEL", "300")

# Admins (used by both file-store and anime mini-app)
def _split_ids(raw: str):
    ids = []
    for chunk in str(raw).split(","):
        chunk = chunk.strip()
        if chunk.lstrip("-").isdigit():
            ids.append(int(chunk))
    return ids

ADMINS = _split_ids(os.getenv("ADMINS", "8771195193"))
if OWNER_ID not in ADMINS:
    ADMINS.append(OWNER_ID)

# Bot Settings
DISABLE_BTN = os.getenv("DISABLE_BTN", "False").lower() == "true"
PROTECT = os.getenv("PROTECT", "False").lower() == "true"

# Messages
MESSAGES = {
    "START": os.getenv(
        "MSG_START",
        "<b>ʜᴇʏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴄᴏᴍᴍᴜɴɪᴛʏ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴜᴘᴘᴏʀᴛ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ʏᴏᴜ ᴄᴀɴ ᴅᴏ sᴏ ʙʏ sᴜʙsᴄʀɪʙɪɴɢ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ\nᴛʜᴀɴᴋs ғᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ</b>",
    ),
    "FSUB": os.getenv(
        "MSG_FSUB",
        "<b><blockquote>ʜᴇʟʟᴏ ᴡᴇʟᴄᴏᴍᴇ</blockquote>ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ/ɢʀᴏᴜᴘ ғɪʀsᴛ</b>",
    ),
    "ABOUT": os.getenv(
        "MSG_ABOUT",
        "<b>ʜᴇʏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ</b>",
    ),
    "REPLY": os.getenv("MSG_REPLY", "<b>ᴡʀᴏɴɢ ᴄᴏᴍᴍᴀɴᴅ</b>"),
    "SHORT_MSG": os.getenv(
        "MSG_SHORT",
        "<b><blockquote>ʏᴏᴜʀ ᴀᴅs ᴛᴏᴋᴇɴ ɪs ᴇxᴘɪʀᴇᴅ ᴘʟᴇᴀsᴇ ᴠᴇʀɪғʏ ᴛᴏ ʀᴇɢᴀɪɴ ᴀᴄᴄᴇss</blockquote></b>",
    ),
    "START_PHOTO": os.getenv("START_PHOTO", ""),
    "FSUB_PHOTO": os.getenv("FSUB_PHOTO", ""),
    "SHORT_PIC": os.getenv("SHORT_PIC", ""),
}

# Compat alias used by Touka-style code
class Config:
    """Namespace matching ToukaV5 Config for the mini-app / anime_database."""
    BRAND_NAME = BRAND_NAME
    BRAND_HANDLE = BRAND_HANDLE
    BANNER_IMAGE_URL = BANNER_IMAGE_URL
    START_MSG = START_MSG
    BOT_TOKEN = TOKEN
    WEBAPP_URL = WEBAPP_URL
    LOG_CHANNEL_ID = LOG_CHANNEL_ID
    ADMIN_IDS = ADMINS
    API_ID = API_ID
    API_HASH = API_HASH
    SECRET_KEY = SECRET_KEY
    PORT = PORT
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    MONGODB_URL = WEB_DB_URI
    MONGODB_NAME = WEB_DB_NAME
    ANILIST_ENDPOINT = ANILIST_ENDPOINT
    CATALOG_CACHE_TTL = CATALOG_CACHE_TTL


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
