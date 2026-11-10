from AloneX import database as db

reactions_db = db["reactions"]


async def get_reaction_status(chat_id: int) -> bool:
    data = await reactions_db.find_one({"chat_id": chat_id})
    if data:
        return data.get("enabled", False)
    return False


async def set_reaction_status(chat_id: int, status: bool) -> bool:
    await reactions_db.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": status}},
        upsert=True
    )
    return True


async def get_all_reaction_chats() -> list:
    chats = []
    async for chat in reactions_db.find({"enabled": True}):
        chats.append(chat["chat_id"])
    return chats


async def count_chats() -> int:
    return await reactions_db.count_documents({"enabled": True})


async def reset_chat_reaction(chat_id: int):
    await reactions_db.delete_one({"chat_id": chat_id})
