

     
from AloneX import database2 as database
from typing import List, Dict, Optional

collection = database['translator']


CHAT_IDS = []

async def count_chats() -> int:
      count = await collection.count_documents({})
      return count

async def get_all_chats() -> List[int]:
    try:
        chats = await collection.find().to_list(length=1000)
        return [chat['chat_id'] for chat in chats]
    except Exception as e:
        print(f"Error in get_all_chats: {e}")
        return []
         
async def get_chat(chat_id: int) -> Optional[Dict]:
    chat_query = {'chat_id': chat_id}
    chat = await collection.find_one(chat_query)
    if chat:
        return chat

async def remove_chat(chat_id: int) -> bool:
    chat_query = {'chat_id': chat_id}
    chat = await collection.find_one(chat_query)
    if chat:
        await collection.delete_one(chat_query)
        return True
    return False

async def add_chat(chat_id: int, lang: str) -> bool:
    chat_query = {'chat_id': chat_id}
    await collection.update_one(chat_query, {'$set': {'lang': lang}}, upsert=True)
    return True

async def initialize_db_chats() -> None:
    chats = await get_all_chats()
    CHAT_IDS.extend(chats)
    
