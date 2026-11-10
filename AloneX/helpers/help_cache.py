from typing import Optional, Dict
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import logging

LOGGER = logging.getLogger(__name__)

class HelpCacheSystem:
    def __init__(self, database):
        self.db = database
        self.help_collection = self.db.help_cache
        self.memory_cache: Dict[str, dict] = {}
        self.session_cache: Dict[str, dict] = {}
    
    async def initialize(self):
        try:
            await self.help_collection.create_index("module_key", unique=True)
            await self.help_collection.create_index("updated_at")
            LOGGER.info("✓ Help Cache Indexes Created")
        except Exception as e:
            LOGGER.error(f"Help Cache initialization failed: {e}")
    
    async def get_help(self, module_key: str) -> Optional[dict]:
        if module_key in self.memory_cache:
            return self.memory_cache[module_key]
        
        doc = await self.help_collection.find_one({"module_key": module_key})
        if doc:
            data = {
                'text': doc['clean_text'],
                'display_name': doc['display_name']
            }
            self.memory_cache[module_key] = data
            return data
        return None
    
    async def set_help(self, module_key: str, help_text: str, clean_text: str, display_name: str):
        try:
            await self.help_collection.update_one(
                {"module_key": module_key},
                {
                    "$set": {
                        "help_text": help_text,
                        "clean_text": clean_text,
                        "display_name": display_name,
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            self.memory_cache[module_key] = {
                'text': clean_text,
                'display_name': display_name
            }
        except Exception as e:
            LOGGER.error(f"Failed to cache help for {module_key}: {e}")
    
    async def preload_all_modules(self, MODULE: dict, safe_markdown_text, clean_module_name):
        try:
            count = 0
            for module_key, help_text in MODULE.items():
                clean_text = safe_markdown_text(help_text)
                display_name = clean_module_name(module_key).upper()
                await self.set_help(module_key, help_text, clean_text, display_name)
                count += 1
            LOGGER.info(f"✓ Preloaded {count} help modules to cache")
        except Exception as e:
            LOGGER.error(f"Preload failed: {e}")
    
    def get_session(self, session_id: str, user_id: int, pages: list, page_num: int = 0) -> dict:
        if session_id in self.session_cache:
            session = self.session_cache[session_id]
            session["timestamp"] = datetime.now(timezone.utc).timestamp()
            return session
        
        self.session_cache[session_id] = {
            "pages": pages,
            "current_page": page_num,
            "timestamp": datetime.now(timezone.utc).timestamp(),
            "user_id": user_id
        }
        return self.session_cache[session_id]
    
    def cleanup_old_sessions(self, timeout: int = 300):
        current_time = datetime.now(timezone.utc).timestamp()
        expired = [
            sid for sid, session in self.session_cache.items()
            if current_time - session["timestamp"] > timeout
        ]
        for sid in expired:
            del self.session_cache[sid]
        if expired:
            LOGGER.info(f"✓ Cleaned {len(expired)} expired help sessions")

help_cache_system = None

async def initialize_help_cache(database):
    global help_cache_system
    help_cache_system = HelpCacheSystem(database)
    await help_cache_system.initialize()
    return help_cache_system
