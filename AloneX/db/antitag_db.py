from AloneX import database as db

antitag_collection = db.antitag
CHAT_IDS = {}

async def get_antitag_limit(chat_id: int) -> int:
    chat_id = int(chat_id)
    return CHAT_IDS.get(chat_id, 0)

async def set_antitag_limit(chat_id: int, limit: int):
    chat_id = int(chat_id)
    if limit > 0:
        CHAT_IDS[chat_id] = limit
        await antitag_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"limit": limit}},
            upsert=True
        )
    else:
        CHAT_IDS.pop(chat_id, None)
        await antitag_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"limit": 0}},
            upsert=True
        )

async def initialize_chats():
    try:
        cursor = antitag_collection.find({"limit": {"$gt": 0}})
        async for doc in cursor:
            chat_id = doc.get("chat_id")
            limit = doc.get("limit")
            if chat_id and limit:
                CHAT_IDS[int(chat_id)] = int(limit)
    except Exception:
        pass
