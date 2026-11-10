from datetime import datetime, timezone
from AloneX import database as db

filters_collection = db["filters"]
CHAT_IDS = []

async def add_filter(chat_id: int, trigger: str, reply_type: str, reply_data: str, added_by: int, buttons=None):
    # पहले check करो कि पुराना filter है तो delete करो
    await filters_collection.delete_one({"chat_id": chat_id, "trigger": trigger})
    
    data = {
        "chat_id": chat_id,
        "trigger": trigger,
        "reply_type": reply_type,
        "reply_data": reply_data,
        "added_by": added_by,
        "added_on": datetime.now(timezone.utc),
        "buttons": buttons
    }
    await filters_collection.insert_one(data)
    return True

async def add_filter_with_caption(chat_id: int, trigger: str, reply_type: str, reply_data: str, added_by: int, caption: str, buttons=None):
    """Add a filter with caption support for media types"""
    # पहले check करो कि पुराना filter है तो delete करो
    await filters_collection.delete_one({"chat_id": chat_id, "trigger": trigger})
    
    data = {
        "chat_id": chat_id,
        "trigger": trigger,
        "reply_type": reply_type,
        "reply_data": reply_data,
        "caption": caption,
        "added_by": added_by,
        "added_on": datetime.now(timezone.utc),
        "buttons": buttons
    }
    await filters_collection.insert_one(data)
    return True

async def get_filters(chat_id: int):
    return await filters_collection.find({"chat_id": chat_id}).to_list(length=100)

async def get_filter_by_trigger(chat_id: int, trigger: str):
    return await filters_collection.find_one({"chat_id": chat_id, "trigger": trigger})

async def remove_filter(chat_id: int, trigger: str):
    result = await filters_collection.delete_one({"chat_id": chat_id, "trigger": trigger})
    return result.deleted_count > 0

async def remove_all_filters(chat_id: int):
    result = await filters_collection.delete_many({"chat_id": chat_id})
    return result.deleted_count > 0

async def get_filter_count(chat_id: int):
    return await filters_collection.count_documents({"chat_id": chat_id})

# Fixed functions for proper counting
async def count_chats() -> int:
    """Count unique chats with filters"""
    try:
        unique_chats = await filters_collection.distinct("chat_id")
        return len(unique_chats)
    except Exception as e:
        print(f"Error counting filter chats: {e}")
        return 0

async def count_total_filters() -> int:
    """Count total number of filters across all chats"""
    try:
        total_filters = await filters_collection.count_documents({})
        return total_filters
    except Exception as e:
        print(f"Error counting total filters: {e}")
        return 0

async def initialize_chats():
    """Initialize filter chats"""
    try:
        chats = await filters_collection.distinct("chat_id")
        CHAT_IDS.clear()  # Clear first to avoid duplicates
        CHAT_IDS.extend(chats)
        print(f"Initialized {len(chats)} filter chats")
    except Exception as e:
        print(f"Error initializing filter chats: {e}")

# Additional utility functions
async def get_filter_stats():
    """Get comprehensive filter statistics"""
    try:
        total_filters = await count_total_filters()
        total_chats = await count_chats()
        return {
            "total_filters": total_filters,
            "total_chats": total_chats
        }
    except Exception as e:
        print(f"Error getting filter stats: {e}")
        return {"total_filters": 0, "total_chats": 0}

async def reset_chat_filters(chat_id: int):
    await filters_collection.delete_many({"chat_id": chat_id})
