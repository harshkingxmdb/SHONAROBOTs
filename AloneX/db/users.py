from AloneX import database2 as database
import config

collection = database['users']

USER_IDS = []


async def check_user_exists(user_id: int):
    user = await collection.find_one({'user_id': user_id})
    return True if user else False


async def get_all_premium_users():
    filter = {'is_premium': True}
    users = await collection.find(filter).to_list(length=None)
    return [user['user_id'] for user in users] if users else []


async def update_user_premium(user_id: int, option: bool) -> bool:
    user_filter = {'user_id': user_id}
    db_user = await collection.find_one(user_filter)
    data = {"$set": {"is_premium": option}}
    if db_user:
        result = await collection.update_one(user_filter, data)
        return result.modified_count > 0
    return False


async def check_user_premium(user_id: int) -> bool:
    db_user = await collection.find_one({'user_id': user_id})
    if db_user:
        return db_user.get("is_premium", False)
    return False


async def get_user_premium(user_id: int) -> dict:
    db_user = await collection.find_one({'user_id': user_id})
    if db_user:
        return {
            "user_id": db_user.get("user_id"),
            "is_premium": db_user.get("is_premium", False)
        }
    return False


async def add_user(obj, active=False):
    try:
        user_id = obj['id']
        filter = {'user_id': user_id}
        
        existing_user = await collection.find_one(filter)
        
        if existing_user:
            user_data = {
                "$set": {
                    'first_name': obj.get('first_name'),
                    'username': obj.get('username'),
                }
            }
        else:
            user_data = {
                "$set": {
                    'user_id': user_id,
                    'first_name': obj.get('first_name'),
                    'username': obj.get('username'),
                    'active': active,
                }
            }
        
        await collection.update_one(filter, user_data, upsert=True)
    except Exception as e:
        print(f"Error adding user: {e}")


async def activate_user(user_id: int):
    try:
        filter = {'user_id': user_id}
        user_data = {"$set": {'active': True}}
        result = await collection.update_one(filter, user_data)
        return result.modified_count > 0
    except Exception as e:
        print(f"Error activating user: {e}")
        return False


async def update_users_status(users_id: list, status=True):
    filter = {'user_id': {'$in': users_id}}
    update = {'$set': {'active': status}}
    result = await collection.update_many(filter, update)
    return result.modified_count > 0


async def remove_user(user_id):
    try:
        await collection.delete_one({'user_id': user_id})
    except Exception as e:
        print(f"Error removing user: {e}")


async def get_user_data(user_id):
    try:
        user = await collection.find_one({'user_id': user_id})
        if user:
            return {key: value for key, value in user.items() if not key.startswith('_')}
        return {}
    except Exception as e:
        print(f"Error getting user: {e}")
        return {}


async def get_users_by_first_name(first_name):
    try:
        users = await collection.find(
            {'first_name': {'$regex': first_name, '$options': 'i'}}
        ).to_list(None)
        return users
    except Exception as e:
        print(f'Error while searching for user_ids by first_name: {str(e)}')
        return []


async def get_users_by_username(username):
    try:
        users = await collection.find(
            {'username': {'$regex': username, '$options': 'i'}}
        ).to_list(None)
        return users
    except Exception as e:
        print(f'Error while searching for user_ids by username: {str(e)}')
        return []


async def get_user_id_by_username(username):
    try:
        user = await collection.find_one(
            {'username': {'$regex': username, '$options': 'i'}}
        )
        return user['user_id'] if user else None
    except Exception as e:
        print(f'Error while searching for user_id by username: {str(e)}')
        return None


async def update_users_status_to_active(users_id: list):
    result = await collection.update_many(
        {'user_id': {'$in': users_id}},
        {'$set': {'active': True}}
    )
    return result.modified_count > 0


async def update_users_status_to_inactive(users_id: list):
    result = await collection.update_many(
        {'user_id': {'$in': users_id}},
        {'$set': {'active': False}}
    )
    return result.modified_count > 0


async def get_all_active_users():
    users = await collection.find({'active': True}).to_list(length=None)
    return [user['user_id'] for user in users] if users else []


async def count_users() -> int:
    return await collection.count_documents({})


async def get_all_users():
    try:
        users = await collection.find().to_list(length=None)
        return [user['user_id'] for user in users]
    except Exception as e:
        print(f"Error getting all users: {e}")
        return []


async def initialize_db_users():
    users = await get_all_users()
    USER_IDS.clear()
    USER_IDS.extend(users)


async def initialize_db_premium_users():
    users = await get_all_premium_users()
    config.PREMIUM_USERS.clear()
    config.PREMIUM_USERS.extend(users)


async def get_user_active_status(user_id: int) -> bool:
    try:
        user = await collection.find_one({"user_id": user_id})
        if user:
            return user.get("active", False)
        return False
    except Exception as e:
        print(f"Error checking user active status: {e}")
        return False


async def is_first_dm_start(user_id: int) -> bool:
    try:
        user = await collection.find_one({"user_id": user_id})
        if user:
            current_status = user.get("active", False)
            return not current_status
        return False
    except Exception as e:
        print(f"Error checking first DM start: {e}")
        return False


async def get_user_join_source(user_id: int) -> str:
    try:
        user_exists = await check_user_exists(user_id)
        
        if not user_exists:
            return 'new'
        
        is_active = await get_user_active_status(user_id)
        if not is_active:
            return 'group_inactive'
        else:
            return 'already_active'
            
    except Exception as e:
        print(f"Error getting user join source: {e}")
        return 'unknown'
