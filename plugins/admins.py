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

    # ── MongoDB (supports multi-URI + multi-name failover) ──
    uris = list(DB_URI) if isinstance(DB_URI, (list, tuple)) else ([DB_URI] if DB_URI else [])
    names = list(DB_NAME) if isinstance(DB_NAME, (list, tuple)) else ([DB_NAME] if DB_NAME else ["cluster0"])
    if not names:
        names = ["cluster0"]
    while len(names) < len(uris):
        names.append(names[-1])
    if not uris and names:
        uris = [""]  # still show name-only entry

    active_uri = (getattr(client.mongodb, "uri", None) or "").strip()
    active_name = (getattr(client.mongodb, "db_name", None) or "").strip()
    if not active_uri and uris:
        active_uri = uris[0]
    if not active_name and names:
        active_name = names[0]

    def _uri_host(u: str) -> str:
        if not u:
            return "unknown"
        try:
            host = urlparse(
                u.replace("mongodb+srv://", "https://").replace("mongodb://", "https://")
            ).hostname
            return host or "unknown"
        except Exception:
            return "unknown"

    # Per-DB status + combined storage across all reachable DBs
    per_db_limit = 512 * 1024 * 1024  # Atlas free-tier per cluster
    status_lines = []
    active_host = "unknown"
    total_used = 0.0
    total_docs = 0
    reachable_count = 0
    for idx, uri in enumerate(uris, start=1):
        name = names[idx - 1] if idx - 1 < len(names) else names[-1]
        is_active = bool(active_uri and uri == active_uri)
        reachable = False
        used = docs = 0
        try:
            if is_active:
                stats = await client.mongodb.db.command("dbstats")
                used = float(stats.get("dataSize", 0) or 0) + float(stats.get("indexSize", 0) or 0)
                docs = int(stats.get("objects", 0) or 0)
                if stats.get("storageSize"):
                    used = max(used, float(stats["storageSize"]))
                reachable = True
                active_host = _uri_host(uri)
            else:
                from pymongo import MongoClient as _SyncMC
                c = _SyncMC(uri, serverSelectionTimeoutMS=3000)
                c.admin.command("ping")
                try:
                    st = c[name].command("dbstats")
                    used = float(st.get("dataSize", 0) or 0) + float(st.get("indexSize", 0) or 0)
                    docs = int(st.get("objects", 0) or 0)
                    if st.get("storageSize"):
                        used = max(used, float(st["storageSize"]))
                except Exception:
                    pass
                c.close()
                reachable = True
        except Exception:
            reachable = False

        if reachable:
            reachable_count += 1
            total_used += used
            total_docs += docs

        mark = "• active" if is_active else ("• standby" if reachable else "• down")
        status_lines.append(
            f"DB #{idx} {mark} (<code>{name}</code>) · <code>{_fmt_bytes(used)}</code>"
        )

    if not status_lines:
        status_lines.append("DB #1 • none configured")

    # Combined limit = 512 MB × number of configured (or reachable) DBs
    n_dbs = max(len(uris), 1)
    combined_limit = per_db_limit * n_dbs
    pct = (total_used / combined_limit) * 100 if combined_limit else 0
    free = max(0, combined_limit - total_used)
    detail = (
        f"Host: <code>{active_host}</code>\n"
        f"Used: <code>{_fmt_bytes(total_used)}</code> / <code>{_fmt_bytes(combined_limit)}</code>  "
        f"(combined · {n_dbs} DB{'s' if n_dbs != 1 else ''})\n"
        f"<code>{_bar(pct)}</code> {pct:.0f}%  {_status_dot(pct)}\n"
        f"Free left: <code>{_fmt_bytes(free)}</code>  ·  Docs: <code>{total_docs:,}</code>"
    )
    db_block = "\n".join(status_lines) + "\n" + detail
    multi_note = ""
    if len(uris) > 1:
        multi_note = f"\nℹ️ Multi-DB: <code>{len(uris)}</code> pairs · combined storage shown above"

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
{db_block}{multi_note}

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
    if not query.from_user.id in client.admins:
        return await client.send_message(query.from_user.id, client.reply_text)
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
    if not query.from_user.id in client.admins:
        return await client.send_message(query.from_user.id, client.reply_text)
    ids_msg = await client.ask(query.from_user.id, "Send user ids seperated by a space in the next 60 seconds!\nEg: `838278682 83622928 82789928`", filters=filters.text, timeout=60)
    ids = ids_msg.text.split()
    
    try:
        for identifier in ids:
            if int(identifier) == client.owner:
                await client.send_message(query.from_user.id, "Nigga i can never remove the owner from the admin list!!")
                continue
            if int(identifier) in client.admins:
                client.admins.remove(int(identifier))
    except Exception as e:
        return await ids_msg.reply(f"Error: {e}")
    await admins(client, query)
    return await ids_msg.reply(f"__{len(ids)} admin {'id' if len(ids)==1 else 'ids'} have been removed!!__")
    

