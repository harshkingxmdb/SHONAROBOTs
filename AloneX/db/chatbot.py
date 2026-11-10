from AloneX import database2 as database

collection = database['chatbot']

CHAT_IDS = []

async def count_chats() -> int:
    return await collection.count_documents({})

async def add_chat(chat_id):
    try:
        chat_id = int(chat_id)
        if not await collection.find_one({'chat_id': chat_id}):
            await collection.insert_one({'chat_id': chat_id})
        if chat_id not in CHAT_IDS:
            CHAT_IDS.append(chat_id)
    except Exception as e:
        print(f"Error adding chatbot chat: {e}")

async def remove_chat(chat_id):
    try:
        chat_id = int(chat_id)
        await collection.delete_one({'chat_id': chat_id})
        if chat_id in CHAT_IDS:
            CHAT_IDS.remove(chat_id)
    except Exception as e:
        print(f"Error removing chatbot chat: {e}")

async def get_all_chats():
    try:
        chats = await collection.find().to_list(length=None)
        return [chat['chat_id'] for chat in chats]
    except Exception as e:
        print(f"Error getting all chatbot chats: {e}")
        return []

async def initialize_db_chats():
    chats = await get_all_chats()
    CHAT_IDS.clear()
    CHAT_IDS.extend(chats)


async def reset_chat_chatbot(chat_id: int):
    await collection.delete_one({"chat_id": chat_id})
    if chat_id in CHAT_IDS:
        CHAT_IDS.remove(chat_id)
