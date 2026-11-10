from AloneX import database

db = database['log_channels']
LOG_CHANNELS = {}

async def set_log_channel(chat_id: int, log_channel_id: int):
    chat_id = int(chat_id)
    log_channel_id = int(log_channel_id)
    await db.update_one(
        {"chat_id": chat_id},
        {"$set": {"log_channel_id": log_channel_id}},
        upsert=True
    )
    LOG_CHANNELS[chat_id] = log_channel_id

async def unset_log_channel(chat_id: int):
    chat_id = int(chat_id)
    await db.delete_one({"chat_id": chat_id})
    LOG_CHANNELS.pop(chat_id, None)
    return True

async def stop_chat_logging(chat_id: int):
    return await unset_log_channel(chat_id)

async def get_log_channel(chat_id: int):
    chat_id = int(chat_id)
    if chat_id in LOG_CHANNELS:
        return LOG_CHANNELS[chat_id]
    res = await db.find_one({"chat_id": chat_id})
    if res:
        log_id = res.get("log_channel_id")
        if log_id:
            LOG_CHANNELS[chat_id] = int(log_id)
            return int(log_id)
    return None

async def disable_log_category(chat_id: int, category: str):
    chat_id = int(chat_id)
    await db.update_one(
        {"chat_id": chat_id},
        {"$addToSet": {"disabled_categories": category.lower()}},
        upsert=True
    )

async def enable_log_category(chat_id: int, category: str):
    chat_id = int(chat_id)
    await db.update_one(
        {"chat_id": chat_id},
        {"$pull": {"disabled_categories": category.lower()}},
        upsert=True
    )

async def is_category_enabled(chat_id: int, category: str):
    chat_id = int(chat_id)
    res = await db.find_one({"chat_id": chat_id})
    if not res: return True
    disabled = res.get("disabled_categories", [])
    return category.lower() not in disabled

async def num_logchannels():
    return await db.count_documents({})

async def initialize_chats():
    try:
        cursor = db.find({})
        async for doc in cursor:
            chat_id = doc.get("chat_id")
            log_id = doc.get("log_channel_id")
            if chat_id and log_id:
                LOG_CHANNELS[int(chat_id)] = int(log_id)
        print(f"✅ Initialized {len(LOG_CHANNELS)} log channels")
    except Exception as e:
        print(f"Error initializing log channels: {e}")
