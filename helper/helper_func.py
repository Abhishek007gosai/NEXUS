import base64
import re
import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import (
    UserNotParticipant,
    Forbidden,
    PeerIdInvalid,
    ChatAdminRequired,
    FloodWait,
)
from datetime import datetime, timedelta
from pyrogram import errors

# Optional: SlowmodeWait / RetryAfter exist on some forks
try:
    from pyrogram.errors import SlowmodeWait
except ImportError:
    SlowmodeWait = None
try:
    from pyrogram.errors import RetryAfter
except ImportError:
    RetryAfter = None


# =============================================================================
# Telegram rate-limit helpers
# =============================================================================

def flood_wait_seconds(exc) -> float:
    """Extract wait seconds from FloodWait / SlowmodeWait / RetryAfter.

    Supports both legacy ``e.x`` and modern ``e.value`` attributes.
    """
    for attr in ("value", "x", "retry_after"):
        v = getattr(exc, attr, None)
        if v is not None:
            try:
                return max(0.0, float(v))
            except (TypeError, ValueError):
                continue
    return 1.0


async def sleep_on_flood(exc, logger=None, label: str = "") -> float:
    """Sleep for the duration required by a flood / rate-limit error."""
    seconds = flood_wait_seconds(exc)
    # Cap extremely long waits so the process doesn't hang forever
    seconds = min(seconds, 600.0)
    # Telegram sometimes returns 0; always wait a tiny bit
    seconds = max(seconds, 0.5)
    msg = f"FloodWait {label}: sleeping {seconds:.1f}s"
    if logger:
        try:
            logger.info(msg)
        except Exception:
            print(msg)
    else:
        print(msg)
    await asyncio.sleep(seconds)
    return seconds


async def retry_on_flood(
    factory,
    *,
    max_retries: int = 5,
    logger=None,
    label: str = "",
    extra_exceptions=(),
):
    """Run an async callable, retrying on Telegram rate-limit errors.

    ``factory`` must be a zero-arg async callable (or coroutine function)
    so each retry creates a fresh awaitable.

    Handles: FloodWait, SlowmodeWait, RetryAfter, plus any extra exception
    types passed in ``extra_exceptions``.
    """
    rate_errors = [FloodWait]
    if SlowmodeWait is not None:
        rate_errors.append(SlowmodeWait)
    if RetryAfter is not None:
        rate_errors.append(RetryAfter)
    rate_errors.extend(extra_exceptions)
    rate_errors = tuple(rate_errors)

    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return await factory()
        except rate_errors as e:
            last_exc = e
            if attempt >= max_retries:
                break
            await sleep_on_flood(
                e,
                logger=logger,
                label=f"{label} attempt {attempt + 1}/{max_retries}",
            )
    if last_exc is not None:
        raise last_exc


# Small delay between consecutive media copies to reduce flood pressure.
# Tunable; 0 disables pacing.
SEND_PACING_SECONDS = 0


async def paced_copy(msg, **kwargs):
    """``msg.copy`` with FloodWait retries + optional inter-send pacing."""
    result = await retry_on_flood(lambda: msg.copy(**kwargs), max_retries=5, label="copy")
    if SEND_PACING_SECONDS > 0:
        await asyncio.sleep(SEND_PACING_SECONDS)
    return result


# =============================================================================
# API compatibility helpers (kurigram / pyrogram deprecations)
# =============================================================================

def _link_preview_kwargs(disable: bool = True) -> dict:
    """Prefer ``link_preview_options``; fall back to ``disable_web_page_preview``."""
    try:
        from pyrogram.types import LinkPreviewOptions
        return {"link_preview_options": LinkPreviewOptions(is_disabled=bool(disable))}
    except Exception:
        return {"disable_web_page_preview": bool(disable)}


