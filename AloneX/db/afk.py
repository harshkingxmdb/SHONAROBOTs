
from AloneX import database2 as database


AFK_USERS = []
collection = database['afk']

async def add_user_afk(user_id, first_name, reason, datetime):
    try:
        user_id = int(user_id)  # Ensure user_id is an integer
        user = await collection.find_one({'user_id': user_id})
        if user:
            update = {
                '$set': {
                    'datetime': datetime,
                    'first_name': first_name,
                    'reason': reason
                }
            }
            await collection.update_one({'user_id': user_id}, update)
        else:
            user = {
                'user_id': user_id,
                'first_name': first_name,
                'datetime': datetime,
                'reason': reason
            }
            await collection.insert_one(user)
        if user_id not in AFK_USERS:
            AFK_USERS.append(user_id)
    except Exception as e:
        print(f'Error while adding AFK user: {str(e)}')


async def get_user_afk(user_id):
    try:
        user = await collection.find_one({'user_id': int(user_id)})
        if user:
            return {
                'user_id': user['user_id'],
                'first_name': user['first_name'],
                'datetime': user['datetime'],
                'reason': user['reason']
            }
        else:
            return {}
    except Exception as e:
        print(f'Error while getting AFK user data: {str(e)}')


async def remove_user_afk(user_id):
    try:
        user_id = int(user_id)  # Ensure user_id is an integer
        result = await collection.delete_one({'user_id': user_id})
        if result.deleted_count > 0 and user_id in AFK_USERS:
            AFK_USERS.remove(user_id)
    except Exception as e:
        print(f'Error while removing AFK user: {str(e)}')


async def count_chats() -> int:
      count = await collection.count_documents({})
      return count


async def get_all_afk_users():
    try:
        users = await collection.find().to_list()
        return [user['user_id'] for user in users]
    except Exception as e:
        print(f'Error while getting all AFK users: {str(e)}')
        return []


async def initialize_afk_users():
      AFK_USERS.extend(await get_all_afk_users())
        
    

    
