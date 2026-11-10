from AloneX import database2 as database

db = database['abuse_filter']

async def set_abuse_state(chat_id: int, state: bool):
    await db.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": state}},
        upsert=True
    )

async def is_abuse_enabled(chat_id: int) -> bool:
    chat = await db.find_one({"chat_id": chat_id})
    return chat.get("enabled", False) if chat else False