def get_forward_info(message):
    """Return ``(chat_id, message_id)`` from a forwarded message.

    Uses ``message.forward_origin`` when available, otherwise the legacy
    ``forward_from_chat`` / ``forward_from_message_id`` attributes.
    Returns ``(None, None)`` for hidden-user forwards or non-forwards.
    """
    if message is None:
        return None, None

    origin = getattr(message, "forward_origin", None)
    if origin is not None:
        chat = getattr(origin, "chat", None) or getattr(origin, "sender_chat", None)
        mid = getattr(origin, "message_id", None)
        if chat is not None and mid is not None:
            return getattr(chat, "id", None), mid
        return None, None

    chat = getattr(message, "forward_from_chat", None)
    mid = getattr(message, "forward_from_message_id", None)
    if chat is not None and mid is not None:
        return chat.id, mid
    return None, None


def is_hidden_forward(message) -> bool:
    """True when the forward hides the original sender (no channel metadata)."""
    if message is None:
        return False
    origin = getattr(message, "forward_origin", None)
    if origin is not None:
        if getattr(origin, "sender_user_name", None) and not (
            getattr(origin, "chat", None) or getattr(origin, "sender_chat", None)
        ):
            return True
        if "Hidden" in type(origin).__name__:
            return True
        return False
    return bool(getattr(message, "forward_sender_name", None))


def is_forwarded_message(message) -> bool:
    """True if the message is a forward (new or legacy API)."""
    if message is None:
        return False
    if getattr(message, "forward_origin", None) is not None:
        return True
    if getattr(message, "forward_date", None) is not None:
        return True
    if getattr(message, "forward_from_chat", None) is not None:
        return True
    if getattr(message, "forward_sender_name", None) is not None:
        return True
    return False


async def safe_delete(msg):
    """Delete a message if it exists; never raise on None / already-gone."""
    if msg is None:
        return
    try:
        await msg.delete()
    except Exception:
        pass


async def safe_reply(message, text, **kwargs):
    """``message.reply`` without the deprecated ``quote`` argument."""
    kwargs.pop("quote", None)
    # Normalize link-preview args
    if "link_preview_options" not in kwargs:
        disable = kwargs.pop("disable_web_page_preview", True)
        kwargs.update(_link_preview_kwargs(bool(disable)))
    else:
        kwargs.pop("disable_web_page_preview", None)
    return await message.reply(text, **kwargs)

# Telegram Bot API button colors (Kurigram / docs.kurigram.icu/api/enums/ButtonStyle)
# PRIMARY = blue, SUCCESS = green, DANGER = red, DEFAULT = client theme
try:
    from pyrogram.enums import ButtonStyle
except ImportError:  # older forks without the enum
    ButtonStyle = None

_STYLE_MAP = {}
if ButtonStyle is not None:
    _STYLE_MAP = {
        "primary": ButtonStyle.PRIMARY,
        "success": ButtonStyle.SUCCESS,
        "danger": ButtonStyle.DANGER,
        "default": getattr(ButtonStyle, "DEFAULT", None),
        ButtonStyle.PRIMARY: ButtonStyle.PRIMARY,
        ButtonStyle.SUCCESS: ButtonStyle.SUCCESS,
        ButtonStyle.DANGER: ButtonStyle.DANGER,
    }
    if hasattr(ButtonStyle, "DEFAULT"):
        _STYLE_MAP[ButtonStyle.DEFAULT] = ButtonStyle.DEFAULT

#===============================================================#

def styled_button(text, style=None, **kwargs):
    """Create an InlineKeyboardButton with Telegram native colors.

    style: "primary" (blue) | "success" (green) | "danger" (red)
           or ButtonStyle.PRIMARY / SUCCESS / DANGER

    Needs Kurigram (ButtonStyle). Always attaches the enum on the button
    object so write() serializes bg_primary / bg_success / bg_danger.
    """
    resolved = None
    if style is not None and ButtonStyle is not None:
        if isinstance(style, ButtonStyle):
            resolved = style
        elif isinstance(style, str):
            resolved = _STYLE_MAP.get(style.lower().strip())
        else:
            resolved = _STYLE_MAP.get(style)

    # Prefer constructor with style=
    if resolved is not None:
        try:
            btn = InlineKeyboardButton(text, style=resolved, **kwargs)
            # Guarantee enum (never a bare string — strings make all bg_* False)
            btn.style = resolved
            return btn
        except TypeError:
            pass

    btn = InlineKeyboardButton(text, **kwargs)
    if resolved is not None:
        try:
            btn.style = resolved
        except Exception:
            pass
    return btn

