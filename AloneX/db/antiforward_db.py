from AloneX import database as db

antiforward_collection = db.antiforward
ANTIFORWARD_CACHE = set()

async def is_antiforward_enabled(chat_id: int) -> bool:
    return int(chat_id) in ANTIFORWARD_CACHE

async def set_antiforward_status(chat_id: int, status: bool):
    chat_id = int(chat_id)
    if status:
        ANTIFORWARD_CACHE.add(chat_id)
        await antiforward_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": True}},
            upsert=True
        )
    else:
        ANTIFORWARD_CACHE.discard(chat_id)
        await antiforward_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": False}},
            upsert=True
        )

async def initialize_chats():
    try:
        cursor = antiforward_collection.find({"enabled": True})
        async for doc in cursor:
            chat_id = doc.get("chat_id")
            if chat_id:
                ANTIFORWARD_CACHE.add(int(chat_id))
    except Exception:
        pass
