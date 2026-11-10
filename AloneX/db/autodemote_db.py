from AloneX import database as db

COLL = db["autodemote_settings"]

async def get_autodemote_settings(chat_id: int):
    """Get autodemote settings for a chat"""
    data = await COLL.find_one({"chat_id": chat_id})
    if not data:
        return {
            "enabled": False,
            "limit": 3,
            "window": 10
        }
    return {
        "enabled": data.get("enabled", False),
        "limit": data.get("limit", 3),
        "window": data.get("window", 10)
    }

async def set_autodemote_status(chat_id: int, enabled: bool):
    """Set autodemote status (ON/OFF)"""
    await COLL.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": enabled}},
        upsert=True
    )

async def set_autodemote_limits(chat_id: int, limit: int, window: int):
    """Set ban limit and time window"""
    await COLL.update_one(
        {"chat_id": chat_id},
        {"$set": {"limit": limit, "window": window}},
        upsert=True
    )
