from AloneX import database2 as database

collection = database['autodelete']


async def set_autodelete(chat_id: int, delay: int):
    try:
        filter = {'chat_id': chat_id}
        data = {
            "$set": {
                'chat_id': chat_id,
                'delay': delay,
                'enabled': True
            }
        }
        await collection.update_one(filter, data, upsert=True)
        return True
    except Exception as e:
        print(f"Error setting autodelete: {e}")
        return False


async def get_autodelete(chat_id: int):
    try:
        result = await collection.find_one({'chat_id': chat_id})
        if result and result.get('enabled'):
            return result.get('delay')
        return None
    except Exception as e:
        print(f"Error getting autodelete: {e}")
        return None


async def disable_autodelete(chat_id: int):
    try:
        filter = {'chat_id': chat_id}
        data = {"$set": {'enabled': False}}
        result = await collection.update_one(filter, data)
        return result.modified_count > 0
    except Exception as e:
        print(f"Error disabling autodelete: {e}")
        return False


async def remove_autodelete(chat_id: int):
    try:
        await collection.delete_one({'chat_id': chat_id})
        return True
    except Exception as e:
        print(f"Error removing autodelete: {e}")
        return False


async def get_all_autodelete_chats():
    try:
        chats = await collection.find({'enabled': True}).to_list(length=None)
        return {chat['chat_id']: chat['delay'] for chat in chats} if chats else {}
    except Exception as e:
        print(f"Error getting all autodelete chats: {e}")
        return {}