#===============================================================#

#===============================================================#

async def encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = (base64_bytes.decode("ascii")).strip("=")
    return base64_string

#===============================================================#

async def decode(base64_string):
    base64_string = base64_string.strip("=") # links generated before this commit will be having = sign, hence striping them to handle padding errors.
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes) 
    string = string_bytes.decode("ascii")
    return string

#===============================================================#

async def get_messages(client, message_ids):
    messages = []
    total_messages = 0
    logger = None
    try:
        logger = client.LOGGER(__name__, client.name)
    except Exception:
        pass
    while total_messages != len(message_ids):
        temb_ids = message_ids[total_messages:total_messages + 200]
        try:
            msgs = await retry_on_flood(
                lambda ids=temb_ids: get_messages_from_db_channels(client, ids),
                max_retries=5,
                logger=logger,
                label="get_messages",
            )
        except Exception:
            msgs = []
        total_messages += len(temb_ids)
        messages.extend(msgs)
    return messages

#===============================================================#

async def get_message_id(client, message):
    """Get message ID and source channel ID from forwarded message or link"""
    fwd_chat_id, fwd_msg_id = get_forward_info(message)
    if fwd_chat_id is not None and fwd_msg_id is not None:
        if fwd_chat_id == client.db:
            return fwd_msg_id, client.db
        db_channels = getattr(client, 'db_channels', {})
        for channel_id_str in db_channels.keys():
            if fwd_chat_id == int(channel_id_str):
                return fwd_msg_id, int(channel_id_str)
        return 0, 0
    if is_hidden_forward(message):
        return 0, 0
    if message.text:
        pattern = r"https://t.me/(?:c/)?(.*)/(\d+)"
        matches = re.match(pattern,message.text)
        if not matches:
            return 0, 0
        channel_id = matches.group(1)
        msg_id = int(matches.group(2))
        if channel_id.isdigit():
            # Check primary DB channel
            if f"-100{channel_id}" == str(client.db):
                return msg_id, client.db
            # Check against multiple DB channels
            db_channels = getattr(client, 'db_channels', {})
            for channel_id_str in db_channels.keys():
                if f"-100{channel_id}" == channel_id_str:
                    return msg_id, int(channel_id_str)
        else:
            # Check by username for primary DB channel
            if hasattr(client, 'db_channel') and channel_id == client.db_channel.username:
                return msg_id, client.db
            # Check against multiple DB channels usernames (if needed)
            db_channels = getattr(client, 'db_channels', {})
            for channel_id_str, channel_data in db_channels.items():
                try:
                    chat = await client.get_chat(int(channel_id_str))
                    if hasattr(chat, 'username') and chat.username == channel_id:
                        return msg_id, int(channel_id_str)
                except:
                    continue
    else:
        return 0, 0


#===============================================================#

async def get_message_id_legacy(client, message):
    """Legacy function for backward compatibility - returns only message ID"""
    msg_id, _ = await get_message_id(client, message)
    return msg_id


#===============================================================#

