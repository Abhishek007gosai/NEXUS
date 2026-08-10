from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from helper.helper_func import styled_button, safe_edit_text, safe_edit_caption, safe_edit_reply_markup
import time

import psutil
import shutil

#===============================================================#

async def admins(client, query):
    if not (query.from_user.id==client.owner):
        return await query.answer('This can only be used by owner.')
    msg = f"""<blockquote>**Admin Settings:**</blockquote>
**Admin User IDs:** {", ".join(f"`{a}`" for a in client.admins)}

__Use the appropriate button below to add or remove an admin based on your needs!__
"""
    reply_markup = InlineKeyboardMarkup([
        [styled_button('ᴀᴅᴅ ᴀᴅᴍɪɴ', style="primary", callback_data='add_admin'), styled_button('ʀᴇᴍᴏᴠᴇ ᴀᴅᴍɪɴ', style="primary", callback_data='rm_admin')],
        [styled_button('◂ ʙᴀᴄᴋ', style="primary", callback_data='settings')]]
    )
    await safe_edit_text(query.message, msg, reply_markup=reply_markup)
    return

#===============================================================#

def _bar(percent: float, width: int = 10) -> str:
    """Simple text progress bar."""
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
    """Human-readable size from bytes."""
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


def _fmt_uptime(seconds: int) -> str:
    days, rem = divmod(max(0, int(seconds)), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


@Client.on_message(filters.command("stats"))
async def usage_cmd(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply("✗ This can only be used by admins!")

    reply = await message.reply("📊 Collecting stats...")

    from datetime import datetime
    from config import DB_NAME, DB_URI
    from urllib.parse import urlparse

    # ── Bot ──
    try:
        total_users = len(await client.mongodb.full_userbase())
    except Exception:
        total_users = 0

    uptime_seconds = (datetime.now() - getattr(client, "uptime", datetime.now())).total_seconds()
    uptime_str = _fmt_uptime(uptime_seconds)
    admins_count = len(client.admins)

    try:
        process = psutil.Process()
        bot_cpu = process.cpu_percent(interval=0.3)
        bot_ram_mb = process.memory_info().rss / (1024 ** 2)
        bot_status = "🟢 Running"
    except Exception:
        bot_cpu, bot_ram_mb, bot_status = 0.0, 0.0, "🔴 Error"

    # ── Server ──
    total_disk, used_disk, free_disk = shutil.disk_usage("/")
    disk_pct = (used_disk / total_disk) * 100 if total_disk else 0

    ram = psutil.virtual_memory()
    ram_pct = ram.percent
    cpu_usage = psutil.cpu_percent(interval=0.5)

    try:
        net_io = psutil.net_io_counters()
        sent = net_io.bytes_sent
        recv = net_io.bytes_recv
    except Exception:
        sent = recv = 0

    # ── MongoDB ──
    db_host = "unknown"
    db_used = 0
    db_limit = 512 * 1024 * 1024  # Atlas free-tier default display
    db_docs = 0
    db_name = DB_NAME or "cluster0"
    try:
        uris = DB_URI if isinstance(DB_URI, (list, tuple)) else [DB_URI]
        raw_uri = (uris[0] if uris else "") or getattr(client.mongodb, "uri", "") or ""
        if raw_uri:
            host = urlparse(raw_uri.replace("mongodb+srv://", "https://").replace("mongodb://", "https://")).hostname
            if host:
                db_host = host
        # dbstats
        stats = await client.mongodb.db.command("dbstats")
        db_used = float(stats.get("dataSize", 0) or 0) + float(stats.get("indexSize", 0) or 0)
        db_docs = int(stats.get("objects", 0) or 0)
        # storageSize can be more accurate for "used"
        if stats.get("storageSize"):
            db_used = max(db_used, float(stats["storageSize"]))
    except Exception:
        pass

    db_pct = (db_used / db_limit) * 100 if db_limit else 0
    db_free = max(0, db_limit - db_used)

    # ── Mini Web App (Anime Index) ──
    web_storage = 0
    titles = web_users = searches = search_hits = requests_n = reports = visits = 0
    pages = api_hits = 0
    try:
        from helper import database as adb
        adb.init_db()
        titles = adb.anime_col.count_documents({})
        web_users = adb.users_col.count_documents({})
        searches = adb.searches_col.count_documents({})
        # sum of hit counts if present
        try:
            agg = list(adb.searches_col.aggregate([{"$group": {"_id": None, "hits": {"$sum": "$count"}}}]))
            search_hits = int(agg[0]["hits"]) if agg else 0
        except Exception:
            search_hits = 0
        requests_n = adb.requests_col.count_documents({})
        reports = adb.reports_col.count_documents({})
        # approximate storage from collection stats
        for col_name in ("anime", "users", "searches", "requests", "reports", "counters"):
            try:
                cs = adb._db.command("collStats", col_name)
                web_storage += float(cs.get("storageSize", 0) or 0) + float(cs.get("totalIndexSize", 0) or 0)
            except Exception:
                pass
        # visits counters if stored
        try:
            vdoc = adb.counters_col.find_one({"_id": "web_visits"}) or {}
            visits = int(vdoc.get("seq", 0) or 0)
            pages = int(vdoc.get("pages", 0) or 0)
            api_hits = int(vdoc.get("api", 0) or 0)
        except Exception:
            pass
        if not web_users and total_users:
            web_users = total_users
    except Exception:
        pass

    # ── Build message ──
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

🌐 <b>Mini Web App</b>
Storage: <code>{_fmt_bytes(web_storage)}</code>
Titles: <code>{titles}</code>  ·  Web users: <code>{web_users}</code>
Searches: <code>{searches}</code> ({search_hits} hits)  ·  Requests: <code>{requests_n}</code>
Reports: <code>{reports}</code>
Visits: <code>{visits}</code>  (pages <code>{pages}</code> · api <code>{api_hits}</code>)

💻 <b>Server</b>
Disk: <code>{_fmt_bytes(used_disk)}</code> / <code>{_fmt_bytes(total_disk)}</code>  ({disk_pct:.0f}%)  {_status_dot(disk_pct)}
<code>{_bar(disk_pct)}</code>
RAM:  <code>{_fmt_bytes(ram.used)}</code> / <code>{_fmt_bytes(ram.total)}</code>  ({ram_pct:.0f}%)  {_status_dot(ram_pct)}
<code>{_bar(ram_pct)}</code>
CPU:  <code>{cpu_usage:.0f}%</code>  {_status_dot(cpu_usage)}
Net:  Sent <code>{_fmt_bytes(sent)}</code>  ·  Recv <code>{_fmt_bytes(recv)}</code>"""

    await reply.edit_text(msg)
#===============================================================#

@Client.on_callback_query(filters.regex("^add_admin$"))
async def add_new_admins(client: Client, query: CallbackQuery):
    await query.answer()
    if query.from_user.id != client.owner:
        return await query.answer("✗ Only the owner can manage admins!", show_alert=True)
    ids_msg = await client.ask(query.from_user.id, "Send user ids seperated by a space in the next 60 seconds!\nEg: `838278682 83622928 82789928`", filters=filters.text, timeout=60)
    ids = ids_msg.text.split()
    
    try:
        for identifier in ids:
            if int(identifier) not in client.admins:
                client.admins.append(int(identifier))
            
    except Exception as e:
        return await ids_msg.reply(f"Error: {e}")
    await admins(client, query)
    return await ids_msg.reply(f"__{len(ids)} admin {'id' if len(ids)==1 else 'ids'} have been promoted!!__")
    
#===============================================================#

@Client.on_callback_query(filters.regex("^rm_admin$"))
async def remove_admins(client: Client, query: CallbackQuery):
    await query.answer()
    if query.from_user.id != client.owner:
        return await query.answer("✗ Only the owner can manage admins!", show_alert=True)
    ids_msg = await client.ask(query.from_user.id, "Send user ids seperated by a space in the next 60 seconds!\nEg: `838278682 83622928 82789928`", filters=filters.text, timeout=60)
    ids = ids_msg.text.split()
    
    try:
        for identifier in ids:
            if int(identifier) == client.owner:
                await client.send_message(query.from_user.id, "The owner can never be removed from the admin list.")
                continue
            if int(identifier) in client.admins:
                client.admins.remove(int(identifier))
    except Exception as e:
        return await ids_msg.reply(f"Error: {e}")
    await admins(client, query)
    return await ids_msg.reply(f"__{len(ids)} admin {'id' if len(ids)==1 else 'ids'} have been removed!!__")
    

