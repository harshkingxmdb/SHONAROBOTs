from AloneX import database as db

# Collections
warn_collection = db.warns
filter_collection = db.warn_filters
limit_collection = db.warn_limits
CHAT_IDS = []

# Basic warn operations
async def add_warn(chat_id: int, user_id: int, reason: str):
    data = await warn_collection.find_one({"chat_id": chat_id, "user_id": user_id})
    if data:
        await warn_collection.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$push": {"reasons": reason}}
        )
    else:
        await warn_collection.insert_one({
            "chat_id": chat_id,
            "user_id": user_id,
            "reasons": [reason]
        })

async def get_warns(chat_id: int, user_id: int):
    data = await warn_collection.find_one({"chat_id": chat_id, "user_id": user_id})
    return data["reasons"] if data else []

async def reset_warns(chat_id: int, user_id: int):
    await warn_collection.delete_one({"chat_id": chat_id, "user_id": user_id})

async def get_all_warned_users(chat_id: int):
    return await warn_collection.find({"chat_id": chat_id}).to_list(length=None)

async def remove_last_warn(chat_id: int, user_id: int):
    data = await warn_collection.find_one({"chat_id": chat_id, "user_id": user_id})
    if data and data.get("reasons"):
        updated = data["reasons"][:-1]
        if updated:
            await warn_collection.update_one(
                {"chat_id": chat_id, "user_id": user_id},
                {"$set": {"reasons": updated}}
            )
        else:
            await reset_warns(chat_id, user_id)

# Auto-warn keyword filter system
async def add_warn_filter(chat_id: int, keyword: str, reply: str):
    await filter_collection.update_one(
        {"chat_id": chat_id, "keyword": keyword},
        {"$set": {"reply": reply}},
        upsert=True
    )

async def remove_warn_filter(chat_id: int, keyword: str):
    await filter_collection.delete_one({"chat_id": chat_id, "keyword": keyword})

async def get_warn_filters(chat_id: int):
    return await filter_collection.find({"chat_id": chat_id}).to_list(length=None)

async def match_warn_filter(chat_id: int, text: str):
    filters = await get_warn_filters(chat_id)
    for f in filters:
        if f["keyword"].lower() in text.lower():
            return f
    return None

# Warn limits and actions
async def set_warn_limit(chat_id: int, limit: int):
    await limit_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"limit": limit}},
        upsert=True
    )

async def get_warn_limit(chat_id: int) -> int:
    data = await limit_collection.find_one({"chat_id": chat_id})
    return data.get("limit", 3) if data else 3

async def set_strong_warn(chat_id: int, enabled: bool):
    await limit_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"strong": enabled}},
        upsert=True
    )

async def get_strong_warn(chat_id: int):
    data = await limit_collection.find_one({"chat_id": chat_id})
    return data.get("strong", False) if data else False

async def set_warn_action(chat_id: int, action: str):
    await limit_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"action": action}},
        upsert=True
    )

async def get_warn_action(chat_id: int):
    data = await limit_collection.find_one({"chat_id": chat_id})
    return data.get("action", "ban") if data else "ban"

# Statistics and counting functions
async def count_chats() -> int:
    """Count chats with warn system"""
    return len(await warn_collection.distinct("chat_id"))

async def count_warns() -> int:
    """Count total warns across all chats"""
    total = 0
    async for doc in warn_collection.find({}):
        total += len(doc.get("reasons", []))
    return total

async def count_warn_filters() -> int:
    """Count total warn filters"""
    return await filter_collection.count_documents({})

async def count_warn_filter_chats() -> int:
    """Count chats with warn filters"""
    return len(await filter_collection.distinct("chat_id"))

async def reset_chat_warns(chat_id: int):
    """Reset all warns, warn filters and limits for a chat"""
    await warn_collection.delete_many({"chat_id": chat_id})
    await filter_collection.delete_many({"chat_id": chat_id})
    await limit_collection.delete_one({"chat_id": chat_id})

async def initialize_chats():
    """Initialize warn chats"""
    try:
        chats = await warn_collection.distinct("chat_id")
        CHAT_IDS.extend(chats)
        print(f"Initialized {len(chats)} warn chats")
    except Exception as e:
        print(f"Error initializing warn chats: {e}")
