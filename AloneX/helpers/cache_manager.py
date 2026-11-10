import asyncio
import inspect
import sys
from typing import Dict, Any

_cache_registry = {
    'refresh_functions': [],
    'clear_functions': [],
    'fetch_functions': []
}


def register_cache_refresh(module_name: str = None):
    def decorator(func):
        mod_name = module_name or func.__module__
        _cache_registry['refresh_functions'].append({
            'function': func,
            'module': mod_name,
            'name': func.__name__
        })
        return func
    return decorator


def register_cache_clear(module_name: str = None):
    def decorator(func):
        mod_name = module_name or func.__module__
        _cache_registry['clear_functions'].append({
            'function': func,
            'module': mod_name,
            'name': func.__name__
        })
        return func
    return decorator


async def auto_refresh_all_caches(bot, chat_id: int, user_id: int = None, client=None) -> Dict[str, Any]:
    results = {}
    
    for item in _cache_registry['refresh_functions']:
        try:
            func = item['function']
            module = item['module']
            
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            
            if asyncio.iscoroutinefunction(func):
                if 'bot' in params and 'chat_id' in params and 'user_id' in params:
                    await func(bot, chat_id, user_id)
                elif 'bot' in params and 'chat_id' in params:
                    await func(bot, chat_id)
                elif 'chat_id' in params and 'user_id' in params:
                    await func(chat_id, user_id)
                else:
                    await func()
            
            results[module] = '✅'
        except Exception as e:
            results[module] = f'❌ {str(e)[:20]}'
    
    all_results = await _discover_and_refresh_modules(bot, chat_id, user_id)
    results.update(all_results)
    
    return results


async def _discover_and_refresh_modules(bot, chat_id: int, user_id: int = None) -> Dict[str, str]:
    results = {}
    checked_modules = set()
    
    skip_modules = ['greetings', 'greetings_cmds']
    
    for module_name, module in list(sys.modules.items()):
        is_plugin = module_name.startswith('AloneX.plugins.')
        is_decorator = module_name == 'AloneX.helpers.decorator'
        
        if not (is_plugin or is_decorator):
            continue
        
        if module_name in checked_modules or module is None:
            continue
        
        mod_short = module_name.split('.')[-1]
        if mod_short in skip_modules:
            continue
        
        checked_modules.add(module_name)
        
        try:
            module_refreshed = await _refresh_module_cache(module, bot, chat_id, user_id)
            if module_refreshed:
                short_name = module_name.split('.')[-1]
                results[short_name] = '✅'
        except Exception:
            continue
    
    return results


async def _refresh_module_cache(module, bot, chat_id: int, user_id: int = None) -> bool:
    refreshed = False
    
    cache_keywords = [
        'get_', 'fetch_', 'check_', 'load_',
        'cache', 'cached',
        'refresh', 'reload', 'update'
    ]
    
    skip_keywords = [
        'init_', 'start_', 'setup_', 'on_startup', 'on_start',
        'initialize', 'load_model', 'starting',
        'test_', '__', 'mock_', 'debug_', 'log_', 
        'print_', 'format_', 'parse_',
        'stop', 'shutdown', 'close', 'cleanup', 'on_shutdown'
    ]
    
    unsafe_only_keywords = ['clear', 'delete', 'remove', 'drop', 'purge', 'flush', 'reset']
    
    for attr_name in dir(module):
        if attr_name.startswith('_'):
            continue
        
        attr_lower = attr_name.lower()
        
        if any(skip in attr_lower for skip in skip_keywords):
            continue
        
        has_unsafe = any(unsafe in attr_lower for unsafe in unsafe_only_keywords)
        if has_unsafe:
            has_safe = any(safe in attr_lower for safe in ['refresh', 'reload', 'update'])
            if not has_safe:
                continue
        
        has_cache = any(kw in attr_lower for kw in cache_keywords)
        
        try:
            func = getattr(module, attr_name)
            if not callable(func):
                continue
            
            if not asyncio.iscoroutinefunction(func):
                continue
            
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            
            has_bot_chat = 'bot' in params and 'chat_id' in params
            has_chat_user = 'chat_id' in params and 'user_id' in params
            has_chat_only = 'chat_id' in params
            has_bot_only = 'bot' in params and len(params) == 1
            
            if not has_cache and not (has_bot_chat or has_chat_user or has_chat_only):
                continue
            
            try:
                if 'bot' in params and 'chat_id' in params:
                    if 'force_refresh' in params:
                        await func(bot, chat_id, force_refresh=True)
                    elif 'user_id' in params and user_id:
                        await func(bot, chat_id, user_id)
                    else:
                        await func(bot, chat_id)
                    refreshed = True
                elif 'chat_id' in params and 'user_id' in params:
                    if user_id:
                        await func(chat_id, user_id)
                    refreshed = True
                elif 'chat_id' in params and 'bot' not in params:
                    await func(chat_id)
                    refreshed = True
                elif has_bot_only and has_cache:
                    await func(bot)
                    refreshed = True
            except:
                continue
                
        except:
            continue
    
    return refreshed


async def smart_cache_refresh(bot, chat_id: int, user_id: int = None, client=None) -> Dict[str, str]:
    results = {}
    
    categories = {
        'Core': [],
        'Plugins': []
    }
    
    try:
        if 'AloneX.plugins.admins' in sys.modules:
            from AloneX.plugins.admins import (
                get_chat_cached, 
                get_member_cached, 
                get_admin_cached,
                reload_admins_cache
            )
            
            await get_chat_cached(bot, chat_id, force_refresh=True)
            await get_member_cached(bot, chat_id, bot.id, force_refresh=True)
            await get_admin_cached(bot, chat_id, bot.id, force_refresh=True)
            
            if user_id:
                await get_member_cached(bot, chat_id, user_id, force_refresh=True)
                await get_admin_cached(bot, chat_id, user_id, force_refresh=True)
            
            await reload_admins_cache(bot, chat_id)
            categories['Core'].append('admins')
    except:
        pass
    
    try:
        if 'AloneX.helpers.decorator' in sys.modules:
            from AloneX.helpers.decorator import (
                get_member_cached as dec_member,
                check_user_admin_cached,
                refresh_sudo_users
            )
            
            await dec_member(bot, chat_id, bot.id)
            await check_user_admin_cached(bot, chat_id, bot.id)
            
            if user_id:
                await dec_member(bot, chat_id, user_id)
                await check_user_admin_cached(bot, chat_id, user_id)
            
            await refresh_sudo_users()
            categories['Core'].append('decorator')
    except:
        pass
    
    plugin_modules = sorted([
        name for name in sys.modules.keys() 
        if name.startswith('AloneX.plugins.') and sys.modules[name] is not None
    ])
    
    skip_modules = ['greetings', 'greetings_cmds', 'logo', 'crypto', 'callbacks', 'base', 'adminpanel']
    
    for module_name in plugin_modules:
        mod_short = module_name.split('.')[-1]
        
        if mod_short == 'admins' or mod_short in skip_modules:
            continue
        
        try:
            module = sys.modules[module_name]
            if module is None:
                continue
            
            refreshed = await _refresh_module_cache(module, bot, chat_id, user_id)
            if refreshed:
                categories['Plugins'].append(mod_short)
        except:
            continue
    
    for category, items in categories.items():
        if items:
            results[category] = ', '.join(items)
    
    return results
