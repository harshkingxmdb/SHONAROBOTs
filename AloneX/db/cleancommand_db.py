from typing import Optional
from AloneX import database as db

cleancommand_collection = db.cleancommand


async def set_clean_type(chat_id: int, clean_type: str) -> None:
    await cleancommand_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"clean_type": clean_type}},
        upsert=True
    )


async def get_clean_type(chat_id: int) -> Optional[str]:
    doc = await cleancommand_collection.find_one({"chat_id": chat_id})
    if doc and doc.get("clean_type") != "disabled":
        return doc.get("clean_type")
    return None


async def disable_cleaning(chat_id: int) -> None:
    await cleancommand_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"clean_type": "disabled"}},
        upsert=True
    )


async def reset_chat_cleancommand(chat_id: int):
    await cleancommand_collection.delete_one({"chat_id": chat_id})
