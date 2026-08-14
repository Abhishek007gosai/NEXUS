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
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, PeerIdInvalid, UserDeactivated
from bot import Bot
from config import *
from helper_func import *
from database.database import *

#=====================================================================================##

REPLY_ERROR = "<code>Use this command as a reply to any telegram message without any spaces.</code>"

# Workers = concurrent sends. 60 is aggressive but works well for ~30k users.
# If you get long FloodWaits often, drop to 40–50.
BROADCAST_WORKERS = 60

# Progress edit interval (users). Higher = fewer status API calls = slightly faster.
PROGRESS_EVERY = 500

# How often the background deleter checks Mongo for due messages (seconds)
DELETE_POLL_INTERVAL = 15

#=====================================================================================##


def _fw_seconds(e: FloodWait) -> float:
    return float(getattr(e, "value", None) or getattr(e, "x", 5))


async def pending_delete_worker(client: Bot):
    """
    Background loop: delete messages whose delete_at has passed.
    Survives bot restarts because schedule is stored in MongoDB.
    Safe for 1-day (or longer) /dbroadcast timers.
    """
    while True:
        try:
            now = time.time()
            due = await db.get_due_deletes(now, limit=400)
            if due:
                remove_ids = []
                for doc in due:
                    try:
                        await client.delete_messages(doc["chat_id"], doc["message_id"])
                    except FloodWait as e:
                        await asyncio.sleep(min(_fw_seconds(e), 60))
                        try:
                            await client.delete_messages(doc["chat_id"], doc["message_id"])
                        except Exception:
                            pass
                    except Exception:
                        pass
                    remove_ids.append(doc["_id"])
                await db.remove_pending_deletes_bulk(remove_ids)
        except Exception as e:
            print(f"[pending_delete_worker] {e}")
        await asyncio.sleep(DELETE_POLL_INTERVAL)


async def _broadcast_to_users(
    client: Bot,
    admin_msg: Message,
    broadcast_msg: Message,
    user_ids: list,
    *,
    pin: bool = False,
    auto_delete_sec: int | None = None,
    title: str = "Broadcast",
):
    """
    Fast broadcast for large userbases (~30k+).
    Fixed worker pool + queue = low memory, high throughput.
    Auto-delete is stored in Mongo so 1-day timers survive restarts.
    """
    total = len(user_ids)
    if total == 0:
        await admin_msg.reply("No users in database.")
        return

    successful = 0
    blocked = 0
    deleted = 0
    unsuccessful = 0
    processed = 0

    start_time = time.time()
    lock = asyncio.Lock()
    queue: asyncio.Queue = asyncio.Queue()
    pending_batch: list = []  # collect {chat_id, message_id, delete_at} then bulk insert

    for uid in user_ids:
        queue.put_nowait(uid)

    pls_wait = await admin_msg.reply(
        f"<i>{title} starting…\nUsers: <code>{total}</code> | Workers: <code>{BROADCAST_WORKERS}</code></i>"
    )

    delete_at = None
    if auto_delete_sec and auto_delete_sec > 0:
        delete_at = time.time() + auto_delete_sec

    async def update_progress():
        async with lock:
            current = processed
            s, b, d, u = successful, blocked, deleted, unsuccessful
        elapsed = time.time() - start_time
        speed = current / elapsed if elapsed > 0 else 0
        eta = (total - current) / speed if speed > 0 else 0
        try:
            await pls_wait.edit(
                f"<b><u>{title} in progress…</u></b>\n\n"
                f"Processed: <code>{current}/{total}</code>\n"
                f"Successful: <code>{s}</code>\n"
                f"Blocked: <code>{b}</code>\n"
                f"Deleted: <code>{d}</code>\n"
                f"Failed: <code>{u}</code>\n\n"
                f"Speed: <code>{speed:.1f}</code> users/sec\n"
                f"ETA: <code>{int(eta)}s</code>"
            )
        except FloodWait as e:
            await asyncio.sleep(min(_fw_seconds(e), 30))
        except Exception:
            pass

    async def worker():
        nonlocal successful, blocked, deleted, unsuccessful, processed
        while True:
            try:
                chat_id = queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            status = "fail"

            for _ in range(4):
                try:
                    sent_msg = await broadcast_msg.copy(chat_id)

                    if pin:
                        try:
                            await client.pin_chat_message(
                                chat_id=chat_id,
                                message_id=sent_msg.id,
                                both_sides=True,
                            )
                        except Exception:
                            pass

                    # Durable schedule — survives restart (works for 1 day+)
                    if delete_at is not None:
                        async with lock:
                            pending_batch.append({
                                "chat_id": chat_id,
                                "message_id": sent_msg.id,
                                "delete_at": delete_at,
                            })
                            # Flush in chunks to avoid huge RAM lists
                            if len(pending_batch) >= 200:
                                batch = pending_batch[:]
                                pending_batch.clear()
                                try:
                                    await db.add_pending_deletes_bulk(batch)
                                except Exception as e:
                                    print(f"pending_deletes bulk insert error: {e}")

                    status = "success"
                    break

                except FloodWait as e:
                    await asyncio.sleep(min(_fw_seconds(e), 90))
                    continue

                except (UserIsBlocked, PeerIdInvalid):
                    try:
                        await db.del_user(chat_id)
                    except Exception:
                        pass
                    status = "blocked"
                    break

                except (InputUserDeactivated, UserDeactivated):
                    try:
                        await db.del_user(chat_id)
                    except Exception:
                        pass
                    status = "deleted"
                    break

                except Exception:
                    status = "fail"
                    break

            async with lock:
                if status == "success":
                    successful += 1
                elif status == "blocked":
                    blocked += 1
                elif status == "deleted":
                    deleted += 1
                else:
                    unsuccessful += 1
                processed += 1
                current = processed

            if current % PROGRESS_EVERY == 0 or current == total:
                await update_progress()

            queue.task_done()

    workers = [asyncio.create_task(worker()) for _ in range(BROADCAST_WORKERS)]
    await asyncio.gather(*workers)

    # Flush remaining pending deletes
    if pending_batch:
        try:
            await db.add_pending_deletes_bulk(pending_batch)
        except Exception as e:
            print(f"pending_deletes final flush error: {e}")

    elapsed = time.time() - start_time
    speed = total / elapsed if elapsed > 0 else 0
    status_text = (
        f"<b><u>{title} Completed</u></b>\n\n"
        f"Total Users: <code>{total}</code>\n"
        f"Successful: <code>{successful}</code>\n"
        f"Blocked Users: <code>{blocked}</code>\n"
        f"Deleted Accounts: <code>{deleted}</code>\n"
        f"Unsuccessful: <code>{unsuccessful}</code>\n\n"
        f"Time taken: <code>{int(elapsed)}s</code> "
        f"(~<code>{speed:.1f}</code> users/sec)"
    )
    if auto_delete_sec:
        hours = auto_delete_sec / 3600
        if hours >= 24:
            human = f"{hours/24:.1f} day(s)"
        elif hours >= 1:
            human = f"{hours:.1f} hour(s)"
        else:
            human = f"{auto_delete_sec} second(s)"
        status_text += (
            f"\n\n⏱ Auto-delete after: <code>{human}</code>"
            f"\n(Stored in DB — survives bot restarts)"
        )

    try:
        await pls_wait.edit(status_text)
    except Exception:
        await admin_msg.reply(status_text)


