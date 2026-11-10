from AloneX import database as db

locks_collection = db.locks
CHAT_IDS = []

async def get_locks(chat_id: int):
    try:
        doc = await locks_collection.find_one({"chat_id": chat_id})
        return doc.get("locked", []) if doc else []
    except Exception as e:
        print(f"Error getting locks for {chat_id}: {e}")
        return []

async def update_lock(chat_id: int, lock_type: str):
    try:
        result = await locks_collection.update_one(
            {"chat_id": chat_id},
            {"$addToSet": {"locked": lock_type}},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        print(f"Error updating lock for {chat_id}: {e}")
        return False

async def remove_lock(chat_id: int, lock_type: str):
    try:
        result = await locks_collection.update_one(
            {"chat_id": chat_id},
            {"$pull": {"locked": lock_type}}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error removing lock for {chat_id}: {e}")
        return False

async def is_locked(chat_id: int, lock_type: str) -> bool:
    try:
        locks = await get_locks(chat_id)
        return lock_type in locks or "all" in locks
    except Exception as e:
        print(f"Error checking if locked for {chat_id}: {e}")
        return False

async def remove_all_locks(chat_id: int):
    try:
        result = await locks_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"locked": []}}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error removing all locks for {chat_id}: {e}")
        return False

async def reset_all_locks(chat_id: int):
    try:
        await locks_collection.delete_one({"chat_id": chat_id})
        return True
    except Exception as e:
        print(f"Error resetting all locks for {chat_id}: {e}")
        return False

async def set_lockwarn(chat_id: int, enabled: bool):
    try:
        await locks_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"lockwarn": enabled}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error setting lockwarn for {chat_id}: {e}")
        return False

async def get_lockwarn(chat_id: int) -> bool:
    try:
        doc = await locks_collection.find_one({"chat_id": chat_id})
        return doc.get("lockwarn", False) if doc else False
    except Exception as e:
        print(f"Error getting lockwarn for {chat_id}: {e}")
        return False

async def set_adminlock(chat_id: int, enabled: bool):
    try:
        await locks_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"adminlock": enabled}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error setting adminlock for {chat_id}: {e}")
        return False

async def get_adminlock(chat_id: int) -> bool:
    try:
        doc = await locks_collection.find_one({"chat_id": chat_id})
        return doc.get("adminlock", False) if doc else False
    except Exception as e:
        print(f"Error getting adminlock for {chat_id}: {e}")
        return False

async def count_chats() -> int:
    try:
        return len(await locks_collection.distinct("chat_id"))
    except Exception as e:
        print(f"Error counting lock chats: {e}")
        return 0

async def initialize_chats():
    try:
        chats = await locks_collection.distinct("chat_id")
        CHAT_IDS.clear()
        CHAT_IDS.extend(chats)
        print(f"Initialized {len(chats)} lock chats")
    except Exception as e:
        print(f"Error initializing lock chats: {e}")

async def debug_locks(chat_id: int):
    try:
        doc = await locks_collection.find_one({"chat_id": chat_id})
        print(f"Debug locks for {chat_id}: {doc}")
        return doc
    except Exception as e:
        print(f"Debug error for {chat_id}: {e}")
        return None
