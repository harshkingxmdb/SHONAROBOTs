import logging
import time
from AloneX import database

LOGGER = logging.getLogger(__name__)

mods_col = database.mods

async def add_mod_role(chat_id: int, user_id: int, role: str):
    try:
        existing = await check_mod_role(chat_id, user_id, role)
        if existing:
            return False
        await mods_col.insert_one({'chat_id': chat_id, 'user_id': user_id, 'role': role, 'created_at': time.time()})
        return True
    except: return False

async def remove_mod_role(chat_id: int, user_id: int, role: str):
    try:
        result = await mods_col.delete_one({'chat_id': chat_id, 'user_id': user_id, 'role': role})
        return result.deleted_count > 0
    except: return False

async def check_mod_role(chat_id: int, user_id: int, role: str = None):
    try:
        query = {'chat_id': chat_id, 'user_id': user_id}
        if role: query['role'] = role
        doc = await mods_col.find_one(query, {'_id': 1})
        return doc is not None
    except: return False

async def get_user_mod_role(chat_id: int, user_id: int):
    try:
        doc = await mods_col.find_one({'chat_id': chat_id, 'user_id': user_id}, {'role': 1})
        return doc['role'] if doc else None
    except: return None

async def get_user_all_roles(chat_id: int, user_id: int):
    try:
        cursor = mods_col.find({'chat_id': chat_id, 'user_id': user_id}, {'role': 1})
        return [doc['role'] async for doc in cursor]
    except: return []

async def get_all_mods(chat_id: int):
    try:
        cursor = mods_col.find({'chat_id': chat_id}, {'user_id': 1, 'role': 1, 'created_at': 1}).sort('created_at', -1)
        return [{'user_id': doc['user_id'], 'role': doc['role'], 'created_at': doc.get('created_at')} async for doc in cursor]
    except: return []

async def remove_all_user_mods(chat_id: int, user_id: int):
    try:
        result = await mods_col.delete_many({'chat_id': chat_id, 'user_id': user_id})
        return result.deleted_count
    except: return 0

async def remove_all_mods(chat_id: int):
    try:
        result = await mods_col.delete_many({'chat_id': chat_id})
        return result.deleted_count
    except: return 0

async def initialize_mods():
    try:
        await mods_col.create_index([('chat_id', 1), ('user_id', 1), ('role', 1)], unique=True)
        await mods_col.create_index('chat_id')
        await mods_col.create_index('user_id')
        LOGGER.info("✓ mod_db (MongoDB)")
    except: pass