async def get_messages_from_db_channels(client, temb_ids):
    """Get messages from multiple DB channels - tries primary first, then falls back to others.

    FloodWait is handled by the caller via ``retry_on_flood``; inner channel
    fetches also retry individually so a single slow channel doesn't abort
    the whole batch.
    """
    messages = []
    logger = None
    try:
        logger = client.LOGGER(__name__, client.name)
    except Exception:
        pass

    primary_db = getattr(client, 'primary_db_channel', client.db)

    async def _fetch(chat_id, ids):
        return await client.get_messages(chat_id=chat_id, message_ids=ids)

    try:
        msgs = await retry_on_flood(
            lambda: _fetch(primary_db, temb_ids),
            max_retries=5,
            logger=logger,
            label=f"get_messages primary:{primary_db}",
        )
        # Filter out None messages (deleted/not found)
        valid_msgs = [msg for msg in (msgs or []) if msg is not None]
        messages.extend(valid_msgs)
        found_ids = {msg.id for msg in valid_msgs}
        missing_ids = [mid for mid in temb_ids if mid not in found_ids]

        if not missing_ids:
            return messages

        db_channels = getattr(client, 'db_channels', {})
        for channel_id_str, channel_data in db_channels.items():
            if not channel_data.get('is_active', True):
                continue
            if int(channel_id_str) == primary_db:
                continue
            try:
                additional_msgs = await retry_on_flood(
                    lambda cid=int(channel_id_str), ids=list(missing_ids): _fetch(cid, ids),
                    max_retries=3,
                    logger=logger,
                    label=f"get_messages channel:{channel_id_str}",
                )
                valid_additional = [msg for msg in (additional_msgs or []) if msg is not None]
                messages.extend(valid_additional)
                found_additional_ids = {msg.id for msg in valid_additional}
                missing_ids = [mid for mid in missing_ids if mid not in found_additional_ids]
                if not missing_ids:
                    break
            except Exception as e:
                if logger:
                    logger.warning(f"Error getting messages from DB channel {channel_id_str}: {e}")
                continue

    except Exception as e:
        if logger:
            logger.warning(f"Error getting messages from DB channels: {e}")

    return messages

#===============================================================#

def get_readable_time(seconds: int) -> str:
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    hmm = len(time_list)
    for x in range(hmm):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    time_list.reverse()
    up_time += ":".join(time_list)
    return up_time

#===============================================================#

async def is_bot_admin(client, channel_id):
    try:
        bot = await client.get_chat_member(channel_id, "me")
        if bot.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            if bot.privileges:
                required_rights = ["can_invite_users", "can_delete_messages"]
                missing_rights = [right for right in required_rights if not getattr(bot.privileges, right, False)]
                if missing_rights:
                    return False, f"Bot is missing the following rights: {', '.join(missing_rights)}"
            return True, None
        return False, "Bot is not an admin in the channel."
    except errors.ChatAdminRequired:
        return False, "Bot lacks perminsion to access admin information in this channel."
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

#===============================================================#

async def check_subscription(client, user_id):
    """Enhanced subscription check with better request channel handling."""
    statuses = {}

    # Ensure user exists in database
    if not await client.mongodb.present_user(user_id):
        await client.mongodb.add_user(user_id)

    for channel_id, (channel_name, channel_link, request, timer) in client.fsub_dict.items():
        try:
            # Get actual membership status first
            user = await client.get_chat_member(channel_id, user_id)
            actual_status = user.status
            
            # If user is already a member, admin, or owner
            if actual_status in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
                await client.mongodb.update_fsub_status(user_id, channel_id, "joined")
                await client.mongodb.add_channel_user(channel_id, user_id)
                
                # If there was a pending join request, mark it as approved
                if request and await client.mongodb.has_submitted_join_request(user_id, channel_id):
                    await client.mongodb.update_join_request_status(user_id, channel_id, "approved")
                
                statuses[channel_id] = actual_status
                continue
            
            # User is not a member - check if they left after being approved  
            if request:
                # For request channels, check if user has submitted a request
                has_request = await client.mongodb.has_submitted_join_request(user_id, channel_id)
                if has_request:
                    # User has submitted request but not yet a member
                    request_status = await client.mongodb.get_join_request_status(user_id, channel_id)
                    
                    if request_status == "approved":
                        # Request was approved but user still not in channel
                        # This means user might have left after approval - force them to rejoin
                        await client.mongodb.update_fsub_status(user_id, channel_id, "left")
                        await client.mongodb.remove_join_request(user_id, channel_id)
                        statuses[channel_id] = ChatMemberStatus.BANNED
                    else:
                        # Request is still pending, allow user to proceed
                        await client.mongodb.update_fsub_status(user_id, channel_id, "request_submitted")
                        statuses[channel_id] = ChatMemberStatus.MEMBER  # Treat as subscribed for request channels
                else:
                    # No request submitted yet for request channel
                    await client.mongodb.update_fsub_status(user_id, channel_id, "not_requested")
                    statuses[channel_id] = ChatMemberStatus.BANNED
            else:
                # Regular channel (not request), user must be a member
                await client.mongodb.update_fsub_status(user_id, channel_id, "left")
                await client.mongodb.remove_channel_user(channel_id, user_id)
                statuses[channel_id] = ChatMemberStatus.BANNED
                
        except UserNotParticipant:
            # User is not in the channel
            await client.mongodb.update_fsub_status(user_id, channel_id, "left")
            await client.mongodb.remove_channel_user(channel_id, user_id)
            
            if request:
                # For request channels, check if user has submitted a request
                has_request = await client.mongodb.has_submitted_join_request(user_id, channel_id)
                if has_request:
                    # User has submitted request but not in channel - still allow access for request channels
                    await client.mongodb.update_fsub_status(user_id, channel_id, "request_submitted")
                    statuses[channel_id] = ChatMemberStatus.MEMBER  # Treat as subscribed for request channels
                else:
                    # No request submitted yet
                    await client.mongodb.update_fsub_status(user_id, channel_id, "not_requested")
                    statuses[channel_id] = ChatMemberStatus.BANNED
            else:
                # Regular channel, user must join
                statuses[channel_id] = ChatMemberStatus.BANNED
                
        except Forbidden:
            client.LOGGER(__name__, client.name).warning(f"Bot lacks permission for {channel_name}.")
            statuses[channel_id] = None
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Error checking {channel_name}: {e}")
            statuses[channel_id] = None

    return statuses

