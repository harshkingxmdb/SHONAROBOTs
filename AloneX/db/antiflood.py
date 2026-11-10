from AloneX import database as db
from cachetools import TTLCache
import asyncio
import time

flooddb = db.flood

_flood_configs: dict[int, dict] = {}
_chat_ids_set: set[int] = set()
_last_refresh = 0
_refresh_lock = asyncio.Lock()
REFRESH_INTERVAL = 300

async def initialize_chats():
    global _last_refresh
    try:
        cursor = flooddb.find({})
        async for doc in cursor:
            chat_id = doc["chat_id"]
            _chat_ids_set.add(chat_id)
            _flood_configs[chat_id] = {
                "limit": doc.get("limit", 0),
                "timer": doc.get("timer", {"count": 0, "seconds": 0}),
                "action": doc.get("action", {"type": "kick", "duration": None}),
                "clear": doc.get("clear", False),
            }
        _last_refresh = time.time()
        print(f"✅ Initialized {len(_chat_ids_set)} flood chats")
    except Exception as e:
        print(f"Error initializing flood chats: {e}")

async def _background_refresh():
    async with _refresh_lock:
        if time.time() - _last_refresh < REFRESH_INTERVAL:
            return
        try:
            await initialize_chats()
        except Exception as e:
            print(f"[Flood Refresh Error]: {e}")

async def get_flood_config(chat_id: int) -> dict:
    current_time = time.time()
    if current_time - _last_refresh > REFRESH_INTERVAL:
        if not _refresh_lock.locked():
            asyncio.create_task(_background_refresh())
    
    if chat_id in _flood_configs:
        return _flood_configs[chat_id].copy()
    
    return {
        "limit": 0,
        "timer": {"count": 0, "seconds": 0},
        "action": {"type": "kick", "duration": None},
        "clear": False,
    }

async def set_flood_limit(chat_id: int, limit: int):
    await flooddb.update_one(
        {"chat_id": chat_id},
        {"$set": {"limit": limit}},
        upsert=True
    )
    if chat_id not in _flood_configs:
        _flood_configs[chat_id] = {
            "limit": 0,
            "timer": {"count": 0, "seconds": 0},
            "action": {"type": "kick", "duration": None},
            "clear": False,
        }
    _flood_configs[chat_id]["limit"] = limit
    _chat_ids_set.add(chat_id)

async def set_flood_timer(chat_id: int, count: int, seconds: int):
    await flooddb.update_one(
        {"chat_id": chat_id},
        {"$set": {"timer": {"count": count, "seconds": seconds}}},
        upsert=True
    )
    if chat_id not in _flood_configs:
        _flood_configs[chat_id] = {
            "limit": 0,
            "timer": {"count": 0, "seconds": 0},
            "action": {"type": "kick", "duration": None},
            "clear": False,
        }
    _flood_configs[chat_id]["timer"] = {"count": count, "seconds": seconds}
    _chat_ids_set.add(chat_id)

async def disable_flood_timer(chat_id: int):
    await flooddb.update_one(
        {"chat_id": chat_id},
        {"$set": {"timer": {"count": 0, "seconds": 0}}},
        upsert=True
    )
    if chat_id in _flood_configs:
        _flood_configs[chat_id]["timer"] = {"count": 0, "seconds": 0}

async def set_flood_action(chat_id: int, action_type: str, duration: str = None):
    await flooddb.update_one(
        {"chat_id": chat_id},
        {"$set": {"action": {"type": action_type, "duration": duration}}},
        upsert=True
    )
    if chat_id not in _flood_configs:
        _flood_configs[chat_id] = {
            "limit": 0,
            "timer": {"count": 0, "seconds": 0},
            "action": {"type": "kick", "duration": None},
            "clear": False,
        }
    _flood_configs[chat_id]["action"] = {"type": action_type, "duration": duration}
    _chat_ids_set.add(chat_id)

async def set_flood_clear(chat_id: int, clear: bool):
    await flooddb.update_one(
        {"chat_id": chat_id},
        {"$set": {"clear": clear}},
        upsert=True
    )
    if chat_id not in _flood_configs:
        _flood_configs[chat_id] = {
            "limit": 0,
            "timer": {"count": 0, "seconds": 0},
            "action": {"type": "kick", "duration": None},
            "clear": False,
        }
    _flood_configs[chat_id]["clear"] = clear
    _chat_ids_set.add(chat_id)

async def count_chats() -> int:
    current_time = time.time()
    if current_time - _last_refresh > REFRESH_INTERVAL:
        if not _refresh_lock.locked():
            asyncio.create_task(_background_refresh())
    return len(_chat_ids_set)

async def reset_chat(chat_id: int):
    await flooddb.delete_one({"chat_id": chat_id})
    if chat_id in _flood_configs:
        _flood_configs.pop(chat_id)
    if chat_id in _chat_ids_set:
        _chat_ids_set.remove(chat_id)
