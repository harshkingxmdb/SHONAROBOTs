from AloneX import database 
from datetime import datetime, timezone


confess_collection = database["confessions"]
settings_collection = database["group_settings"]

# ------------------ Confession Functions ------------------ #
async def log_confession(from_id: int, to_id: int, message: str):
    await confess_collection.insert_one({
        "from_id": from_id,
        "to_id": to_id,
        "message": message,
        "timestamp": datetime.now(timezone.utc)
    })

async def get_confess_logs(from_id: int):
    return await confess_collection.find({"from_id": from_id}).to_list(length=100)

async def get_confess_logs_all():
    return await confess_collection.find({}).to_list(length=100)

# ------------------ Anti-Channel Settings ------------------ #
async def set_antichannel_setting(chat_id: int, state: bool):
    await settings_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"antichannel": state}},
        upsert=True
    )

async def get_antichannel_setting(chat_id: int) -> bool:
    doc = await settings_collection.find_one({"chat_id": chat_id})
    return doc.get("antichannel", False) if doc else False