#===============================================================#

def is_user_subscribed(statuses):
    """Check if user is subscribed to all channels."""
    return all(
        status in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}
        for status in statuses.values() if status is not None
    ) and bool(statuses)

#===============================================================#

def force_sub(func):
    """Decorator to enforce force subscription before executing a command."""
    async def wrapper(client: Client, message: Message):
        if not client.fsub_dict:
            return await func(client, message)
        photo = client.messages.get('FSUB_PHOTO', '')
        # protect_content=True → users cannot forward the force-sub message
        if photo:
            msg = await message.reply_photo(
                caption="<b>ᴡᴀɪᴛ ᴀ sᴇᴄᴏɴᴅ.....</b>",
                photo=photo,
                protect_content=True,
            )
        else:
            msg = await message.reply(
                "<code><b>ᴡᴀɪᴛ ᴀ sᴇᴄᴏɴᴅ.....</b></code>",
                protect_content=True,
            )
        user_id = message.from_user.id
        statuses = await check_subscription(client, user_id)

        if is_user_subscribed(statuses):
            await msg.delete()
            return await func(client, message)

        # User is not subscribed to all channels
        buttons = []
        channels_message = f"{client.messages.get('FSUB', '')}\n\n"

        for channel_id, (channel_name, channel_link, request, timer) in client.fsub_dict.items():
            status = statuses.get(channel_id, None)

            # Generate invite link if needed
            if timer > 0:
                expire_time = datetime.now() + timedelta(minutes=timer)
                try:
                    invite = await client.create_chat_invite_link(
                        chat_id=channel_id,
                        expire_date=expire_time,
                        creates_join_request=request
                    )
                    channel_link = invite.invite_link
                except Exception as e:
                    client.LOGGER(__name__, client.name).warning(f"Error creating invite link for {channel_name}: {e}")

            # Add button based on user status
            if status not in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
                # Check if user has already submitted request for request channels
                if request and await client.mongodb.has_submitted_join_request(user_id, channel_id):
                    request_status = await client.mongodb.get_join_request_status(user_id, channel_id)
                    if request_status == "pending":
                        # Don't add button if request is still pending
                        continue
                    elif request_status == "approved":
                        # User can now join the channel
                        button_text = f"{channel_name}"
                    else:
                        button_text = f"{channel_name}"
                else:
                    # User hasn't submitted request or it's a regular channel
                    if request:
                        button_text = f"{channel_name}"
                    else:
                        button_text = f"{channel_name}"
                
                buttons.append(styled_button("𝙹𝙾𝙸𝙽 𝙲𝙷𝙰𝙽𝙽𝙴𝙻", style="primary", url=channel_link))

        # Arrange join channel buttons 2 per row; if an odd one is left over,
        # it gets its own full-width row
        rows = []
        for i in range(0, len(buttons), 2):
            pair = buttons[i:i + 2]
            rows.append(pair)

        # Add "Try Again" button if needed (always full-width, own row)
        from_link = message.text.split(" ")
        if len(from_link) > 1:
            try_again_link = f"https://t.me/{client.username}/?start={from_link[1]}"
            rows.append([styled_button("🔄 Try Again", style="primary", url=try_again_link)])

        buttons_markup = InlineKeyboardMarkup(rows)
        buttons_markup = None if not rows else buttons_markup

        # Edit message with status update and buttons
        try:
            await msg.edit_text(text=channels_message, reply_markup=buttons_markup)
        except Exception as e:
            client.LOGGER(__name__, client.name).warning(f"Error updating force sub message: {e}")
            # Fallback: send new message if edit fails
            try:
                await msg.delete()
                await message.reply(
                    text=channels_message,
                    reply_markup=buttons_markup,
                    protect_content=True,
                )
            except Exception:
                pass


    return wrapper

