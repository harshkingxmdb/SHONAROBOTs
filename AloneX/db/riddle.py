from AloneX import database2 as database

db = database["riddle"]

CHAT_IDS = []

async def update_chat_riddle(chat_id: int, enable: bool):
    chat = {"chat_id": chat_id}

    if enable:
        await db.update_one(chat, {"$set": {"enabled": True}}, upsert=True)
    else:
        result = await db.delete_one(chat)
        return result.deleted_count > 0

async def update_chat_riddle_count(chat_id: int, count: int):
    filter_ = {"chat_id": chat_id}
    update_ = {"$set": {"count": count}}

    result = await db.update_one(filter_, update_, upsert=True)
    return result.modified_count > 0 or result.upserted_id is not None

async def get_chat_riddle_count(chat_id: int):
    result = await db.find_one({"chat_id": chat_id})
    return result.get("count") if result else None

async def get_all_chats():
    try:
        chats = await db.find({}, {"chat_id": 1, "_id": 0}).to_list(length=None)
        return [chat["chat_id"] for chat in chats] if chats else []
    except Exception as e:
        print(f"Error getting all chats: {e}")
        return []

async def initialize_db_chats():
    users = await get_all_chats()
    CHAT_IDS.clear()
    CHAT_IDS.extend(users)

async def count_chats():
    """Count the number of chats with riddle enabled"""
    try:
        count = await db.count_documents({"enabled": True})
        return count
    except Exception as e:
        print(f"Error counting riddle chats: {e}")
        return 0


async def reset_chat_riddle(chat_id: int):
    await db.delete_one({"chat_id": chat_id})
    if chat_id in CHAT_IDS:
        CHAT_IDS.remove(chat_id)
