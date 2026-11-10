from AloneX import database as db

join_request_col = db["join_request"]


async def toggle_request(chat_id: int, state: bool):
    """Enable or disable join request notification for a chat"""
    await join_request_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": state}},
        upsert=True
    )


async def is_request_enabled(chat_id: int) -> bool:
    """Check if join request is enabled for a chat"""
    doc = await join_request_col.find_one({"chat_id": chat_id})
    return bool(doc and doc.get("enabled", False))


async def reset_chat_join_request(chat_id: int):
    await join_request_col.delete_one({"chat_id": chat_id})
