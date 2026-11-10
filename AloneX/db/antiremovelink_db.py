from AloneX import database as db

antilink_collection = db.antiremovelink
CHAT_IDS = set()

async def is_antilink_enabled(chat_id: int) -> bool:
    return int(chat_id) in CHAT_IDS

async def set_antilink_status(chat_id: int, status: bool):
    chat_id = int(chat_id)
    if status:
        CHAT_IDS.add(chat_id)
        await antilink_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": True}},
            upsert=True
        )
    else:
        CHAT_IDS.discard(chat_id)
        await antilink_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": False}},
            upsert=True
        )

async def initialize_chats():
    try:
        cursor = antilink_collection.find({"enabled": True})
        async for doc in cursor:
            chat_id = doc.get("chat_id")
            if chat_id:
                CHAT_IDS.add(int(chat_id))
    except Exception:
        pass
