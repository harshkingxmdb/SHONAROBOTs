from AloneX import database2 as database

db = database['fsub']


CHAT_IDS = []


async def update_fsub(chat_id: int, force_chat_id: int, switch: bool = True) -> bool:
    chat_filter = {'chat_id': chat_id}
    chat_update = {
        "$set": {
            "force_chat_id": force_chat_id,
            "switch": switch
        }
    }
    result = await db.update_one(chat_filter, chat_update, upsert=True)
    return result.modified_count > 0 or result.upserted_id is not None
       

async def get_chat_fsub(chat_id: int) -> [bool, int]:
       chat_filter = {'chat_id': chat_id}
       chat = await db.find_one(chat_filter)
       if chat:
            return chat
       return False
  
async def remove_chat(chat_id: int) -> bool:
    result = await db.delete_one({'chat_id': chat_id})
    return result.deleted_count > 0


async def count_chats() -> int:
      count = await db.count_documents({})
      return count
  
async def get_all_chats() -> list:
    chats = await db.find().to_list(length=10000)
    if chats:
        return [ chat["chat_id"] for chat in chats ]
    else:
        return []


async def initialize_chats():
      chats = await get_all_chats()
      CHAT_IDS.extend(chats)



  
