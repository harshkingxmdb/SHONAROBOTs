from AloneX import database as DB

admin_cache = DB["admin_cache"]

async def get_last_admins(chat_id):
    data = await admin_cache.find_one({"chat_id": chat_id})
    if not data:
        return []
    return data.get("admin_ids", [])


async def save_admins(chat_id, admin_ids):
    await admin_cache.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "admin_ids": admin_ids}},
        upsert=True
    )
