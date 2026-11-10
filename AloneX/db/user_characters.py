
from AloneX import database2 as database
from typing import Optional, Dict, Any

db = database['user_characters']

USER_CHARACTERS = []




async def update_user_level(user_id: int, level: int = 1) -> bool:
    user_filter = {"user_id": user_id}
    update_filter = {"$inc": {"level": level}}
    update = await db.update_one(user_filter, update_filter, upsert=True)
    return update.modified_count > 0 or update.upserted_id is not None


async def get_user_level(user_id: int) -> int:
    user_filter = {"user_id": user_id}
    user = await db.find_one(user_filter)
    if user:
        if "level" not in user:
            await db.update_one(user_filter, {"$set": {"level": 0}})
            return 0
        return user["level"]
    return 0


async def update_user_win(user_id: int, win: int = 1) -> bool:
    user_filter = {"user_id": user_id}
    update_filter = {"$inc": {"win_count": level}}
    update = await db.update_one(user_filter, update_filter, upsert=True)
    return update.modified_count > 0 or update.upserted_id is not None


async def update_user_lose(user_id: int, win: int = 1) -> bool:
    user_filter = {"user_id": user_id}
    update_filter = {"$inc": {"lose_count": level}}
    update = await db.update_one(user_filter, update_filter, upsert=True)
    return update.modified_count > 0 or update.upserted_id is not None



async def get_user_lose(user_id: int) -> int:
    user_filter = {"user_id": user_id}
    user = await db.find_one(user_filter)
    if user:
        if "lose_count" not in user:
            await db.update_one(user_filter, {"$set": {"lose_count": 0}})
            return 0
        return user["lose_count"]
    return 0


async def get_user_win(user_id: int) -> int:
    user_filter = {"user_id": user_id}
    user = await db.find_one(user_filter)
    if user:
        if "win_count" not in user:
            await db.update_one(user_filter, {"$set": {"win_count": 0}})
            return 0
        return user["win_count"]
    return 0



async def add_user_character(
    user_id: int,
    character_name: str,
    character_id: str,
    rarity_type: int = 404,
    health: int = 200,
    attack: list = [],
    images: list = [],
):
    character_data = {
        "character_id": character_id,
        "character_name": character_name,
        "health": health,
        "attack": attack,
        "rarity_type": rarity_type,
        "images": images,
    }

    update_operation = {
        '$set': {f'characters.{character_id}': character_data}
    }

    result = await db.update_one(
        {'user_id': user_id},
        update_operation,
        upsert=True
    )
  
    return result.modified_count > 0 or result.upserted_id is not None

async def update_user_character(
    user_id: int,
    character_id: int,
    character_name: Optional[str] = None,
    health: Optional[int] = None,
    attack: Optional[list] = None,
    images: Optional[list] = None,
    rarity_type: Optional[int] = None
):
    update_fields = {}
    
    if character_name is not None:
        update_fields[f'characters.{character_id}.character_name'] = character_name
    if health is not None:
        update_fields[f'characters.{character_id}.health'] = health
    if attack is not None:
        update_fields[f'characters.{character_id}.attack'] = attack
    if images is not None:
        update_fields[f'characters.{character_id}.images'] = images
    if rarity_type is not None:
        update_fields[f'characters.{character_id}.rarity_type'] = rarity_type

    if not update_fields:
        return False  # No fields to update

    update_operation = {
        '$set': update_fields
    }

    result = await db.update_one(
        {'user_id': user_id, f'characters.{character_id}': {'$exists': True}},
        update_operation
    )

    return result.modified_count > 0


async def initialize_user_characters():
      user_character_db = await db.find({}).to_list()
      if USER_CHARACTERS:
          USER_CHARACTERS.clear()
      USER_CHARACTERS.extend(user_character_db)


async def get_user_characters(user_id: int):
     character = await db.find_one({'user_id': user_id})
     return dict(character.get('characters')) if character else {}


async def remove_user_character(user_id: int, character_id: str):
    update_operation = {
        '$unset': {f'characters.{character_id}': ''}
    }

    result = await db.update_one(
        {'user_id': user_id},
        update_operation
    )

    return result.modified_count > 0


async def get_user_character(user_id: int, character_id: str) -> Optional[Dict[str, Any]]:
    query = {
        'user_id': user_id
    }
    
    projection = {
        f'characters.{character_id}': 1,
        '_id': 0
    }
    
    document = await db.find_one(query, projection)
    
    if document and 'characters' in document:
        return document['characters'].get(character_id)
    
    return None


async def user_character_exists(user_id: int, character_id: str) -> bool:
    query = {
        'user_id': user_id,
        f'characters.{character_id}': {'$exists': True}
    }
    document = await db.find_one(query, projection={'_id': 1})
    
    return document is not None
