import asyncio
from threading import Thread

asyncio.set_event_loop(asyncio.new_event_loop())


from bot import Bot, run_flask
from pyrogram import compose
from config import (
    SESSION, WORKERS, DB_CHANNEL, FSUBS, TOKEN, ADMINS, MESSAGES,
    AUTO_DEL, DB_URI, DB_NAME, API_ID, API_HASH, PROTECT, DISABLE_BTN,
    LINKSHARE_DB_URI, LINKSHARE_DB_NAME,
)


# Clear any leftover Telegram webhook ASAP (polling mode).
def _clear_webhook_early():
    try:
        import requests
        from config import TOKEN as tok
        if not tok:
            return
        requests.get(
            f"https://api.telegram.org/bot{tok}/deleteWebhook",
            params={"drop_pending_updates": "true"},
            timeout=15,
        )
    except Exception:
        pass


_clear_webhook_early()

# Flask (Anime Index mini app + health) — required for Render/Koyeb health checks
Thread(target=run_flask, daemon=True).start()


async def main():
    apps = [
        Bot(
            SESSION,
            WORKERS,
            DB_CHANNEL,
            FSUBS,
            TOKEN,
            ADMINS,
            MESSAGES,
            AUTO_DEL,
            DB_URI,
            DB_NAME,
            API_ID,
            API_HASH,
            PROTECT,
            DISABLE_BTN,
            LINKSHARE_DB_URI,
            LINKSHARE_DB_NAME,
        )
    ]
    await compose(apps)


asyncio.run(main())