#=====================================================================================##
# /pbroadcast
#=====================================================================================##

@Bot.on_message(filters.private & filters.command("pbroadcast") & admin)
async def send_pin_text(client: Bot, message: Message):
    if not message.reply_to_message:
        msg = await message.reply("Reply to a message to broadcast and pin it.")
        await asyncio.sleep(8)
        await msg.delete()
        return

    users = await db.full_userbase()
    await _broadcast_to_users(
        client, message, message.reply_to_message, users,
        pin=True, title="Pin Broadcast",
    )


#=====================================================================================##
# /broadcast
#=====================================================================================##

@Bot.on_message(filters.private & filters.command("broadcast") & admin)
async def send_text(client: Bot, message: Message):
    if not message.reply_to_message:
        msg = await message.reply(REPLY_ERROR)
        await asyncio.sleep(8)
        await msg.delete()
        return

    users = await db.full_userbase()
    await _broadcast_to_users(
        client, message, message.reply_to_message, users,
        title="Broadcast",
    )


#=====================================================================================##
# /dbroadcast
#=====================================================================================##

@Bot.on_message(filters.private & filters.command("dbroadcast") & admin)
async def delete_broadcast(client: Bot, message: Message):
    if not message.reply_to_message:
        msg = await message.reply(
            "Please reply to a message to broadcast it with Auto-Delete.\n"
            "Usage: <code>/dbroadcast {duration}</code>\n\n"
            "Examples:\n"
            "• <code>/dbroadcast 60</code> — 1 minute\n"
            "• <code>/dbroadcast 3600</code> — 1 hour\n"
            "• <code>/dbroadcast 86400</code> — 1 day"
        )
        await asyncio.sleep(10)
        await msg.delete()
        return

    try:
        duration = int(message.command[1])
        if duration < 1:
            raise ValueError
    except (IndexError, ValueError):
        await message.reply(
            "<b>Please use a valid duration in seconds.</b>\n\n"
            "Usage: <code>/dbroadcast {duration}</code>\n"
            "• <code>/dbroadcast 60</code> — 1 minute\n"
            "• <code>/dbroadcast 3600</code> — 1 hour\n"
            "• <code>/dbroadcast 86400</code> — 1 day"
        )
        return

    users = await db.full_userbase()
    await _broadcast_to_users(
        client, message, message.reply_to_message, users,
        auto_delete_sec=duration, title="Broadcast with Auto-Delete",
    )
