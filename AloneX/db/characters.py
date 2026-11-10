
from AloneX import database2 as database

db = database['characters']


CHARACTERS = []


async def add_character(
       character_name: str,
       health: int = 200,
       attack: list = [],
       images: list = [],
       rarity_type: int = 404,
       cash: int = 2000,
):

      last_character = await db.find_one(sort=[("character_id", -1)])
      character_id = f"{int(last_character['character_id']) + 1:02d}" if last_character else "01"
      character_data = {
        "character_id": character_id,
        "character_name": character_name,
        "health": health,
        "attack": attack,
        "rarity_type": rarity_type,
        "images": images,
        "cash": cash,
}
      result = await db.insert_one(character_data)
      return result.inserted_id is not None


async def get_character(character_id: str):
    result = await db.find_one({"character_id": character_id})
    return result
       
async def remove_character(character_id: str):
    result = await db.delete_one({"character_id": character_id})
    return result.deleted_count > 0

async def get_all_characters():
    characters = await db.find().to_list(length=None)
    return characters

async def initialize_characters():
      characters = await get_all_characters()
      CHARACTERS.extend(characters)

async def get_character_by_id(character_id: str):
    character = await db.find_one({"character_id": character_id})
    return character

async def update_character_name(character_id: str, new_name: str):
    result = await db.update_one(
        {"character_id": character_id},
        {"$set": {"character_name": new_name}}
    )
    return result.modified_count > 0

async def update_character_health(character_id: str, new_health: int):
    result = await db.update_one(
        {"character_id": character_id},
        {"$set": {"health": new_health}}
    )
    return result.modified_count > 0

async def update_character_attack(character_id: str, new_attack: list):
    result = await db.update_one(
        {"character_id": character_id},
        {"$set": {"attack": new_attack}}
    )
    return result.modified_count > 0

async def update_character_rarity_type(character_id: str, new_rarity_type: int):
    result = await db.update_one(
        {"character_id": character_id},
        {"$set": {"rarity_type": new_rarity_type}}
    )
    return result.modified_count > 0

async def update_character_images(character_id: str, new_images: list):
    result = await db.update_one(
        {"character_id": character_id},
        {"$set": {"images": new_images}}
    )
    return result.modified_count > 0

async def update_character_cash(character_id: str, new_cash: int):
    result = await db.update_one(
        {"character_id": character_id},
        {"$set": {"cash": new_cash}}
    )
    return result.modified_count > 0

