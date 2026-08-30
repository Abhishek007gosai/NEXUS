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
SESSION = os.getenv("SESSION", "Kaya")
TOKEN = os.getenv("TOKEN", "")
API_ID = int(os.getenv("API_ID", ""))
API_HASH = os.getenv("API_HASH", "")
WORKERS = int(os.getenv("WORKERS", "5"))
OWNER_ID = int(os.getenv("OWNER_ID", ""))
MSG_EFFECT = 5046509860389126442

# Extra admin user IDs (space or comma separated). Owner is always treated as admin.
ADMINS = [
    int(x) for x in os.getenv("ADMINS", "").replace(",", " ").split() if x.strip().isdigit()
]

# ──────────────────────────────────────────────
# MongoDB
# ──────────────────────────────────────────────
# Multi: space or comma separated, paired by index (failover order).
#   DB_URI="mongodb://uri1 mongodb://uri2"
#   DB_NAME="cluster0 cluster1"
DB_URI = [u for u in os.getenv("DB_URI", "").replace(",", " ").split() if u.strip()]
DB_NAME = [n for n in os.getenv("DB_NAME", "cluster0").replace(",", " ").split() if n.strip()] or ["cluster0"]

# ──────────────────────────────────────────────
# Anime Index branding
# ──────────────────────────────────────────────
BRAND_NAME = os.getenv("BRAND_NAME", "kaya")
BRAND_HANDLE = os.getenv("BRAND_HANDLE", "kaya")
# Bot display name used in log-channel messages (Request / Report posts)
# Prefer BOTNAME env, else BRAND_NAME, else "kaya" (never the Telegram @username)
BOTNAME = os.getenv("BOTNAME", "").strip() or BRAND_NAME or "kaya"
WEBAPP_URL = os.getenv("WEBAPP_URL", "").rstrip("/")
# Custom URL for the "Open Index" button (falls back to WEBAPP_URL if empty)
INDEX_URL = os.getenv("INDEX_URL", "").rstrip("/")
# Channel / group where new requests & reports are posted (use -100... form)
LOG_CHANNEL_ID = (os.getenv("LOG_CHANNEL_ID", "") or "").strip()
SUPPORT_CHAT_URL = os.getenv("SUPPORT_CHAT_URL", "").strip()
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
CATALOG_CACHE_TTL = int(os.getenv("CATALOG_CACHE_TTL", "600"))
# AniList GraphQL (set ANILIST_ENDPOINT to your own proxy URL if needed)
ANILIST_ENDPOINT = os.getenv("ANILIST_ENDPOINT", "https://graphql.anilist.co").rstrip("/")
# If server catalog is empty, WebApp fetches AniList from the user's device
ANILIST_CLIENT_FALLBACK = os.getenv("ANILIST_CLIENT_FALLBACK", "true").lower() in ("1", "true", "yes")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ──────────────────────────────────────────────
# Shortener
# ──────────────────────────────────────────────
SHORT_URL = os.getenv("SHORT_URL", "")
SHORT_API = os.getenv("SHORT_API", "")
SHORT_TUT = os.getenv("SHORT_TUT", "")

# ──────────────────────────────────────────────
# Channels / Force Sub / Bot settings
# ──────────────────────────────────────────────
DB_CHANNEL = int(os.getenv("DB_CHANNEL", "-1003928914916"))
FSUBS = [[-1002369123167, True, 5]]
AUTO_DEL = os.getenv("AUTO_DEL", "300")
DISABLE_BTN = os.getenv("DISABLE_BTN", "False").lower() == "true"
PROTECT = os.getenv("PROTECT", "False").lower() == "true"

# ──────────────────────────────────────────────
# Messages
# ──────────────────────────────────────────────
MESSAGES = {
    "INDEX": "<b>ᴛʜɪs ɪs ᴀɴɪᴍᴇ ɪɴᴅᴇx ʜᴇʀᴇ ʏᴏᴜ ᴄᴀɴ ʙʀᴏᴡsᴇ, sᴇᴀʀᴄʜ ʏᴏᴜ ғᴀᴠᴏᴜʀɪᴛᴇ ᴀɴɪᴍᴇ</b>",
    "START": "<b>ʜᴇʏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴄᴏᴍᴍᴜɴɪᴛʏ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴜᴘᴘᴏʀᴛ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ʏᴏᴜ ᴄᴀɴ ᴅᴏ sᴏ ʙʏ sᴜʙsᴄʀɪʙɪɴɢ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ\nᴛʜᴀɴᴋs ғᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ</b>",
    "FSUB": "<b><blockquote>ʜᴇʟʟᴏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴇᴛᴇʀɴᴀʟs</blockquote>ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ/ɢʀᴏᴜᴘ ғɪʀsᴛ, ᴘʟᴇᴀsᴇ sᴜʙsᴄʀɪʙᴇ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ᴛʜʀᴏᴜɢʜ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴀɴᴅ sᴛᴀʀᴛ ʙᴏᴛ ᴀɢᴀɪɴ<blockquote>ʜᴏᴡ ᴛᴏ ᴜsᴇ ʙᴏᴛ <a href=https://t.me/NexusTutorial/6>ᴛᴜᴛᴏʀɪᴀʟ ᴄʟɪᴄᴋ ʜᴇʀᴇ</a></blockquote></b>",
    "ABOUT": "<b>ʜᴇʏ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴜᴘᴘᴏʀᴛ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ ʏᴏᴜ ᴄᴀɴ ᴅᴏ sᴏ ʙʏ sᴜʙsᴄʀɪʙɪɴɢ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴛʜᴀɴᴋs Fᴏʀ ʏᴏᴜʀ sᴜᴘᴘᴏʀᴛ\n❏ ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅs\n├/start : sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ\nsɪᴍᴘʟʏ ᴄʟɪᴄᴋ ᴏɴ ʟɪɴᴋ ᴀɴᴅ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ᴊᴏɪɴ ʙᴏᴛʜ ᴄʜᴀɴɴᴇʟs ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ ᴛʜᴀᴛs ɪᴛ.</b>",
    "REPLY": "<b>ᴡʀᴏɴɢ ᴄᴏᴍᴍᴀɴᴅ</b>",
    "SHORT_MSG": "<b><blockquote>ʏᴏᴜʀ ᴀᴅs ᴛᴏᴋᴇɴ ɪs ᴇxᴘɪʀᴇᴅ ᴘʟᴇᴀsᴇ ᴠᴇʀɪғʏ ᴛᴏ ʀᴇɢᴀɪɴ ᴀᴄᴄᴇss ᴛᴏ ᴛʜᴇ ʙᴏᴛs</blockquote>ᴡʜᴀᴛ ɪs ᴛʜᴇ ᴛᴏᴋᴇɴ?ᴛʜɪs ɪs ᴀɴ ᴀᴅs ᴛᴏᴋᴇɴ. ᴘᴀssɪɴɢ ᴏɴᴇ ᴀᴅ ᴀʟʟᴏᴡs ʏᴏᴜ ᴛᴏ ᴜsᴇ ᴛʜᴇ ᴏᴜʀ ʙᴏᴛs</b>",
    "START_PHOTO": "https://i.ibb.co/0R9k9x4M/tmpbtpr7q0.jpg",
    "FSUB_PHOTO": "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg",
    "SHORT_PIC": "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg",
    "SHORT": "https://i.ibb.co/sdYHCnBC/tmp9peum4mg.jpg",
    "SEARCH_PHOTO": os.getenv("SEARCH_PHOTO", "").strip(),
    "BANNER_IMAGE_URL": os.getenv("BANNER_IMAGE_URL", "").strip(),
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
