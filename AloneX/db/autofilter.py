
import re
from AloneX import database as db
from AloneX.helpers.utils import async_cache
from typing import List, Dict, Optional
from pymongo import ASCENDING, DESCENDING
from itertools import permutations

database = db['autofilter']


CHAT_IDS = []

async def count_chats() -> int:
      count = await database.chats.count_documents({})
      return count


async def update_chat_imdb(chat_id: int, imdb: bool):
    try:
        chat = {'chat_id': chat_id}  # Ensure chat_id is an integer
        data = {
            '$set': {  # Use $set to update fields
                'imdb': imdb
            }
        }
        result = await database.chats.update_one(chat, data, upsert=True)
        return result.upserted_id is not None or result.modified_count > 0
    except Exception as e:
        print(f"Error updating chat: {e}")

async def update_chat_type(chat_id: int, type: [str, bool]):
    try:
        chat = {'chat_id': chat_id}  # Ensure chat_id is an integer
        data = {
            '$set': {  # Use $set to update fields
                'type': type
            }
        }
        result = await database.chats.update_one(chat, data, upsert=True)
        return result.upserted_id is not None or result.modified_count > 0
    except Exception as e:
        print(f"Error updating chat: {e}")

async def get_chat_type(chat_id: int):
      chat = {'chat_id': chat_id}
      result = await database.chats.find_one(chat)
      if result:
           return result.get('type')
      return False

async def get_chat_imdb(chat_id: int):
      chat = {'chat_id': chat_id}
      result = await database.chats.find_one(chat)
      if result:
           return result.get('imdb')
      return False



async def remove_chat(chat_id: int):
    try:
        result = await database.chats.delete_one({'chat_id': chat_id})
        return result.deleted_count > 0  # Check deleted_count instead
    except Exception as e:
        print(f"Error removing chat: {e}")
      


async def get_all_chats():
    try:
        chats = await database.chats.find().to_list(length=None)
        return [chat['chat_id'] for chat in chats]
    except Exception as e:
        print(f"Error getting all chats: {e}")
        return []


async def initialize_db_chats():
     users = await get_all_chats()
     CHAT_IDS.extend(users)


@async_cache(max_size=15)
async def get_latest_files(limit: int = 40):
      files = database.files.find({}).sort('_id', -1).limit(limit)
      return await files.to_list()


async def get_files_by_index(start_index: int, max_length: int = 10):
    max_length += 1 # for fixed length
    files = await database.files.find(
        {'index': {'$gte': start_index, '$lt': start_index + max_length}}
    ).to_list(length=max_length)
    return files



# Function to add a file
async def add_file(file_name: list[str], file_type: str, file_id: str, file_unique_id: str, filter_type: str):
    # Get the current count of files to determine the index
    count = await database.files.count_documents({})
    index = count + 1  # Start index from 1

    file_query = {'file_unique_id': file_unique_id}
    exist = await database.files.find_one(file_query)
    if exist:
        return False

    data = {
        'file_name': file_name,
        'index': index,
        'file_type': file_type,
        'filter_type': filter_type,
        'file_id': file_id,
        'file_unique_id': file_unique_id
    }

    result = await database.files.insert_one(data)
    return result.inserted_id is not None
  

# Function to get files by filter type
async def get_files_by_type(filter_type: str):
    files = await database.files.find({'filter_type': filter_type}).to_list(length=None)
    return files

async def get_files_count():
    count = await database.files.count_documents({})
    return count

async def count_files_by_type(filter_type: str):
    count = await database.files.count_documents({'filter_type': filter_type})
    return count




async def get_files_by_name_v1(query: str, filter_type: str = None, limit: int = 50) -> list[dict]:
    """
    Optimized search function for files using regex and MongoDB indexing
    
    Args:
        query: Search term for file names
        filter_type: Optional filter type
        limit: Maximum results to return (default 50)
    Returns:
        List of matching files with index and file_type
    """
    # Base query with only needed fields
    projection = {
        "index": 1,
        "file_type": 1,
        "file_name": 1,
        "file_id": 1,
        "_id": 0
    }
    
    # Build search query
    search_query = {}
    
    # Add filter type if specified
    if filter_type and filter_type != 'all':
        search_query["filter_type"] = filter_type
    
    # Add file name search if query provided
    if query.strip():
        # Create case-insensitive regex pattern
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        search_query["file_name"] = {"$regex": pattern}
    
    # Execute search
    cursor = database.files.find(
        search_query,
        projection
    ).limit(limit)
    
    return await cursor.to_list(length=limit)



#words = [re.escape(word) for word in search_query.split()]
#lookahead_patterns = [f'(?=.*{word})' for word in words]
#regex_pattern = ''.join(lookahead_patterns) + '.*'
#return regex_pattern


