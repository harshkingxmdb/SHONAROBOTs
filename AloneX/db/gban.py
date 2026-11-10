from AloneX import database

gban_collection = database["gbans"]
gban_history_collection = database["gban_history"]
gban_settings_collection = database["gban_settings"]

async def add_gban_user(user_id: int, reason: str, user_name: str = None, username: str = None):
    await gban_collection.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "reason": reason,
                "user_name": user_name,
                "username": username,
                "banned": True
            }
        },
        upsert=True
    )
    await gban_history_collection.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "ever_gbanned": True,
                "user_name": user_name,
                "username": username
            }
        },
        upsert=True
    )

async def remove_gban_user(user_id: int):
    await gban_collection.update_one(
        {"user_id": user_id},
        {"$set": {"banned": False}}
    )

async def is_user_gbanned(user_id: int) -> bool:
    user = await gban_collection.find_one({"user_id": user_id, "banned": True})
    return user is not None

async def was_user_gbanned_before(user_id: int) -> bool:
    user = await gban_history_collection.find_one({"user_id": user_id, "ever_gbanned": True})
    return user is not None

async def get_all_gbans():
    return await gban_collection.find({"banned": True}).to_list(length=None)

async def get_gban_reason(user_id: int):
    user = await gban_collection.find_one({"user_id": user_id})
    return user.get("reason", "No reason") if user else None

async def set_gban_status(chat_id: int, enabled: bool):
    await gban_settings_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "gban_enabled": enabled}},
        upsert=True
    )

async def get_gban_status(chat_id: int) -> bool:
    chat = await gban_settings_collection.find_one({"chat_id": chat_id})
    if chat is None:
        return True
    return chat.get("gban_enabled", True)

async def get_all_gban_disabled_chats():
    return await gban_settings_collection.find({"gban_enabled": False}).to_list(length=None)
