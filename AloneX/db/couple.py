
from AloneX import database2 as database

db = database['couple']


async def count_chats() -> int:
      count = await db.count_documents({})
      return count

async def remove_couple_by_user(chat_id: int, user_id: int) -> bool:
    """
    Remove the entire couple dictionary from couples list 
    if the given user_id is found in either man or woman

    :param chat_id: Chat identifier
    :param user_id: User identifier to remove
    :return: True if couple was removed, False otherwise
    """
    result = await db.update_one(
        {
            'chat_id': chat_id,
            'couples': {
                '$elemMatch': {
                    '$or': [
                        {'man.user_id': user_id},
                        {'woman.user_id': user_id}
                    ]
                }
            }
        },
        {
            '$pull': {
                'couples': {
                    '$or': [
                        {'man.user_id': user_id},
                        {'woman.user_id': user_id}
                    ]
                }
            }
        }
    )
    
    return result.modified_count > 0

async def get_users_not_in_couples(chat_id: int, user_ids: list[int]) -> list[int]:
    """
    Find user_ids that are not in any couple for a given chat
    
    :param chat_id: Chat identifier
    :param user_ids: List of user_ids to check
    :return: List of user_ids not in any couple
    """
    # Find the document for the specific chat
    result = await db.find_one({'chat_id': chat_id})
    
    # If no document found, return all user_ids
    if not result or 'couples' not in result:
        return user_ids
    
    # Extract all user_ids already in couples
    coupled_user_ids = set()
    for couple in result.get('couples', []):
        coupled_user_ids.add(couple['man']['user_id'])
        coupled_user_ids.add(couple['woman']['user_id'])
    
    # Return users not in couples
    return [
        user_id for user_id in user_ids 
        if user_id not in coupled_user_ids
    ]

async def get_user_couple(chat_id: int, user_id: int) -> dict | None:
    """
    Retrieve the specific couple data for a user in a given chat
    
    :param chat_id: Chat identifier
    :param user_id: User identifier
    :return: Specific couple dictionary if user found, None otherwise
    """
    result = await db.find_one({
        'chat_id': chat_id,
        'couples': {
            '$elemMatch': {
                '$or': [
                    {'man.user_id': user_id},
                    {'woman.user_id': user_id}
                ]
            }
        }
    })
    
    if not result or 'couples' not in result:
        return None
    
    # List comprehension to find the matching couple
    matching_couples = [
        couple for couple in result.get('couples', []) 
        if couple['man']['user_id'] == user_id or couple['woman']['user_id'] == user_id
    ]
    
    return matching_couples[0] if matching_couples else None


async def is_user_in_couples(chat_id: int, user_id: int) -> bool:
    """
    Check if a specific user_id exists in the couples data
    
    :param chat_id: Chat identifier
    :param user_id: User identifier to check
    :return: True if user_id found in couples, False otherwise
    """
    result = await db.find_one({
        'chat_id': chat_id,
        'couples': {
            '$elemMatch': {
                '$or': [
                    {'man.user_id': user_id},
                    {'woman.user_id': user_id}
                ]
            }
        }
    })
    return result is not None

async def get_all_chats() -> list[int]:
    """
    Retrieve all unique chat_ids from the database
    
    :return: List of chat_ids
    """
    # Use distinct to get unique chat_ids
    chats = await db.distinct('chat_id')
    return chats
         
async def get_couple(chat_id: int) -> dict | None:
    """
    Retrieve couple data for a specific chat_id
    
    :param chat_id: Chat identifier
    :return: Couple data dictionary if found, None otherwise
    """
    result = await db.find_one({'chat_id': chat_id})
    return result if result else None



async def remove_couple(chat_id: int) -> bool:
    chat_filter = {'chat_id': chat_id}
    result = await db.delete_one(chat_filter)
    return result.deleted_count > 0




async def update_couple(chat_id: int, man: dict, woman: dict, day: int, photo_id = None):
         filter = {'chat_id': chat_id}
         data = {
                "$set": {
                     "man": man,
                     "woman": woman,
                     "day": day,
                     "photo_id": photo_id,
    },
                "$push": {
                     "couples": {"man": man, "woman": woman, "photo_id": photo_id}
    }
         }
         result = await db.update_one(filter, data, upsert=True)
         return result.modified_count > 0 or result.upserted_id is not None


async def reset_chat_couple(chat_id: int):
    await db.delete_one({"chat_id": chat_id})
         
