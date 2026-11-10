from AloneX import database as db

DISABLE_COLLECTION = db["disabled_cmds"]


async def disable_cmd(chat_id: int, cmd: str):
    await DISABLE_COLLECTION.update_one(
        {"chat_id": chat_id},
        {"$addToSet": {"disabled": cmd}},
        upsert=True
    )


async def enable_cmd(chat_id: int, cmd: str):
    await DISABLE_COLLECTION.update_one(
        {"chat_id": chat_id},
        {"$pull": {"disabled": cmd}},
        upsert=True
    )


async def get_disabled(chat_id: int):
    data = await DISABLE_COLLECTION.find_one({"chat_id": chat_id})
    if not data or "disabled" not in data:
        return []
    return data["disabled"]


async def count_disabled_items() -> int:
    total = 0
    async for doc in DISABLE_COLLECTION.find({}):
        disabled_list = doc.get("disabled", [])
        total += len(disabled_list)
    return total


async def count_chats() -> int:
    return await DISABLE_COLLECTION.count_documents({"disabled": {"$exists": True, "$ne": []}})


async def enable_all_cmds(chat_id: int):
    await DISABLE_COLLECTION.delete_one({"chat_id": chat_id})
