from datetime import datetime
from AloneX import database as db

COLL = db["antiraid"]
CHAT_IDS = []  # Add this

async def enable_antiraid(chat_id: int, until: datetime):
    await COLL.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled_until": until}},
        upsert=True
    )

async def disable_antiraid(chat_id: int):
    await COLL.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled_until": None}},
        upsert=True
    )

async def set_raid_time(chat_id: int, seconds: int):
    await COLL.update_one(
        {"chat_id": chat_id},
        {"$set": {"raid_time": seconds}},
        upsert=True
    )

async def set_ban_time(chat_id: int, seconds: int):
    await COLL.update_one(
        {"chat_id": chat_id},
        {"$set": {"ban_time": seconds}},
        upsert=True
    )

async def set_auto_trigger(chat_id: int, threshold: int):
    await COLL.update_one(
        {"chat_id": chat_id},
        {"$set": {"auto_trigger": threshold}},
        upsert=True
    )

async def get_antiraid_config(chat_id: int) -> dict:
    config = await COLL.find_one({"chat_id": chat_id})
    if not config:
        return {
            "enabled_until": None,
            "raid_time": 21600,   # default 6 hours
            "ban_time": 3600,     # default 1 hour
            "auto_trigger": 0
        }
    return config

# Missing functions - Add these to antiraid.py
async def count_chats() -> int:
    """Count chats with antiraid"""
    return len(await COLL.distinct("chat_id"))

async def initialize_chats():
    """Initialize antiraid chats"""
    try:
        chats = await COLL.distinct("chat_id")
        CHAT_IDS.extend(chats)
        print(f"Initialized {len(chats)} antiraid chats")
    except Exception as e:
        print(f"Error initializing antiraid chats: {e}")


async def reset_chat_antiraid(chat_id: int):
    await COLL.delete_one({"chat_id": chat_id})
