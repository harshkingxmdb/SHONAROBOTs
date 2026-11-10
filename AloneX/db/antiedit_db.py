from AloneX import database as db

COLL = db["antiedit_settings"]
MSG_COLL = db["antiedit_messages"]

# Anti-Edit Settings
async def get_antiedit(chat_id: int) -> bool:
    """Return True if Anti-Edit is ON for the chat"""
    try:
        data = await COLL.find_one({"chat_id": chat_id})
        if data and "enabled" in data:
            return data["enabled"]
    except Exception as e:
        print(f"Error in get_antiedit: {e}")
    return False

async def set_antiedit(chat_id: int, value: bool):
    """Set Anti-Edit ON/OFF for the chat"""
    try:
        await COLL.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": value}},
            upsert=True
        )
    except Exception as e:
        print(f"Error in set_antiedit: {e}")

# Message Caching in DB
async def save_msg_content(chat_id: int, message_id: int, content: str):
    """Save message content to database"""
    try:
        await MSG_COLL.update_one(
            {"chat_id": chat_id, "message_id": message_id},
            {"$set": {"content": content}},
            upsert=True
        )
    except Exception as e:
        print(f"Error in save_msg_content: {e}")

async def get_msg_content(chat_id: int, message_id: int) -> str:
    """Retrieve original message content from database"""
    try:
        data = await MSG_COLL.find_one({"chat_id": chat_id, "message_id": message_id})
        return data["content"] if data else None
    except Exception as e:
        print(f"Error in get_msg_content: {e}")
        return None
