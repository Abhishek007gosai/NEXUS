#Codeflix_Botz
#rohit_1888 on Tg

import motor.motor_asyncio
import time
import pymongo
import os
import logging
from datetime import datetime, timedelta
from config import DB_URI, DB_NAME
from bot import Bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _normalize_uris(uri) -> list:
    """Accept a string or list of MongoDB URIs and return a clean list."""
    if isinstance(uri, (list, tuple)):
        return [u.strip() for u in uri if u and str(u).strip()]
    if isinstance(uri, str) and uri.strip():
        return [u for u in uri.split() if u.strip()]
    return []


def _pick_working_uri(uris: list) -> str:
    """Try each URI with a short sync ping; return the first that works."""
    if not uris:
        raise RuntimeError(
            "No MongoDB URI configured. Set DB_URI (or DATABASE_URL) env var. "
            "For multiple: DB_URI=\"mongodb://uri1 mongodb://uri2\""
        )
    last_err = None
    for u in uris:
        try:
            c = pymongo.MongoClient(u, serverSelectionTimeoutMS=5000)
            c.admin.command("ping")
            c.close()
            logger.info(f"MongoDB connected: {u[:40]}...")
            return u
        except Exception as e:
            last_err = e
            logger.warning(f"MongoDB URI failed ({u[:40]}...): {e}")
            continue
    # Fallback to first so motor still constructs (will error on use)
    logger.error(f"All MongoDB URIs failed. Using first. Last error: {last_err}")
    return uris[0]


_uris = _normalize_uris(DB_URI)
_used_uri = _pick_working_uri(_uris)

dbclient = pymongo.MongoClient(_used_uri, serverSelectionTimeoutMS=8000)
database = dbclient[DB_NAME]


class Rohit:

    def __init__(self, uri, DB_NAME):
        uris = _normalize_uris(uri)
        used = _pick_working_uri(uris) if uris else _used_uri
        self.dbclient = motor.motor_asyncio.AsyncIOMotorClient(used, serverSelectionTimeoutMS=8000)
        self.database = self.dbclient[DB_NAME]
        self.uri = used

        self.channel_data = self.database['channels']
        self.admins_data = self.database['admins']
        self.user_data = self.database['users']
        self.banned_user_data = self.database['banned_user']
        self.autho_user_data = self.database['autho_user']
        self.del_timer_data = self.database['del_timer']
        self.fsub_data = self.database['fsub']
        self.rqst_fsub_data = self.database['request_forcesub']
        self.rqst_fsub_Channel_data = self.database['request_forcesub_channel']
        self.db_channels_col = self.database['db_channels']  # multiple file-store channels

