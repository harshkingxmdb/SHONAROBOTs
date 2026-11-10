import time
from telegram.constants import ChatMemberStatus
from AloneX.db.mod import get_user_all_roles

class ModRoleCache:
    __slots__ = ('d', 't', 'm')
    def __init__(self, m=10000, t=0.5):
        self.d = {}
        self.t = t
        self.m = m
    
    def get(self, k):
        if k in self.d:
            v, e = self.d[k]
            if time.monotonic() < e:
                return v
            del self.d[k]
        return None
    
    def set(self, k, v):
        if len(self.d) >= self.m:
            to_remove = list(self.d.keys())[:self.m // 10]
            for key in to_remove:
                self.d.pop(key, None)
        self.d[k] = (v, time.monotonic() + self.t)
    
    def clear_user(self, chat_id, user_id):
        self.d.pop((chat_id, user_id), None)

mod_role_cache = ModRoleCache()

PERM_ACTIONS = {
    "warn": {"mod", "warner"},
    "mute": {"mod", "muter"},
    "restrict": {"mod", "muter"},
    "ban": {"mod"},
    "kick": {"mod"},
    "delete": {"mod", "cleaner"}
}

async def check_mod_permission_fast(chat_id: int, user_id: int, action: str, chat_obj) -> bool:
    from AloneX import DEV_LIST
    from AloneX.helpers.decorator import is_sudo_user_db
    
    if user_id in DEV_LIST:
        return True
    
    cache_key = (chat_id, user_id)
    cached_roles = mod_role_cache.get(cache_key)
    
    is_user_sudo = await is_sudo_user_db(user_id)
    if is_user_sudo:
        return True
    
    try:
        member = await chat_obj.get_member(user_id)
        
        if member.status == ChatMemberStatus.OWNER:
            mod_role_cache.set(cache_key, ["admin"])
            return True
        
        if member.status == ChatMemberStatus.ADMINISTRATOR:
            if getattr(member, "can_restrict_members", False):
                mod_role_cache.set(cache_key, ["admin"])
                return True
    except Exception:
        pass
    
    if cached_roles is not None and "admin" in cached_roles:
        return True

    if cached_roles is not None:
        allowed_roles = PERM_ACTIONS.get(action, set())
        return any(role in allowed_roles for role in cached_roles)
    
    try:
        roles = await get_user_all_roles(chat_id, user_id)
        mod_role_cache.set(cache_key, roles if roles else ["none"])
        
        if not roles:
            return False
        
        allowed_roles = PERM_ACTIONS.get(action, set())
        return any(role in allowed_roles for role in roles)
    except Exception:
        return False

def clear_mod_cache(chat_id: int = None, user_id: int = None):
    if chat_id and user_id:
        mod_role_cache.clear_user(chat_id, user_id)
    elif chat_id:
        keys_to_remove = [k for k in mod_role_cache.d.keys() if k[0] == chat_id]
        for key in keys_to_remove:
            mod_role_cache.d.pop(key, None)

async def can_user_warn(chat_id: int, user_id: int, chat_obj) -> bool:
    return await check_mod_permission_fast(chat_id, user_id, "warn", chat_obj)

async def can_user_mute(chat_id: int, user_id: int, chat_obj) -> bool:
    return await check_mod_permission_fast(chat_id, user_id, "mute", chat_obj)

async def can_user_ban(chat_id: int, user_id: int, chat_obj) -> bool:
    return await check_mod_permission_fast(chat_id, user_id, "ban", chat_obj)

async def can_user_delete(chat_id: int, user_id: int, chat_obj) -> bool:
    return await check_mod_permission_fast(chat_id, user_id, "delete", chat_obj)
