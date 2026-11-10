from AloneX import database as db

joinmute_collection = db.joinmute
JOINMUTE_CACHE = {} # chat_id: duration_seconds

async def get_joinmute_duration(chat_id: int) -> int:
    return JOINMUTE_CACHE.get(int(chat_id), 0)

async def set_joinmute_duration(chat_id: int, duration: int):
    chat_id = int(chat_id)
    if duration > 0:
        JOINMUTE_CACHE[chat_id] = duration
        await joinmute_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"duration": duration}},
            upsert=True
        )
    else:
        JOINMUTE_CACHE.pop(chat_id, None)
        await joinmute_collection.delete_one({"chat_id": chat_id})

async def initialize_chats():
    try:
        cursor = joinmute_collection.find({})
        async for doc in cursor:
            chat_id = doc.get("chat_id")
            duration = doc.get("duration")
            if chat_id:
                JOINMUTE_CACHE[int(chat_id)] = int(duration)
    except Exception:
        pass
