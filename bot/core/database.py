import motor.motor_asyncio
import re, os
import pymongo
import os
import logging
from config import Var
from .reporter import rep

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def normalize_title(title: str) -> str:
    # Lowercase
    title = title.lower()
    # Remove common suffixes (season 2, part 1, etc.)
    title = re.sub(r'\b(season|part|chapter|s|p|vol|volume)\s*\d+', '', title)
    title = re.sub(r'\b(s\d+|p\d+)\b', '', title)
    # Remove non-alphanumeric characters
    title = re.sub(r'[^a-z0-9]', '', title)
    return title.strip()



class Database:
    def __init__(self, uri=Var.DB_URI, database_name=Var.DB_NAME):
        """Initialize MongoDB connection with a single URI and database name."""
        self.__client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.__db = self.__client[database_name]
        
        # Collections for user, admin, ban, channel, and force-sub management
        self.channel_data = self.__db['channels']
        self.admins_data = self.__db['admins']
        self.user_data = self.__db['users']
        self.banned_user_data = self.__db['banned_user']
        self.autho_user_data = self.__db['autho_user']
        self.del_timer_data = self.__db['del_timer']
        self.fsub_data = self.__db['fsub']
        self.rqst_fsub_data = self.__db['request_forcesub']
        self.rqst_fsub_channel_data = self.__db['request_forcesub_channel']
        self.anime_channels = self.__db['anime_channels']  # Collection for anime-to-channel mappings
        self.settings = self.__db['settings']  # Collection for settings (e.g., sticker_id)
        self.anime_posters = self.__db['anime_posters']
        # Anime collection (named using BOT_TOKEN)
        self.__animes = self.__db[f"animes_{Var.BOT_TOKEN.split(':')[0]}"]

    # USER DATA
    async def present_user(self, user_id: int):
        found = await self.user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_user(self, user_id: int):
        await self.user_data.insert_one({'_id': user_id})
        await rep.report(f"User added: {user_id}", "info", log=True)
        return

    async def full_userbase(self):
        user_docs = await self.user_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in user_docs]
        return user_ids

    async def del_user(self, user_id: int):
        await self.user_data.delete_one({'_id': user_id})
        await rep.report(f"User deleted: {user_id}", "info", log=True)
        return

    # ADMIN DATA
    async def admin_exist(self, admin_id: int):
        found = await self.admins_data.find_one({'_id': admin_id})
        return bool(found)

    async def add_admin(self, admin_id: int):
        if not await self.admin_exist(admin_id):
            await self.admins_data.insert_one({'_id': admin_id})
            await rep.report(f"Admin added: {admin_id}", "info", log=True)
            return

    async def del_admin(self, admin_id: int):
        if await self.admin_exist(admin_id):
            await self.admins_data.delete_one({'_id': admin_id})
            await rep.report(f"Admin deleted: {admin_id}", "info", log=True)
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
            await rep.report(f"Banned user added: {user_id}", "info", log=True)
            return

    async def del_ban_user(self, user_id: int):
        if await self.ban_user_exist(user_id):
            await self.banned_user_data.delete_one({'_id': user_id})
            await rep.report(f"Banned user deleted: {user_id}", "info", log=True)
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
        await rep.report(f"Auto delete timer set to: {value}", "info", log=True)

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
            await rep.report(f"Channel added: {channel_id}", "info", log=True)
            return

    async def rem_channel(self, channel_id: int):
        if await self.channel_exist(channel_id):
            await self.fsub_data.delete_one({'_id': channel_id})
            await rep.report(f"Channel removed: {channel_id}", "info", log=True)
            return

    async def show_channels(self):
        channel_docs = await self.fsub_data.find().to_list(length=None)
        channel_ids = [doc['_id'] for doc in channel_docs]
        return channel_ids

    async def get_channel_mode(self, channel_id: int):
        data = await self.fsub_data.find_one({'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    async def set_channel_mode(self, channel_id: int, mode: str):
        await self.fsub_data.update_one(
            {'_id': channel_id},
            {'$set': {'mode': mode}},
            upsert=True
        )
        await rep.report(f"Channel mode set: channel_id={channel_id}, mode={mode}", "info", log=True)

    # REQUEST FORCE-SUB MANAGEMENT
    async def req_user(self, channel_id: int, user_id: int):
        try:
            await self.rqst_fsub_channel_data.update_one(
                {'_id': int(channel_id)},
                {'$addToSet': {'user_ids': int(user_id)}},
                upsert=True
            )
            await rep.report(f"User {user_id} added to request list for channel {channel_id}", "info", log=True)
        except Exception as e:
            await rep.report(f"Failed to add user to request list: {e}", "error", log=True)

    async def del_req_user(self, channel_id: int, user_id: int):
        await self.rqst_fsub_channel_data.update_one(
            {'_id': channel_id}, 
            {'$pull': {'user_ids': user_id}}
        )
        await rep.report(f"User {user_id} removed from request list for channel {channel_id}", "info", log=True)

    async def req_user_exist(self, channel_id: int, user_id: int):
        try:
            found = await self.rqst_fsub_channel_data.find_one({
                '_id': int(channel_id),
                'user_ids': int(user_id)
            })
            return bool(found)
        except Exception as e:
            await rep.report(f"Failed to check request list: {e}", "error", log=True)
            return False  

    async def reqChannel_exist(self, channel_id: int):
        channel_ids = await self.show_channels()
        if channel_id in channel_ids:
            return True
        return False

    # ANIME DATA MANAGEMENT
    async def get_anime(self, ani_id: int) -> dict:
        """Get anime data by ID."""
        try:
            botset = await self.__animes.find_one({'_id': ani_id})
            if botset:
                return botset.get('episodes', {})
            await rep.report(f"No anime data found for ani_id={ani_id}", "info", log=True)
            return {}
        except Exception as e:
            await rep.report(f"Error in get_anime for ani_id={ani_id}: {e}", "error", log=True)
            return {}

    async def save_anime(self, ani_id: int, ep_no: str, qual: str, post_id: int = None):
        """Save anime episode data with quality and post ID."""
        try:
            quals = (await self.get_anime(ani_id)).get(ep_no, {q: False for q in Var.QUALS})
            quals[qual] = True
            update_data = {f"episodes.{ep_no}": quals}
            if post_id:
                update_data["msg_id"] = post_id
            await self.__animes.update_one(
                {'_id': ani_id},
                {'$set': update_data},
                upsert=True
            )
            await rep.report(f"Saved anime data: ani_id={ani_id}, ep_no={ep_no}, qual={qual}, post_id={post_id}", "info", log=True)
        except Exception as e:
            await rep.report(f"Error in save_anime for ani_id={ani_id}: {e}", "error", log=True)
            raise

# ── ANIME → CHANNEL + CUSTOM POSTER MAPPING ───────────────────────────────
    async def set_anime_channel(self, ani_id: int, channel_id: int, custom_poster: str = None):
        """
        Set channel + optional custom poster for anime
        """
        try:
            update_data = {'channel_id': channel_id}
            if custom_poster is not None:
                update_data['custom_poster'] = custom_poster
            await self.anime_channels.update_one(
                {'ani_id': ani_id},
                {'$set': update_data},
                upsert=True
            )
            await rep.report(f"Anime mapped: {ani_id} → {channel_id} | Poster: {bool(custom_poster)}", "info", log=True)
        except Exception as e:
            await rep.report(f"set_anime_channel error: {e}", "error", log=True)

    async def get_anime_channel(self, ani_id: int) -> int | None:
        try:
            doc = await self.anime_channels.find_one({'ani_id': ani_id})
            return doc['channel_id'] if doc else None
        except Exception as e:
            await rep.report(f"get_anime_channel error: {e}", "error", log=True)
            return None

    async def get_custom_poster(self, ani_id: int) -> str | None:
        """Get custom poster path for anime"""
        try:
            doc = await self.anime_channels.find_one({'ani_id': ani_id})
            return doc.get('custom_poster') if doc else None
        except Exception as e:
            await rep.report(f"get_custom_poster error: {e}", "error", log=True)
            return None

    async def get_all_anime_channels(self) -> list:
        try:
            docs = await self.anime_channels.find().to_list(length=None)
            return [
                {
                    "ani_id": d["ani_id"],
                    "channel_id": d["channel_id"],
                    "custom_poster": d.get("custom_poster")
                } for d in docs
            ]
        except Exception as e:
            await rep.report(f"get_all_anime_channels error: {e}", "error", log=True)
            return []

    # ── STICKER ───────────────────────────────────────────────────────────────
    async def set_sticker(self, sticker_id: str):
        try:
            await self.settings.update_one(
                {'key': 'sticker_id'},
                {'$set': {'value': sticker_id}},
                upsert=True
            )
            await rep.report(f"Sticker set: {sticker_id}", "info", log=True)
        except Exception as e:
            await rep.report(f"set_sticker error: {e}", "error", log=True)

    async def set_anime_poster(self, anime_name: str, poster_id: str):
        await self.anime_posters.update_one(
            {"_id": normalize_title(anime_name)},
            {"$set": {"original": anime_name, "poster": poster_id}},
            upsert=True
        )

    async def get_anime_poster(self, anime_name: str):
        doc = await self.anime_posters.find_one({"_id": normalize_title(anime_name)})
        return doc.get("poster") if doc else None

    async def delete_anime_poster(self, anime_name: str):
        await self.anime_posters.delete_one({"_id": normalize_title(anime_name)})

    async def list_all_anime_posters(self):
        """Returns a list of anime names that have a custom poster."""
        docs = await self.anime_posters.find().to_list(length=None)
        return [doc["original"] for doc in docs if "original" in doc]

    async def get_sticker(self) -> str | None:
        try:
            doc = await self.settings.find_one({'key': 'sticker_id'})
            return doc['value'] if doc else None
        except Exception as e:
            await rep.report(f"get_sticker error: {e}", "error", log=True)
            return None
            
    async def reboot(self):
        """Drop the anime collection (use with caution)."""
        try:
            await self.__animes.drop()
            await rep.report("Anime collection dropped", "info", log=True)
        except Exception as e:
            await rep.report(f"Error in reboot: {e}", "error", log=True)

# Initialize the database
db = Database(Var.DB_URI, Var.DB_NAME)