# USER DATA
    async def present_user(self, user_id: int):
        found = await self.user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_user(self, user_id: int):
        await self.user_data.insert_one({'_id': user_id})
        return

    async def full_userbase(self):
        user_docs = await self.user_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in user_docs]
        return user_ids

    async def del_user(self, user_id: int):
        await self.user_data.delete_one({'_id': user_id})
        return


    # ADMIN DATA
    async def admin_exist(self, admin_id: int):
        found = await self.admins_data.find_one({'_id': admin_id})
        return bool(found)

    async def add_admin(self, admin_id: int):
        if not await self.admin_exist(admin_id):
            await self.admins_data.insert_one({'_id': admin_id})
            return

    async def del_admin(self, admin_id: int):
        if await self.admin_exist(admin_id):
            await self.admins_data.delete_one({'_id': admin_id})
            return

    async def get_all_admins(self):
        users_docs = await self.admins_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids


    # BAN USER DATA
    async def ban_user_exist(self, user_id: int):
        found = await self.banned_user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_ban_user(self, user_id: int):
        if not await self.ban_user_exist(user_id):
            await self.banned_user_data.insert_one({'_id': user_id})
            return

    async def del_ban_user(self, user_id: int):
        if await self.ban_user_exist(user_id):
            await self.banned_user_data.delete_one({'_id': user_id})
            return

    async def get_ban_users(self):
        users_docs = await self.banned_user_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids



    # AUTO DELETE TIMER SETTINGS
    async def set_del_timer(self, value: int):        
        existing = await self.del_timer_data.find_one({})
        if existing:
            await self.del_timer_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.del_timer_data.insert_one({'value': value})

    async def get_del_timer(self):
        data = await self.del_timer_data.find_one({})
        if data:
            return data.get('value', 600)
        return 0


    # CHANNEL MANAGEMENT
    async def channel_exist(self, channel_id: int):
        found = await self.fsub_data.find_one({'_id': channel_id})
        return bool(found)

    async def add_channel(self, channel_id: int):
        if not await self.channel_exist(channel_id):
            await self.fsub_data.insert_one({'_id': channel_id})
            return

    async def rem_channel(self, channel_id: int):
        if await self.channel_exist(channel_id):
            await self.fsub_data.delete_one({'_id': channel_id})
            return

    async def show_channels(self):
        channel_docs = await self.fsub_data.find().to_list(length=None)
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids

    
# Get current mode of a channel
    async def get_channel_mode(self, channel_id: int):
        data = await self.fsub_data.find_one({'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    # Set mode of a channel
    async def set_channel_mode(self, channel_id: int, mode: str):
        await self.fsub_data.update_one(
            {'_id': channel_id},
            {'$set': {'mode': mode}},
            upsert=True
        )

    # REQUEST FORCE-SUB MANAGEMENT

    # Add the user to the set of users for a   specific channel
    async def req_user(self, channel_id: int, user_id: int):
        try:
            await self.rqst_fsub_Channel_data.update_one(
                {'_id': int(channel_id)},
                {'$addToSet': {'user_ids': int(user_id)}},
                upsert=True
            )
        except Exception as e:
            print(f"[DB ERROR] Failed to add user to request list: {e}")


    # Method 2: Remove a user from the channel set
    async def del_req_user(self, channel_id: int, user_id: int):
        # Remove the user from the set of users for the channel
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id}, 
            {'$pull': {'user_ids': user_id}}
        )

    # Check if the user exists in the set of the channel's users
    async def req_user_exist(self, channel_id: int, user_id: int):
        try:
            found = await self.rqst_fsub_Channel_data.find_one({
                '_id': int(channel_id),
                'user_ids': int(user_id)
            })
            return bool(found)
        except Exception as e:
            print(f"[DB ERROR] Failed to check request list: {e}")
            return False  


    # Method to check if a channel exists using show_channels
    async def reqChannel_exist(self, channel_id: int):
    # Get the list of all channel IDs from the database
        channel_ids = await self.show_channels()
        #print(f"All channel IDs in the database: {channel_ids}")

    # Check if the given channel_id is in the list of channel IDs
        if channel_id in channel_ids:
            #print(f"Channel {channel_id} found in the database.")
            return True
        else:
            #print(f"Channel {channel_id} NOT found in the database.")
            return False


    # Alias used by some plugins
    async def del_channel(self, channel_id: int):
        return await self.rem_channel(channel_id)

    # ===================== MULTIPLE DB CHANNELS =====================
    async def get_db_channels(self) -> dict:
        """Return {channel_id_str: {is_primary, is_active, title}}"""
        data = await self.db_channels_col.find_one({"_id": "db_channels"})
        return data.get("channels", {}) if data else {}

    async def set_db_channels(self, channels: dict):
        await self.db_channels_col.update_one(
            {"_id": "db_channels"},
            {"$set": {"channels": channels}},
            upsert=True,
        )

    async def add_db_channel(self, channel_id: int, title: str = "", is_primary: bool = False):
        channels = await self.get_db_channels()
        if is_primary:
            for v in channels.values():
                v["is_primary"] = False
        channels[str(channel_id)] = {
            "is_primary": is_primary or (len(channels) == 0),
            "is_active": True,
            "title": title or str(channel_id),
        }
        # Ensure at least one primary
        if not any(v.get("is_primary") for v in channels.values()):
            channels[str(channel_id)]["is_primary"] = True
        await self.set_db_channels(channels)

    async def remove_db_channel(self, channel_id: int):
        channels = await self.get_db_channels()
        was_primary = channels.get(str(channel_id), {}).get("is_primary", False)
        channels.pop(str(channel_id), None)
        if was_primary and channels:
            # promote first remaining
            first = next(iter(channels))
            channels[first]["is_primary"] = True
        await self.set_db_channels(channels)

    async def set_primary_db_channel(self, channel_id: int) -> bool:
        channels = await self.get_db_channels()
        if str(channel_id) not in channels:
            return False
        for cid, data in channels.items():
            data["is_primary"] = (cid == str(channel_id))
        await self.set_db_channels(channels)
        return True

    async def get_primary_db_channel(self):
        channels = await self.get_db_channels()
        for cid, data in channels.items():
            if data.get("is_primary"):
                return int(cid)
        if channels:
            return int(next(iter(channels)))
        return None

    async def list_db_channel_ids(self) -> list:
        channels = await self.get_db_channels()
        return [int(cid) for cid, d in channels.items() if d.get("is_active", True)]


db = Rohit(DB_URI, DB_NAME)
