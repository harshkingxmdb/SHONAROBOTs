from AloneX import database2 as database

collection = database["ignore"]

USER_IDS = []

async def add_user(user_id: int) -> bool:
    user = {"user_id": user_id}
    exist = await collection.find_one(user)
    if not exist:
        await collection.insert_one(user)
        return True
    return False

async def count_chats() -> int:
    count = await collection.count_documents({})
    return count

async def remove_user(user_id: int) -> bool:
    user = {"user_id": user_id}
    exist = await collection.find_one(user)
    if exist:
        await collection.delete_one(user)
        return True
    return False

async def get_all_users() -> list:
    users = await collection.find().to_list(length=1000)
    if users:
        return [user["user_id"] for user in users]
    return []

async def is_user_blocked(user_id: int) -> bool:
    return user_id in USER_IDS

async def initialize_db_users():
    users = await get_all_users()
    USER_IDS.clear()
    USER_IDS.extend(users)
    return True
