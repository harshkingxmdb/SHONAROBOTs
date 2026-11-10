from AloneX import database as db

GHOST_DB = db.ghost_mode
CHAT_IDS = set()

async def is_ghost_enabled(chat_id: int) -> bool:
    """Check if ghost mode is enabled for a chat."""
    if chat_id in CHAT_IDS:
        return True
    data = await GHOST_DB.find_one({"chat_id": chat_id})
    if data is None:
        return True
    return bool(data.get("enabled", True))

async def set_ghost(chat_id: int, status: bool):
    """Enable or disable ghost mode for a chat."""
    if status:
        CHAT_IDS.add(chat_id)
    else:
        CHAT_IDS.discard(chat_id)

    await GHOST_DB.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": status}},
        upsert=True
    )

async def initialize_chats():
    try:
        cursor = GHOST_DB.find({"enabled": True})
        async for doc in cursor:
            chat_id = doc.get("chat_id")
            if chat_id:
                CHAT_IDS.add(int(chat_id))
    except Exception:
        pass
