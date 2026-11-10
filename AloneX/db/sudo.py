from AloneX import database as db
import config

sudo_col = db["sudos"]
support_col = db["supports"]
whitelist_col = db["whitelists"]

_sudo_cache = set()
_support_cache = set()
_whitelist_cache = set()
_loaded = False

async def load_cache():
    global _loaded
    if _loaded:
        return
    if hasattr(config, 'SUDO_USERS') and config.SUDO_USERS:
        _sudo_cache.update(config.SUDO_USERS if isinstance(config.SUDO_USERS, list) else [config.SUDO_USERS])
    if hasattr(config, 'SUPPORT_USERS') and config.SUPPORT_USERS:
        _support_cache.update(config.SUPPORT_USERS if isinstance(config.SUPPORT_USERS, list) else [config.SUPPORT_USERS])
    if hasattr(config, 'WHITELIST_USERS') and config.WHITELIST_USERS:
        _whitelist_cache.update(config.WHITELIST_USERS if isinstance(config.WHITELIST_USERS, list) else [config.WHITELIST_USERS])
    async for doc in sudo_col.find({}):
        _sudo_cache.add(doc["user_id"])
    async for doc in support_col.find({}):
        _support_cache.add(doc["user_id"])
    async for doc in whitelist_col.find({}):
        _whitelist_cache.add(doc["user_id"])
    _loaded = True

async def initialize_cache():
    await load_cache()

async def add_sudo_user(user_id: int) -> bool:
    if hasattr(config, 'SUDO_USERS'):
        config_sudos = config.SUDO_USERS if isinstance(config.SUDO_USERS, list) else [config.SUDO_USERS]
        if user_id in config_sudos:
            _sudo_cache.add(user_id)
            return False
    if await sudo_col.find_one({"user_id": user_id}):
        _sudo_cache.add(user_id)
        return False
    await sudo_col.insert_one({"user_id": user_id})
    _sudo_cache.add(user_id)
    return True

async def remove_sudo_user(user_id: int) -> bool:
    if hasattr(config, 'SUDO_USERS'):
        config_sudos = config.SUDO_USERS if isinstance(config.SUDO_USERS, list) else [config.SUDO_USERS]
        if user_id in config_sudos:
            return False
    result = await sudo_col.delete_one({"user_id": user_id})
    _sudo_cache.discard(user_id)
    return result.deleted_count > 0

async def get_all_sudo_users() -> list[int]:
    if not _loaded:
        await load_cache()
    return list(_sudo_cache)

async def is_sudo_user(user_id: int) -> bool:
    if not _loaded:
        await load_cache()
    return user_id in _sudo_cache

async def add_support_user(user_id: int) -> bool:
    if hasattr(config, 'SUPPORT_USERS'):
        config_supports = config.SUPPORT_USERS if isinstance(config.SUPPORT_USERS, list) else [config.SUPPORT_USERS]
        if user_id in config_supports:
            _support_cache.add(user_id)
            return False
    if await support_col.find_one({"user_id": user_id}):
        _support_cache.add(user_id)
        return False
    await support_col.insert_one({"user_id": user_id})
    _support_cache.add(user_id)
    return True

async def remove_support_user(user_id: int) -> bool:
    if hasattr(config, 'SUPPORT_USERS'):
        config_supports = config.SUPPORT_USERS if isinstance(config.SUPPORT_USERS, list) else [config.SUPPORT_USERS]
        if user_id in config_supports:
            return False
    result = await support_col.delete_one({"user_id": user_id})
    _support_cache.discard(user_id)
    return result.deleted_count > 0

async def get_all_support_users() -> list[int]:
    if not _loaded:
        await load_cache()
    return list(_support_cache)

async def is_support_user(user_id: int) -> bool:
    if not _loaded:
        await load_cache()
    return user_id in _support_cache

async def add_whitelist_user(user_id: int) -> bool:
    if hasattr(config, 'WHITELIST_USERS'):
        config_whitelists = config.WHITELIST_USERS if isinstance(config.WHITELIST_USERS, list) else [config.WHITELIST_USERS]
        if user_id in config_whitelists:
            _whitelist_cache.add(user_id)
            return False
    if await whitelist_col.find_one({"user_id": user_id}):
        _whitelist_cache.add(user_id)
        return False
    await whitelist_col.insert_one({"user_id": user_id})
    _whitelist_cache.add(user_id)
    return True

async def remove_whitelist_user(user_id: int) -> bool:
    if hasattr(config, 'WHITELIST_USERS'):
        config_whitelists = config.WHITELIST_USERS if isinstance(config.WHITELIST_USERS, list) else [config.WHITELIST_USERS]
        if user_id in config_whitelists:
            return False
    result = await whitelist_col.delete_one({"user_id": user_id})
    _whitelist_cache.discard(user_id)
    return result.deleted_count > 0

async def get_all_whitelist_users() -> list[int]:
    if not _loaded:
        await load_cache()
    return list(_whitelist_cache)

async def is_whitelist_user(user_id: int) -> bool:
    if not _loaded:
        await load_cache()
    return user_id in _whitelist_cache

async def get_all_protected_ids() -> set[int]:
    if not _loaded:
        await load_cache()
    return _sudo_cache | _support_cache | _whitelist_cache
