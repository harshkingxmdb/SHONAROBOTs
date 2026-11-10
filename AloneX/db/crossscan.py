from AloneX import database2 as db
from datetime import datetime, timezone

collection = db["crossscan_config"]

# Toggle
async def is_crossscan_enabled(chat_id: int) -> bool:
    return await collection.find_one({"chat_id": chat_id}) is not None

async def enable_crossscan(chat_id: int):
    await collection.update_one({"chat_id": chat_id}, {"$set": {"chat_id": chat_id}}, upsert=True)

async def disable_crossscan(chat_id: int):
    await collection.delete_one({"chat_id": chat_id})

# Flag
async def flag_user(user_id: int, reason: str, flagged_by: int):
    await collection.update_one(
        {"flag_user_id": user_id},
        {"$set": {
            "flag_user_id": user_id,
            "reason": reason,
            "flagged_by": flagged_by,
            "time": datetime.now(timezone.utc)
        }},
        upsert=True
    )

async def unflag_user(user_id: int):
    await collection.delete_one({"flag_user_id": user_id})

async def get_flag_info(user_id: int):
    return await collection.find_one({"flag_user_id": user_id})

async def get_all_flagged_users():
    return collection.find({"flag_user_id": {"$exists": True}})
