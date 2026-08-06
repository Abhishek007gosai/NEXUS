from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from helper.helper_func import styled_button
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
    await query.message.edit_text(msg, reply_markup=reply_markup)
    return

#===============================================================#

def _fmt_bytes(n: float) -> str:
    """Human-readable size."""
    try:
        n = float(n or 0)
    except (TypeError, ValueError):
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return f"{n:.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} PB"


def _progress_bar(percent: float, width: int = 10) -> str:
    """Simple text progress bar."""
    try:
        p = max(0.0, min(100.0, float(percent)))
    except (TypeError, ValueError):
        p = 0.0
    filled = int(round(width * p / 100.0))
    return "█" * filled + "░" * (width - filled)


def _status_emoji(percent: float) -> str:
    if percent < 70:
        return "🟢 OK"
    if percent < 90:
        return "🟡 High"
    return "🔴 Full"


async def _mongo_storage_section(client) -> str:
    """Simple MongoDB how-full section for /stats."""
    ATLAS_M0_LIMIT = 512 * 1024 * 1024  # free Atlas reference

    lines = ["<b>🗄 Database (MongoDB)</b>"]

    mongo = getattr(client, "mongodb", None)
    if mongo is None or getattr(mongo, "db", None) is None:
        lines.append("Not connected")
        return "\n".join(lines)

    targets = []
    clients = list(getattr(mongo, "_clients", None) or [])
    db_name = getattr(mongo, "_db_name", None) or getattr(mongo.db, "name", "?")
    active_idx = getattr(mongo, "_active_idx", 0)

    if clients:
        for i, (uri, mclient) in enumerate(clients):
            label = f"DB #{i + 1}"
            if i == active_idx:
                label += " • active"
            host_hint = ""
            try:
                after = uri.split("@", 1)[-1]
                host_hint = after.split("/", 1)[0].split("?", 1)[0][:36]
            except Exception:
                pass
            targets.append((label, host_hint, mclient, db_name))
    else:
        targets.append(("DB #1 • active", "", mongo.client, db_name))

    for label, host_hint, mclient, name in targets:
        try:
            stats = await mclient[name].command("dbStats")
            storage_size = float(stats.get("storageSize") or 0)
            index_size = float(stats.get("indexSize") or 0)
            total_size = float(stats.get("totalSize") or (storage_size + index_size))
            objects = int(stats.get("objects") or 0)

            fs_used = stats.get("fsUsedSize")
            fs_total = stats.get("fsTotalSize")
            if fs_total and fs_total > 0:
                used_ref = float(fs_used or total_size)
                limit_ref = float(fs_total)
                limit_note = "server disk"
            else:
                used_ref = total_size
                limit_ref = float(ATLAS_M0_LIMIT)
                limit_note = "free plan ~512 MB"

            percent = (used_ref / limit_ref * 100.0) if limit_ref else 0.0
            free_ref = max(0.0, limit_ref - used_ref)

            host_line = f"\nHost: <code>{host_hint}</code>" if host_hint else ""
            lines.append(
                f"<blockquote><b>{label}</b> (<code>{name}</code>){host_line}\n"
                f"Used: <b>{_fmt_bytes(total_size)}</b> / {_fmt_bytes(limit_ref)}\n"
                f"{_progress_bar(percent)} <b>{percent:.0f}%</b>  {_status_emoji(percent)}\n"
                f"Free left: {_fmt_bytes(free_ref)}  ·  Docs: {objects:,}\n"
                f"<i>Limit: {limit_note}</i></blockquote>"
            )
        except Exception as e:
            lines.append(f"<blockquote><b>{label}</b>\nError: <code>{str(e)[:60]}</code></blockquote>")

    if len(targets) > 1:
        lines.append("<i>Several DBs set — bot switches if one fills up.</i>")

    return "\n".join(lines)


@Client.on_message(filters.command("stats"))
async def usage_cmd(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply("Admins only.")

    reply = await message.reply("Loading stats...")

    # Users
    try:
        total_users = len(await client.mongodb.full_userbase())
    except Exception:
        total_users = "?"

    # Uptime
    from datetime import datetime
    up = datetime.now() - getattr(client, "uptime", datetime.now())
    d, rem = up.days, up.seconds
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    if d:
        uptime_str = f"{d}d {h}h {m}m"
    elif h:
        uptime_str = f"{h}h {m}m"
    else:
        uptime_str = f"{m}m"

    # Disk
    total, used, free = shutil.disk_usage("/")
    disk_pct = (used / total) * 100 if total else 0

    # RAM
    ram = psutil.virtual_memory()
    ram_pct = ram.percent

    # CPU
    cpu_pct = psutil.cpu_percent(interval=0.5)

    # Bot process
    try:
        proc = psutil.Process()
        bot_ram_mb = proc.memory_info().rss / (1024 ** 2)
        bot_cpu = proc.cpu_percent(interval=0.3)
        bot_ok = True
    except Exception:
        bot_ram_mb = 0.0
        bot_cpu = 0.0
        bot_ok = False

    # Network (optional)
    try:
        net = psutil.net_io_counters()
        up_mb = net.bytes_sent / (1024 ** 2)
        down_mb = net.bytes_recv / (1024 ** 2)
        net_line = f"Sent {_fmt_bytes(net.bytes_sent)}  ·  Recv {_fmt_bytes(net.bytes_recv)}"
    except Exception:
        net_line = "N/A"

    # MongoDB
    try:
        mongo_section = await _mongo_storage_section(client)
    except Exception as e:
        mongo_section = f"<b>🗄 Database (MongoDB)</b>\nError: <code>{str(e)[:60]}</code>"

    msg = f"""<b>📊 Bot Stats</b>

<b>🤖 Bot</b>
<blockquote>Status: {"🟢 Running" if bot_ok else "🔴 Error"}
Users: <b>{total_users}</b>
Uptime: <b>{uptime_str}</b>
Admins: {len(client.admins)}
Bot RAM: {_fmt_bytes(bot_ram_mb * 1024 * 1024)}  ·  Bot CPU: {bot_cpu:.0f}%</blockquote>

{mongo_section}

<b>💻 Server</b>
<blockquote>Disk: {_fmt_bytes(used)} / {_fmt_bytes(total)}  ({disk_pct:.0f}%)  {_status_emoji(disk_pct)}
{_progress_bar(disk_pct)}
RAM:  {_fmt_bytes(ram.used)} / {_fmt_bytes(ram.total)}  ({ram_pct:.0f}%)  {_status_emoji(ram_pct)}
{_progress_bar(ram_pct)}
CPU:  {cpu_pct:.0f}%  {_status_emoji(cpu_pct)}
Net:  {net_line}</blockquote>

<i>Tip: watch Database % — add another MongoDB URL in DB_URI when it gets high.</i>"""

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
    