#===============================================================#

#Time conversion for auto delete timer
def convert_time(duration_seconds: int) -> str:
    periods = [
        ('Yᴇᴀʀ', 60 * 60 * 24 * 365),
        ('Mᴏɴᴛʜ', 60 * 60 * 24 * 30),
        ('Day', 60 * 60 * 24),
        ('Hour', 60 * 60),
        ('Minute', 60),
        ('Second', 1)
    ]

    parts = []
    for period_name, period_seconds in periods:
        if duration_seconds >= period_seconds:
            num_periods = duration_seconds // period_seconds
            duration_seconds %= period_seconds
            parts.append(f"{num_periods} {period_name}{'s' if num_periods > 1 else ''}")

    if len(parts) == 0:
        return "0 Sᴇᴄᴏɴᴅ"
    elif len(parts) == 1:
        return parts[0]
    else:
        return ', '.join(parts[:-1]) +' ᴀɴᴅ '+ parts[-1]

#===============================================================#
#.........Auto Delete Functions.......#
#===============================================================#

DEL_MSG = """<b>» ᴛʜɪs ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ {time}<blockquote>ᴘʟᴇᴀsᴇ sᴀᴠᴇ ᴏʀ ғᴏʀᴡᴀʀᴅ ɪᴛ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ʙᴇғᴏʀᴇ ɪᴛ ɢᴇᴛs ᴅᴇʟᴇᴛᴇᴅ.</blockquote></b>"""

#Function for provide auto delete notification message
async def auto_del_notification(bot_username, msg, delay_time, transfer):
    if msg is None:
        return
    temp = await msg.reply_text(
        DEL_MSG.format(username=bot_username, time=convert_time(delay_time)),
        **_link_preview_kwargs(True),
    )

    await asyncio.sleep(delay_time)
    try:
        if transfer:
            try:
                name = "• ɢᴇᴛ ᴀɢᴀɪɴ •"
                link = f"https://t.me/{bot_username}?start={transfer}"
                button = [[styled_button(text=f"{name}", style="primary", url=link), styled_button(text="ᴄʟᴏsᴇ •", style="danger", callback_data="close")]]

                await temp.edit_text(
                    text=f"<b>ᴘʀᴇᴠɪᴏᴜs ᴍᴇssᴀɢᴇ ᴡᴀs ᴅᴇʟᴇᴛᴇᴅ<blockquote>ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ɢᴇᴛ ᴛʜᴇ ғɪʟᴇs ᴀɢᴀɪɴ, ᴛʜᴇɴ ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴅᴇʟᴇᴛᴇᴅ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ. ᴇʟsᴇ ᴄʟᴏsᴇ ᴛʜɪs ᴍᴇssᴀɢᴇ.</blockquote></b>",
                    reply_markup=InlineKeyboardMarkup(button),
                    **_link_preview_kwargs(True),
                )

            except Exception as e:
                try:
                    await temp.edit_text(f"<b>›› ᴘʀᴇᴠɪᴏᴜs ᴍᴇssᴀɢᴇ ᴡᴀs ᴅᴇʟᴇᴛᴇᴅ </b>")
                except Exception:
                    pass
                print(f"Error occured while editing the Delete message: {e}")
        else:
            await temp.edit_text(f"<b>ᴘʀᴇᴠɪᴏᴜs ᴍᴇssᴀɢᴇ ᴡᴀs ᴅᴇʟᴇᴛᴇᴅ </b>")

    except Exception as e:
        print(f"Error occured while editing the Delete message: {e}")
        try:
            await temp.edit_text(f"<b>ᴘʀᴇᴠɪᴏᴜs ᴍᴇssᴀɢᴇ ᴡᴀs ᴅᴇʟᴇᴛᴇᴅ</b>")
        except Exception:
            pass

    await safe_delete(msg)

