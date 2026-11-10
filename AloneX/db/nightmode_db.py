from AloneX import database2 as database

db = database['nightmode']
NIGHTMODE_CHATS = {}

async def add_nightmode(chat_id: int, close_hour: int = None, open_hour: int = None):
    data = await db.find_one({"chat_id": chat_id})
    update_data = {"nightmode": True}

    if close_hour is not None:
        update_data["close_hour"] = close_hour
    elif not data or "close_hour" not in data:
        update_data["close_hour"] = 0

    if open_hour is not None:
        update_data["open_hour"] = open_hour
    elif not data or "open_hour" not in data:
        update_data["open_hour"] = 6

    await db.update_one(
        {"chat_id": chat_id},
        {"$set": update_data},
        upsert=True
    )

    # Update cache
    full_data = await db.find_one({"chat_id": chat_id})
    if full_data:
        NIGHTMODE_CHATS[chat_id] = full_data

async def rm_nightmode(chat_id: int):
    await db.update_one({"chat_id": chat_id}, {"$set": {"nightmode": False}})
    if chat_id in NIGHTMODE_CHATS:
        NIGHTMODE_CHATS[chat_id]["nightmode"] = False

async def is_nightmode(chat_id: int) -> bool:
    if chat_id in NIGHTMODE_CHATS:
        return NIGHTMODE_CHATS[chat_id].get("nightmode", False)
    chat = await db.find_one({"chat_id": chat_id, "nightmode": True})
    return bool(chat)

async def get_nightmode_data(chat_id: int):
    if chat_id in NIGHTMODE_CHATS:
        return NIGHTMODE_CHATS[chat_id]
    return await db.find_one({"chat_id": chat_id})

async def get_all_nightmode_chats():
    # Return from cache if populated, otherwise from DB
    if NIGHTMODE_CHATS:
        return [data for data in NIGHTMODE_CHATS.values() if data.get("nightmode")]
    return await db.find({"nightmode": True}).to_list(length=2000)

async def initialize_chats():
    try:
        cursor = db.find({"nightmode": True})
        async for doc in cursor:
            chat_id = doc.get("chat_id")
            if chat_id:
                NIGHTMODE_CHATS[int(chat_id)] = doc
    except Exception:
        pass


async def reset_chat_nightmode(chat_id: int):
    await db.delete_one({"chat_id": chat_id})
    if chat_id in NIGHTMODE_CHATS:
        NIGHTMODE_CHATS.pop(chat_id)
