from AloneX import database as db  # Motor client

COLL = db["antinsfw_settings"]  # MongoDB collection

# ---------------- Normal Users ---------------- #
async def get_antinsfw(chat_id: int) -> bool:
    """Return True if Anti-NSFW for normal users is ON"""
    data = await COLL.find_one({"chat_id": chat_id})
    if data and "antiporn" in data:
        return data["antiporn"]
    return False

async def set_antinsfw(chat_id: int, value: bool):
    """Set Anti-NSFW ON/OFF for normal users"""
    await COLL.update_one(
        {"chat_id": chat_id},
        {"$set": {"antiporn": value}},
        upsert=True
    )


# ---------------- Admin Mode ---------------- #
async def get_antinsfw_admin(chat_id: int) -> bool:
    """Return True if Anti-NSFW admin mode is ON (all messages deleted)"""
    data = await COLL.find_one({"chat_id": chat_id})
    if data and "antiporn_admin" in data:
        return data["antiporn_admin"]
    return False

async def set_antinsfw_admin(chat_id: int, value: bool):
    """Set Anti-NSFW ADMIN ON/OFF"""
    await COLL.update_one(
        {"chat_id": chat_id},
        {"$set": {"antiporn_admin": value}},
        upsert=True
    )


# ---------------- Statistics ---------------- #
async def count_antinsfw_enabled() -> int:
    """Return count of chats with Anti-NSFW enabled (either mode)"""
    count = await COLL.count_documents({
        "$or": [
            {"antiporn": True},
            {"antiporn_admin": True}
        ]
    })
    return count


async def reset_chat_antinsfw(chat_id: int):
    await COLL.delete_one({"chat_id": chat_id})