#Function for deleteing files/Messages.....
async def delete_message(msg, delay_time):
    await asyncio.sleep(delay_time)
    await safe_delete(msg)

#===============================================================#

#Function for batch auto delete - sends one notification for all files
async def batch_auto_del_notification(bot_username, messages, delay_time, transfer_link, chat_id, client):
    """Send one notification for batch of files and delete all after timer"""
    # Drop any None entries from failed copies
    messages = [m for m in (messages or []) if m is not None]
    if not messages:
        return

    # Send single countdown notification (with flood retry)
    try:
        notification_msg = await retry_on_flood(
            lambda: client.send_message(
                chat_id=chat_id,
                text=DEL_MSG.format(username=bot_username, time=convert_time(delay_time)),
                **_link_preview_kwargs(True),
            ),
            max_retries=3,
            label="auto_del_notify",
        )
    except Exception as e:
        print(f"Error sending auto-delete notification: {e}")
        notification_msg = None

    await asyncio.sleep(delay_time)

    # Delete all file messages (skip None, ignore already-gone)
    for msg in messages:
        await safe_delete(msg)

    if notification_msg is None:
        return

    # Update notification with get files button
    try:
        if transfer_link:
            try:
                name = "• ɢᴇᴛ ғɪʟᴇs •"
                link = f"https://t.me/{bot_username}?start={transfer_link}"
                button = [[styled_button(text=f"{name}", style="primary", url=link), styled_button(text="ᴄʟᴏsᴇ •", style="danger", callback_data="close")]]

                await notification_msg.edit_text(
                    text=f"<b>ᴘʀᴇᴠɪᴏᴜs ᴍᴇssᴀɢᴇ ᴡᴀs ᴅᴇʟᴇᴛᴇᴅ<blockquote>ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ɢᴇᴛ ᴛʜᴇ ғɪʟᴇs ᴀɢᴀɪɴ, ᴛʜᴇɴ ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴅᴇʟᴇᴛᴇᴅ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ. ᴇʟsᴇ ᴄʟᴏsᴇ ᴛʜɪs ᴍᴇssᴀɢᴇ.</blockquote></b>",
                    reply_markup=InlineKeyboardMarkup(button),
                    **_link_preview_kwargs(True),
                )
            except Exception as e:
                try:
                    await notification_msg.edit_text(f"<b>›› ᴘʀᴇᴠɪᴏᴜs ᴍᴇssᴀɢᴇ ᴡᴀs ᴅᴇʟᴇᴛᴇᴅ</b>")
                except Exception:
                    pass
                print(f"Error editing notification message: {e}")
        else:
            await notification_msg.edit_text(f"<b>ᴘʀᴇᴠɪᴏᴜs ᴍᴇssᴀɢᴇ ᴡᴀs ᴅᴇʟᴇᴛᴇᴅ</b>")
    except Exception as e:
        print(f"Error updating notification message: {e}")
