from AloneX import database as db_connect

blchats_db = db_connect["blacklist_chats"]

async def add_blchat(chat_id: int):
    """Add chat to blacklist"""
    try:
        await blchats_db.insert_one({"chat_id": chat_id})
        return True
    except Exception as e:
        print(f"Error adding blacklist chat: {e}")
        return False

async def rm_blchat(chat_id: int):
    """Remove chat from blacklist"""
    try:
        result = await blchats_db.delete_one({"chat_id": chat_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error removing blacklist chat: {e}")
        return False

async def is_blchat(chat_id: int):
    """Check if chat is blacklisted"""
    try:
        chat = await blchats_db.find_one({"chat_id": chat_id})
        return bool(chat)
    except Exception as e:
        print(f"Error checking blacklist chat: {e}")
        return False

async def get_all_blchats():
    """Get all blacklisted chats"""
    try:
        chats = []
        async for chat in blchats_db.find({}):
            chats.append(chat["chat_id"])
        return chats
    except Exception as e:
        print(f"Error getting all blacklist chats: {e}")
        return []
