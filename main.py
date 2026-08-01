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
from plugins import web_server


# Start Flask (Anime Index mini app + health) first for Render/Koyeb
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


async def runner():
    await asyncio.gather(
        main(),
        _run_aiohttp(),
    )


async def _run_aiohttp():
    """Optional legacy aiohttp routes (plugins/route.py)."""
    try:
        from aiohttp import web
        app = await web_server()
        runner = web.AppRunner(app)
        await runner.setup()
        # Bind a different internal port so it does not clash with Flask
        site = web.TCPSite(runner, "0.0.0.0", 8081)
        await site.start()
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        print(f"[aiohttp] skipped: {e}")
        while True:
            await asyncio.sleep(3600)


asyncio.run(runner())
