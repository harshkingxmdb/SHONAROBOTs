from AloneX import database2 as database

collection = database['chats']


async def check_chat_exists(chat_id: int) -> bool:
    """Check if a chat exists in the database."""
    try:
        chat = await collection.find_one({'chat_id': chat_id})
        return True if chat else False
    except Exception:
        return False


async def count_chats() -> int:
    """Return the total number of chats in the database."""
    try:
        count = await collection.count_documents({})
        return count
    except Exception:
        return 0


async def add_chat(chat_id, chat_username=None):
    """
    Adds a new chat to the database.
    :param chat_id: The unique ID of the chat.
    :param chat_username: Optional username of the chat (for channels/groups with a @username).
    """
    try:
        chat_id = int(chat_id)
        existing = await collection.find_one({'chat_id': chat_id})
        
        clean_username = chat_username.strip('@').strip() if chat_username else None
        
        if not existing:
            chat_data = {'chat_id': chat_id, 'active': True}
            if clean_username:
                chat_data['chat_username'] = clean_username
            await collection.insert_one(chat_data)
        elif clean_username and ('chat_username' not in existing or existing.get('chat_username') != clean_username):
            await collection.update_one(
                {'chat_id': chat_id},
                {'$set': {'chat_username': clean_username}}
            )
    except Exception as e:
        print(f"Error adding chat: {e}")


async def remove_chat(chat_id):
    """Remove a chat from the database."""
    try:
        chat_id = int(chat_id)
        await collection.delete_one({'chat_id': chat_id})
    except Exception as e:
        print(f"Error removing chat: {e}")


async def get_chat(chat_id):
    """Get a specific chat from the database."""
    try:
        chat_id = int(chat_id)
        chat = await collection.find_one({'chat_id': chat_id})
        return chat
    except Exception as e:
        print(f"Error getting chat: {e}")
        return None


async def get_all_chats():
    """Get a list of all active chat IDs."""
    try:
        chats = await collection.find({'active': {'$ne': False}}).to_list(length=10000)
        return [chat['chat_id'] for chat in chats]
    except Exception as e:
        print(f"Error getting all chats: {e}")
        return []


async def update_chats_status(chat_ids: list, status: bool):
    """Update the active status of multiple chats."""
    try:
        for chat_id in chat_ids:
            chat_id = int(chat_id)
            await collection.update_one(
                {'chat_id': chat_id},
                {'$set': {'active': status}}
            )
    except Exception as e:
        print(f"Error updating chat status: {e}")
