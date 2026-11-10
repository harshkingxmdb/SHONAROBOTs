from AloneX import database2 as db

BIO_DB = db.bio_filter
BIO_FILTER_CHATS = set()

async def is_bio_filter_enabled(chat_id: int) -> bool:
    if chat_id in BIO_FILTER_CHATS:
        return True
    data = await BIO_DB.find_one({"chat_id": chat_id})
    if not data:
        return False
    status = data.get("enabled", False)
    if status:
        BIO_FILTER_CHATS.add(chat_id)
    return status

async def set_bio_filter_status(chat_id: int, status: bool):
    if status:
        BIO_FILTER_CHATS.add(chat_id)
    else:
        BIO_FILTER_CHATS.discard(chat_id)

    await BIO_DB.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": status}},
        upsert=True,
    )

async def get_auth_users(chat_id: int) -> list:
    data = await BIO_DB.find_one({"chat_id": chat_id})
    if not data:
        return []
    return data.get("auth_users", [])

async def add_auth(chat_id: int, user_id: int):
    await BIO_DB.update_one(
        {"chat_id": chat_id},
        {"$addToSet": {"auth_users": user_id}},
        upsert=True,
    )

async def remove_auth(chat_id: int, user_id: int):
    await BIO_DB.update_one(
        {"chat_id": chat_id},
        {"$pull": {"auth_users": user_id}},
        upsert=True,
    )

async def initialize_chats():
    try:
        cursor = BIO_DB.find({"enabled": True})
        async for doc in cursor:
            chat_id = doc.get("chat_id")
            if chat_id:
                BIO_FILTER_CHATS.add(int(chat_id))
    except Exception:
        pass
