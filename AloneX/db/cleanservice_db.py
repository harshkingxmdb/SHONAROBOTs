from AloneX import database as db

CLEAN_DB = db.cleanservice


async def get_clean_settings(chat_id: int) -> set:
    """Return set of service types to clean for this chat."""
    data = await CLEAN_DB.find_one({"chat_id": chat_id})
    if not data:
        return set()
    return set(data.get("clean", []))


async def save_clean_settings(chat_id: int, types: set):
    """Save or remove clean settings for this chat."""
    if types:
        await CLEAN_DB.update_one(
            {"chat_id": chat_id}, {"$set": {"clean": list(types)}}, upsert=True
        )
    else:
        await CLEAN_DB.delete_one({"chat_id": chat_id})


async def reset_chat_cleanservice(chat_id: int):
    await CLEAN_DB.delete_one({"chat_id": chat_id})