@async_cache(max_size=30)
async def get_files_by_name(search_query: str, filter_type: str = None, limit: int = 50):
    """
    Hybrid search function that uses regex for queries with 4 or fewer words
    and text search for longer queries
    
    Args:
        search_query (str): The search term to look for
        filter_type (str, optional): Type of filter to apply
        limit (int, optional): Maximum number of results to return
        
    Returns:
        list: Search results
    """
    # Initialize base query
    query = {}
    if filter_type and filter_type != 'all':
        query['filter_type'] = filter_type
        
    # Common projection for both search types
    projection = {
        'file_id': 1,
        'file_type': 1, 
        'index': 1,
        'file_name': 1,
        '_id': 0
    }

    # For shorter queries, use regex search
    if len(search_query.split()) <= 4:
        words = [re.escape(word) for word in search_query.lower().split()]
        patterns = []
        for perm in permutations(words):
            pattern = '.*'.join(perm)
            patterns.append(pattern)
        regex_pattern = '|'.join(patterns)
        
        # Add regex search condition to query
        query['file_name'] = {'$regex': regex_pattern, '$options': 'i'}
        
        results = await database.files.find(
            query,
            projection
        ).sort('index', DESCENDING).limit(limit).to_list(None)
        
    # For longer queries, use text search
    else:
        query.update({
            '$text': {
                '$search': search_query,
                '$caseSensitive': False
            }
        })
        
        # Add score to projection for text search
        projection['score'] = {'$meta': 'textScore'}
        
        # Sort by text score for text search
        sort = [('score', {'$meta': 'textScore'}), ('index', DESCENDING)]
        
        results = await database.files.find(
            query,
            projection
        ).sort(sort).limit(limit).to_list(None)
    
    return results



async def get_files_by_name_fast(search_query: str, filter_type: str = None, limit: int = 50) -> list[dict]:
    """
    Optimized regex-based search returning only file_type, index, and file_name fields.
    Uses MongoDB's $regex for pattern matching to improve performance.
    """
    query = {}
    if filter_type and filter_type != 'all':
        query['filter_type'] = filter_type

    # Create optimized regex pattern
    words = [re.escape(word) for word in search_query.lower().split()]
    pattern = '.*'.join(words)  # Create a pattern for MongoDB

    query['file_name'] = {'$regex': pattern, '$options': 'i'}

    # Use projection to get only needed fields
    files = await database.files.find(
        query,
        { 'file_id': 1, 'file_type': 1, 'index': 1, 'file_name': 1, '_id': 0}
    ).sort('index', ASCENDING).limit(limit).to_list(length=None)

    return files


async def get_files_by_name_test_v1(search_query: str, filter_type: str = None) -> list[dict]:
    """
    Optimized regex-based search returning only file_type, index, and file_name fields.
    Uses projection to reduce data transfer and improve performance.
    """
    query = {}
    if filter_type and filter_type != 'all':
        query['filter_type'] = filter_type

    # Use projection to get only needed fields
    files = await database.files.find(
             query,
           {'file_type': 1, 'index': 1, 'file_name': 1, '_id': 0}
    ).to_list(length=None)
    
    # Create optimized regex pattern outside the loop
    words = [re.escape(word) for word in search_query.lower().split()]
    pattern = re.compile(''.join(f'(?=.*\\b{word}\\b)' for word in words), re.IGNORECASE)
    
    # Filter files with pattern matching
    matched_files = [file for file in files if pattern.search(" ".join(file['file_name']))]
    
    return matched_files


# Function to get a file by index
async def get_file_by_index(index: int):
    file = await database.files.find_one({'index': index})
    return file

# Function to delete a file by index
async def delete_file_by_index(index: int):
    result = await database.files.delete_one({'index': index})
    return result.deleted_count > 0  # Returns True if a file was deleted

async def update_file_by_index(index: int, updates: dict):
    result = await database.files.update_one({'index': index}, {'$set': updates})
    return result.modified_count > 0  # Returns True if a file was updated


async def update_filename_by_file_unique_id(file_unique_id: str, file_name: list):
     query = {'file_unique_id': file_unique_id}
     if await database.files.count_documents(query) > 0:
          data = {
             "$set": {
                "file_name": file_name
             }
          }
          result = await database.files.update_one(query, data)
          return result.modified_count > 0
       

async def file_exists(file_unique_id: str):
    # Construct the query to check for existence based on file_id
    query = {'file_unique_id': file_unique_id}
    # Check if any documents match the query
    exists = await database.files.count_documents(query) > 0
    return exists
  
