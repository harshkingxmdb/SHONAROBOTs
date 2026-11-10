import logging
from AloneX import database as db

banall_coll = db.banall
LOCKDOWN_CACHE = {}
STATUS_CACHE = {}

async def set_lockdown(chat_id: int, status: bool):
    await banall_coll.update_one(
        {"chat_id": chat_id},
        {"$set": {"lockdown": status}},
        upsert=True
    )
    LOCKDOWN_CACHE[chat_id] = status

async def is_lockdown(chat_id: int) -> bool:
    if chat_id in LOCKDOWN_CACHE:
        return LOCKDOWN_CACHE[chat_id]
    doc = await banall_coll.find_one({"chat_id": chat_id})
    res = doc.get("lockdown", False) if doc else False
    LOCKDOWN_CACHE[chat_id] = res
    return res

async def set_banall_status(chat_id: int, status: bool):
    await banall_coll.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": status}},
        upsert=True
    )
    STATUS_CACHE[chat_id] = status

async def is_banall_enabled(chat_id: int) -> bool:
    if chat_id in STATUS_CACHE:
        return STATUS_CACHE[chat_id]
    doc = await banall_coll.find_one({"chat_id": chat_id})
    # Defaulting to True for a security trap seems logical,
    # but the user said "/antibanall" toggle, which often implies "anti-trap" protection.
    # However, standard pattern is toggle for the feature.
    res = doc.get("enabled", True) if doc else True
    STATUS_CACHE[chat_id] = res
    return res

LOGGER = logging.getLogger(__name__)

async def initialize_chats():
    try:
        count_lock = 0
        count_status = 0
        async for doc in banall_coll.find({}):
            chat_id = doc["chat_id"]
            if doc.get("lockdown"):
                LOCKDOWN_CACHE[chat_id] = True
                count_lock += 1
            if "enabled" in doc:
                STATUS_CACHE[chat_id] = doc["enabled"]
                count_status += 1
        LOGGER.info(f"Initialized {count_lock} lockdown chats and {count_status} status settings")
    except Exception as e:
        LOGGER.error(f"Error initializing banall chats: {e}")
