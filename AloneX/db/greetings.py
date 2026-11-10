from AloneX import database2 as database
import re

welcome_db = database['welcome']
goodbye_db = database["goodbye"]
CHAT_IDS = []

def clean_text_for_storage(text: str) -> str:
    if not text:
        return text
    return str(text).strip()

async def set_welcome_status(chat_id: int, status: bool):
    try:
        result = await welcome_db.update_one(
            {'chat_id': chat_id},
            {'$set': {'welcome_enabled': status}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        print(f"Error setting welcome status: {e}")
        return False

async def get_welcome_status(chat_id: int) -> bool:
    try:
        data = await welcome_db.find_one({'chat_id': chat_id})
        if data and 'welcome_enabled' in data:
            return data['welcome_enabled']
        return True
    except Exception as e:
        print(f"Error getting welcome status: {e}")
        return True

async def set_goodbye_status(chat_id: int, status: bool):
    try:
        result = await goodbye_db.update_one(
            {'chat_id': chat_id},
            {'$set': {'goodbye_enabled': status}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None or result.matched_count > 0
    except Exception as e:
        print(f"Error setting goodbye status: {e}")
        return False

async def get_goodbye_status(chat_id: int) -> bool:
    try:
        data = await goodbye_db.find_one({'chat_id': chat_id})
        if data and 'goodbye_enabled' in data:
            return data['goodbye_enabled']
        return False
    except Exception as e:
        print(f"Error getting goodbye status: {e}")
        return False

async def get_all_goodbye_chats() -> list:
    try:
        chats = await goodbye_db.find().to_list(length=None)
        return [chat['chat_id'] for chat in chats] if chats else []
    except Exception as e:
        print(f"Error getting goodbye chats: {e}")
        return []

async def count_goodbye_chats() -> int:
    try:
        return await goodbye_db.count_documents({})
    except Exception as e:
        print(f"Error counting goodbye chats: {e}")
        return 0

async def set_goodbye_time(chat_id: int, time: int = 300):
    try:
        existing_chat = await goodbye_db.find_one({'chat_id': chat_id})
        if not existing_chat:
            return False
        result = await goodbye_db.update_one({'chat_id': chat_id}, {"$set": {"time": time}})
        return result.modified_count > 0
    except Exception as e:
        print(f"Error setting goodbye time: {e}")
        return False

async def get_goodbye_time(chat_id: int):
    try:
        data = await goodbye_db.find_one({'chat_id': chat_id})
        return data.get('time') if data else None
    except Exception as e:
        print(f"Error getting goodbye time: {e}")
        return None

async def clear_goodbye(chat_id: int):
    try:
        if await goodbye_db.find_one({'chat_id': chat_id}):
            await goodbye_db.delete_one({'chat_id': chat_id})
            return True
        return False
    except Exception as e:
        print(f"Error clearing goodbye: {e}")
        return False

async def check_goodbye(chat_id: int):
    try:
        data = await goodbye_db.find_one({'chat_id': chat_id})
        if not data:
            return False
        return bool(data.get('text') or data.get('file_id'))
    except Exception as e:
        print(f"Error checking goodbye: {e}")
        return False

async def get_goodbye(chat_id: int):
    try:
        data = await goodbye_db.find_one({'chat_id': chat_id})
        if not data:
            return None
        if not (data.get('text') or data.get('file_id')):
            return None
        return data
    except Exception as e:
        print(f"Error getting goodbye: {e}")
        return None

async def set_goodbye(chat_id: int, file_id=None, file_type=None, text=None, keyboard=None, has_rules_button=False, has_rules_same=False, rules_target_row=-1):
    try:
        cleaned_text = clean_text_for_storage(text) if text else None
        update = {
            "$set": {
                "file_type": file_type,
                "file_id": file_id,
                "text": cleaned_text,
                "keyboard": keyboard,
                "has_rules_button": has_rules_button,
                "has_rules_same": has_rules_same,
                "rules_target_row": rules_target_row
            }
        }
        result = await goodbye_db.update_one({'chat_id': chat_id}, update, upsert=True)
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        print(f"Error setting goodbye: {e}")
        return False

async def check_welcome(chat_id: int):
    try:
        data = await welcome_db.find_one({'chat_id': chat_id})
        if not data:
            return False
        return bool(data.get('text') or data.get('file_id'))
    except Exception as e:
        print(f"Error checking welcome: {e}")
        return False

async def clear_welcome(chat_id: int):
    try:
        if await welcome_db.find_one({'chat_id': chat_id}):
            await welcome_db.delete_one({'chat_id': chat_id})
            return True
        return False
    except Exception as e:
        print(f"Error clearing welcome: {e}")
        return False

async def get_welcome(chat_id: int):
    try:
        data = await welcome_db.find_one({'chat_id': chat_id})
        if not data:
            return None
        if not (data.get('text') or data.get('file_id')):
            return None
        return data
    except Exception as e:
        print(f"Error getting welcome: {e}")
        return None

async def get_welcome_time(chat_id: int):
    try:
        data = await welcome_db.find_one({'chat_id': chat_id})
        return data.get('time') if data else None
    except Exception as e:
        print(f"Error getting welcome time: {e}")
        return None

async def count_welcome_chats() -> int:
    try:
        return await welcome_db.count_documents({})
    except Exception as e:
        print(f"Error counting welcome chats: {e}")
        return 0

async def get_all_welcome_chats() -> list:
    try:
        chats = await welcome_db.find().to_list(length=None)
        return [chat['chat_id'] for chat in chats] if chats else []
    except Exception as e:
        print(f"Error getting welcome chats: {e}")
        return []

async def set_welcome_time(chat_id: int, time: int = 300):
    try:
        existing_chat = await welcome_db.find_one({'chat_id': chat_id})
        if not existing_chat:
            return False
        result = await welcome_db.update_one({'chat_id': chat_id}, {"$set": {"time": time}})
        return result.modified_count > 0
    except Exception as e:
        print(f"Error setting welcome time: {e}")
        return False

async def set_welcome(chat_id: int, file_id=None, file_type=None, text=None, keyboard=None, has_rules_button=False, has_rules_same=False, rules_target_row=-1):
    try:
        cleaned_text = clean_text_for_storage(text) if text else None
        update = {
            "$set": {
                "file_type": file_type,
                "file_id": file_id,
                "text": cleaned_text,
                "keyboard": keyboard,
                "has_rules_button": has_rules_button,
                "has_rules_same": has_rules_same,
                "rules_target_row": rules_target_row
            }
        }
        result = await welcome_db.update_one({'chat_id': chat_id}, update, upsert=True)
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        print(f"Error setting welcome: {e}")
        return False

async def set_clean_welcome(chat_id: int, status: bool):
    try:
        await welcome_db.update_one(
            {'chat_id': chat_id},
            {'$set': {'clean_welcome': status}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error setting clean welcome: {e}")
        return False

async def get_clean_welcome(chat_id: int) -> bool:
    try:
        data = await welcome_db.find_one({'chat_id': chat_id})
        return data.get('clean_welcome', False) if data else False
    except Exception as e:
        print(f"Error getting clean welcome: {e}")
        return False

async def set_clean_goodbye(chat_id: int, status: bool):
    try:
        await goodbye_db.update_one(
            {'chat_id': chat_id},
            {'$set': {'clean_goodbye': status}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error setting clean goodbye: {e}")
        return False

async def get_clean_goodbye(chat_id: int) -> bool:
    try:
        data = await goodbye_db.find_one({'chat_id': chat_id})
        return data.get('clean_goodbye', False) if data else False
    except Exception as e:
        print(f"Error getting clean goodbye: {e}")
        return False

async def set_last_welcome(chat_id: int, message_id: int):
    try:
        await welcome_db.update_one(
            {'chat_id': chat_id},
            {'$set': {'last_welcome_id': message_id}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error setting last welcome: {e}")
        return False

async def get_last_welcome(chat_id: int):
    try:
        data = await welcome_db.find_one({'chat_id': chat_id})
        return data.get('last_welcome_id') if data else None
    except Exception as e:
        print(f"Error getting last welcome: {e}")
        return None

async def set_last_goodbye(chat_id: int, message_id: int):
    try:
        await goodbye_db.update_one(
            {'chat_id': chat_id},
            {'$set': {'last_goodbye_id': message_id}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error setting last goodbye: {e}")
        return False

async def get_last_goodbye(chat_id: int):
    try:
        data = await goodbye_db.find_one({'chat_id': chat_id})
        return data.get('last_goodbye_id') if data else None
    except Exception as e:
        print(f"Error getting last goodbye: {e}")
        return None

async def count_chats() -> int:
    try:
        welcome_chats = set(await get_all_welcome_chats())
        goodbye_chats = set(await get_all_goodbye_chats())
        return len(welcome_chats.union(goodbye_chats))
    except Exception as e:
        print(f"Error counting total chats: {e}")
        return 0

async def initialize_chats():
    try:
        welcome_chats = await get_all_welcome_chats()
        goodbye_chats = await get_all_goodbye_chats()
        all_chats = list(set(welcome_chats + goodbye_chats))
        CHAT_IDS.clear()
        CHAT_IDS.extend(all_chats)
        print(f"Initialized {len(all_chats)} greeting chats")
        return True
    except Exception as e:
        print(f"Error initializing greeting chats: {e}")
        return False

async def clean_existing_data():
    try:
        print("Cleaning existing welcome messages...")
        welcome_chats = await welcome_db.find().to_list(length=None)
        for chat in welcome_chats:
            if chat.get('text'):
                cleaned_text = clean_text_for_storage(chat['text'])
                await welcome_db.update_one(
                    {'chat_id': chat['chat_id']},
                    {'$set': {'text': cleaned_text}}
                )

        print("Cleaning existing goodbye messages...")
        goodbye_chats = await goodbye_db.find().to_list(length=None)
        for chat in goodbye_chats:
            if chat.get('text'):
                cleaned_text = clean_text_for_storage(chat['text'])
                await goodbye_db.update_one(
                    {'chat_id': chat['chat_id']},
                    {'$set': {'text': cleaned_text}}
                )

        print("Database cleanup completed!")
        return True
    except Exception as e:
        print(f"Error cleaning existing data: {e}")
        return False
