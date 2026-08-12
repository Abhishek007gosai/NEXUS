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

import asyncio
import os
import shutil
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup

from bot import Bot
from config import *
from helper_func import *
from database.database import *

try:
    import psutil
except ImportError:
    psutil = None

#=====================================================================================##

def _bar(percent: float, width: int = 10) -> str:
    try:
        p = max(0.0, min(100.0, float(percent)))
    except (TypeError, ValueError):
        p = 0.0
    filled = int(round(p / 100.0 * width))
    return "█" * filled + "░" * (width - filled)


def _status_dot(percent: float) -> str:
    if percent < 70:
        return "🟢 OK"
    if percent < 90:
        return "🟡 HIGH"
    return "🔴 CRITICAL"


def _fmt_bytes(n: float) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    if i == 0:
        return f"{int(n)} {units[i]}"
    return f"{n:.2f} {units[i]}"


def _fmt_uptime(seconds: float) -> str:
    days, rem = divmod(max(0, int(seconds)), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


@Bot.on_message(filters.command("stats") & filters.private & filters.user(OWNER_ID))
async def stats(bot: Bot, message: Message):
    """Detailed bot / DB / server stats — owner only."""
    reply = await message.reply("📊 Collecting stats...")

    # ── Bot ──
    try:
        total_users = len(await db.full_userbase())
    except Exception:
        total_users = 0

    uptime_ref = getattr(bot, "uptime", datetime.now())
    # uptime may be timezone-aware (IST); normalize
    try:
        now = datetime.now(tz=uptime_ref.tzinfo) if getattr(uptime_ref, "tzinfo", None) else datetime.now()
        uptime_seconds = (now - uptime_ref).total_seconds()
    except Exception:
        uptime_seconds = 0
    uptime_str = _fmt_uptime(uptime_seconds)

    try:
        admins_count = len(await db.get_all_admins()) + 1  # + owner
    except Exception:
        admins_count = 1

    bot_cpu, bot_ram_mb, bot_status = 0.0, 0.0, "🟢 Running"
    if psutil:
        try:
            process = psutil.Process()
            bot_cpu = process.cpu_percent(interval=0.3)
            bot_ram_mb = process.memory_info().rss / (1024 ** 2)
        except Exception:
            bot_status = "🔴 Error"
    else:
        bot_status = "🟢 Running"

    # ── Server ──
    try:
        total_disk, used_disk, free_disk = shutil.disk_usage("/")
        disk_pct = (used_disk / total_disk) * 100 if total_disk else 0
    except Exception:
        total_disk = used_disk = free_disk = disk_pct = 0

    ram_used = ram_total = ram_pct = cpu_usage = 0
    sent = recv = 0
    if psutil:
        try:
            ram = psutil.virtual_memory()
            ram_used, ram_total, ram_pct = ram.used, ram.total, ram.percent
            cpu_usage = psutil.cpu_percent(interval=0.5)
        except Exception:
            pass
        try:
            net_io = psutil.net_io_counters()
            sent, recv = net_io.bytes_sent, net_io.bytes_recv
        except Exception:
            pass

    # ── MongoDB ──
    db_host = "unknown"
    db_used = 0.0
    db_limit = 512 * 1024 * 1024  # Atlas free-tier style display limit
    db_docs = 0
    db_name = DB_NAME or "cluster0"
    try:
        uris = DB_URI if isinstance(DB_URI, (list, tuple)) else [DB_URI]
        raw_uri = (uris[0] if uris else "") or getattr(db, "uri", "") or ""
        if raw_uri:
            host = urlparse(
                raw_uri.replace("mongodb+srv://", "https://").replace("mongodb://", "https://")
            ).hostname
            if host:
                db_host = host
        stats_doc = await db.database.command("dbstats")
        db_used = float(stats_doc.get("dataSize", 0) or 0) + float(stats_doc.get("indexSize", 0) or 0)
        db_docs = int(stats_doc.get("objects", 0) or 0)
        if stats_doc.get("storageSize"):
            db_used = max(db_used, float(stats_doc["storageSize"]))
    except Exception as e:
        print(f"[stats] mongo: {e}")

    db_pct = (db_used / db_limit) * 100 if db_limit else 0
    db_free = max(0, db_limit - db_used)

    msg = f"""📊 <b>Bot Stats</b>

🤖 <b>Bot</b>
Status: {bot_status}
Users: <code>{total_users}</code>
Uptime: <code>{uptime_str}</code>
Admins: <code>{admins_count}</code>
Bot RAM: <code>{bot_ram_mb:.2f} MB</code>  ·  Bot CPU: <code>{bot_cpu:.0f}%</code>

🗄 <b>Database (MongoDB)</b>
DB #1 • active (<code>{db_name}</code>)
Host: <code>{db_host}</code>
Used: <code>{_fmt_bytes(db_used)}</code> / <code>{_fmt_bytes(db_limit)}</code>
<code>{_bar(db_pct)}</code> {db_pct:.0f}%  {_status_dot(db_pct)}
Free left: <code>{_fmt_bytes(db_free)}</code>  ·  Docs: <code>{db_docs:,}</code>

💻 <b>Server</b>
Disk: <code>{_fmt_bytes(used_disk)}</code> / <code>{_fmt_bytes(total_disk)}</code>  ({disk_pct:.0f}%)  {_status_dot(disk_pct)}
<code>{_bar(disk_pct)}</code>
RAM:  <code>{_fmt_bytes(ram_used)}</code> / <code>{_fmt_bytes(ram_total)}</code>  ({ram_pct:.0f}%)  {_status_dot(ram_pct)}
<code>{_bar(ram_pct)}</code>
CPU:  <code>{cpu_usage:.0f}%</code>  {_status_dot(cpu_usage)}
Net:  Sent <code>{_fmt_bytes(sent)}</code>  ·  Recv <code>{_fmt_bytes(recv)}</code>"""

    await reply.edit_text(
        msg,
        reply_markup=InlineKeyboardMarkup(
            [[styled_button("• ᴄʟᴏsᴇ •", style="danger", callback_data="close")]]
        ),
    )


#=====================================================================================##

WAIT_MSG = "<b>Working....</b>"

#=====================================================================================##


@Bot.on_message(filters.command('users') & filters.private & admin)
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await db.full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")

#=====================================================================================##

#AUTO-DELETE

@Bot.on_message(filters.private & filters.command('dlt_time') & admin)
async def set_delete_time(client: Bot, message: Message):
    try:
        duration = int(message.command[1])

        await db.set_del_timer(duration)

        await message.reply(f"<b>Dᴇʟᴇᴛᴇ Tɪᴍᴇʀ ʜᴀs ʙᴇᴇɴ sᴇᴛ ᴛᴏ <blockquote>{duration} sᴇᴄᴏɴᴅs.</blockquote></b>")

    except (IndexError, ValueError):
        await message.reply("<b>Pʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ᴅᴜʀᴀᴛɪᴏɴ ɪɴ sᴇᴄᴏɴᴅs.</b> Usage: /dlt_time {duration}")

@Bot.on_message(filters.private & filters.command('check_dlt_time') & admin)
async def check_delete_time(client: Bot, message: Message):
    duration = await db.get_del_timer()

    await message.reply(f"<b><blockquote>Cᴜʀʀᴇɴᴛ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ ɪs sᴇᴛ ᴛᴏ {duration}sᴇᴄᴏɴᴅs.</blockquote></b>")

#=====================================================================================##
