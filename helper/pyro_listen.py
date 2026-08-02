"""
Lightweight ask/listen for Kurigram (no external pyromod).

Runs on the same asyncio loop as the Pyrogram client, so there is no
"Future attached to a different loop" crash.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional, Union

from pyrogram import Client, StopPropagation
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message


class ListenerTimeout(Exception):
    """Raised when ask/listen times out waiting for a reply."""


# client-id -> list of waiter dicts
_waiters: dict[int, list[dict[str, Any]]] = {}


def _client_key(client: Client) -> int:
    return id(client)


async def _match_filter(flt, client: Client, message: Message) -> bool:
    if flt is None:
        return True
    try:
        result = flt(client, message)
        if asyncio.iscoroutine(result):
            result = await result
        return bool(result)
    except Exception:
        return False


async def _dispatch(client: Client, message: Message):
    key = _client_key(client)
    waiters = list(_waiters.get(key, []))
    if not waiters:
        return

    uid = message.from_user.id if message.from_user else None
    cid = message.chat.id if message.chat else None

    for waiter in waiters:
        fut = waiter["future"]
        if fut.done():
            continue

        user_id = waiter.get("user_id")
        chat_id = waiter.get("chat_id")
        flt = waiter.get("filters")

        if user_id is not None:
            # normalize list/single
            allowed = user_id if isinstance(user_id, (list, tuple, set)) else [user_id]
            if uid not in allowed:
                continue

        if chat_id is not None:
            allowed_c = chat_id if isinstance(chat_id, (list, tuple, set)) else [chat_id]
            if cid not in allowed_c:
                continue

        if not await _match_filter(flt, client, message):
            continue

        fut.set_result(message)
        try:
            _waiters[key].remove(waiter)
        except (ValueError, KeyError):
            pass
        # Don't let normal command handlers also process this reply
        raise StopPropagation


def install_listen(client: Client) -> None:
    """Register the internal message waiter (once per client)."""
    if getattr(client, "_nexus_listen_installed", False):
        return

    async def _handler(c: Client, message: Message):
        await _dispatch(c, message)

    # Very high priority group so waiters see the message first
    client.add_handler(MessageHandler(_handler), group=-999)
    client._nexus_listen_installed = True

    # Bind instance methods
    client.listen = _listen.__get__(client, Client)  # type: ignore[method-assign]
    client.ask = _ask.__get__(client, Client)  # type: ignore[method-assign]


async def _listen(
    self: Client,
    filters=None,
    timeout: Optional[float] = 60,
    chat_id: Union[int, str, list, None] = None,
    user_id: Union[int, str, list, None] = None,
    **kwargs,
) -> Message:
    install_listen(self)
    loop = self.loop
    fut: asyncio.Future = loop.create_future()
    key = _client_key(self)
    waiter = {
        "future": fut,
        "filters": filters,
        "chat_id": chat_id,
        "user_id": user_id,
    }
    _waiters.setdefault(key, []).append(waiter)
    try:
        if timeout is None:
            return await fut
        return await asyncio.wait_for(fut, timeout=timeout)
    except asyncio.TimeoutError as e:
        try:
            _waiters[key].remove(waiter)
        except (ValueError, KeyError):
            pass
        raise ListenerTimeout("Listening timed out") from e


async def _ask(
    self: Client,
    chat_id: Union[int, str],
    text: str,
    filters=None,
    timeout: Optional[float] = 60,
    user_id: Union[int, str, list, None] = None,
    *args,
    **kwargs,
) -> Message:
    """Send a prompt, then wait for the next matching message."""
    install_listen(self)
    # Private chat: chat_id is usually the user id
    await self.send_message(chat_id, text, *args, **{k: v for k, v in kwargs.items() if k not in ("listener_type", "unallowed_click_alert", "message_id", "inline_message_id")})
    listen_user = user_id
    listen_chat = chat_id
    if listen_user is None and isinstance(chat_id, int) and chat_id > 0:
        listen_user = chat_id
    return await _listen(
        self,
        filters=filters,
        timeout=timeout,
        chat_id=listen_chat,
        user_id=listen_user,
    )
