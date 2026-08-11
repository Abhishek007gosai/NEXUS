import asyncio
from threading import Thread

asyncio.set_event_loop(asyncio.new_event_loop())


from bot import Bot, run_flask
from pyrogram import compose
from config import (
    SESSION, WORKERS, DB_CHANNEL, FSUBS, TOKEN, ADMINS, MESSAGES,
    AUTO_DEL, DB_URI, DB_NAME, API_ID, API_HASH, PROTECT, DISABLE_BTN,
)


# Clear any leftover Telegram webhook ASAP (polling mode).
def _clear_webhook_early():
    try:
        import requests
        from config import TOKEN as tok
        if not tok:
            return
        r = requests.get(
            f"https://api.telegram.org/bot{tok}/deleteWebhook",
            params={"drop_pending_updates": "true"},
            timeout=15,
        )
        print("deleteWebhook:", r.json() if r.ok else r.status_code)
    except Exception as e:
        print("deleteWebhook error:", e)


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
        )
    ]
    await compose(apps)


asyncio.run(main())
