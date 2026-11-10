
from AloneX import database 

whispers = database["whispers"]
collection = database["whispers"]  # 👈 THIS must be defined

async def save_whisper(whisper_id: str, data: dict):
    await collection.insert_one({"_id": whisper_id, **data})

async def get_whisper(whisper_id: str):
    return await collection.find_one({"_id": whisper_id})

async def mark_read(whisper_id: str, reader_name: str):
    await collection.update_one(
        {"_id": whisper_id},
        {"$set": {"read": True, "reader": reader_name}}
    )
