from AloneX import database2 as database

db = database['media_delete']

# In-memory cache for media delete settings
CHAT_SETTINGS = {}

async def set_media_delete_state(chat_id: int, state: bool):
    chat_id = int(chat_id)
    await db.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": state}},
        upsert=True
    )
    if chat_id not in CHAT_SETTINGS:
        CHAT_SETTINGS[chat_id] = {"enabled": state, "delay": 60}
    else:
        CHAT_SETTINGS[chat_id]["enabled"] = state

async def set_media_delete_delay(chat_id: int, delay: int):
    chat_id = int(chat_id)
    await db.update_one(
        {"chat_id": chat_id},
        {"$set": {"delay": delay}},
        upsert=True
    )
    if chat_id not in CHAT_SETTINGS:
        CHAT_SETTINGS[chat_id] = {"enabled": False, "delay": delay}
    else:
        CHAT_SETTINGS[chat_id]["delay"] = delay

async def get_media_delete_settings(chat_id: int):
    chat_id = int(chat_id)
    if chat_id in CHAT_SETTINGS:
        return CHAT_SETTINGS[chat_id]

    result = await db.find_one({"chat_id": chat_id})
    if result:
        settings = {
            "enabled": result.get("enabled", False),
            "delay": result.get("delay", 60) # Default 1 min
        }
        CHAT_SETTINGS[chat_id] = settings
        return settings

    return {"enabled": False, "delay": 60}

async def delete_all_media_delete(chat_id: int):
    chat_id = int(chat_id)
    await db.delete_one({"chat_id": chat_id})
    if chat_id in CHAT_SETTINGS:
        CHAT_SETTINGS.pop(chat_id)

async def initialize_chats():
    try:
        cursor = db.find({})
        async for doc in cursor:
            chat_id = doc.get("chat_id")
            if chat_id:
                CHAT_SETTINGS[int(chat_id)] = {
                    "enabled": doc.get("enabled", False),
                    "delay": doc.get("delay", 60)
                }
    except Exception:
        pass
