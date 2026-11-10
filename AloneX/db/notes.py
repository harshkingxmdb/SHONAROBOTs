
from AloneX import database2 as database

db = database['notes']


CHAT_IDS = []


async def count_chats() -> int:
      count = await db.count_documents({})
      return count

async def save_note(chat_id, tag, type, text, file_id=None):
    """
    Save a new note to the database
    """
    chat_doc = await db.find_one({'chat_id': chat_id})
    
    new_note = {
        "tag": tag,
        "type": type, 
        "text": text, 
        "file_id": file_id,
        "index": len(chat_doc.get('notes', [])) + 1 if chat_doc else 1
    }
    
    if chat_doc:
        result = await db.update_one(
            {'chat_id': chat_id}, 
            {'$push': {'notes': new_note}}
        )
        return result.modified_count > 0
    else:
        result = await db.insert_one({
            'chat_id': chat_id,
            'notes': [new_note]
        })
        return bool(result.inserted_id)

async def get_notes_by_chat(chat_id):
    """
    Retrieve all notes for a specific chat
    """
    chat_doc = await db.find_one({'chat_id': chat_id})
    return chat_doc.get('notes', []) if chat_doc else []

async def get_note_by_index(chat_id, index):
    """
    Retrieve a specific note by index and chat ID
    """
    chat_doc = await db.find_one({'chat_id': chat_id})
    if chat_doc and 'notes' in chat_doc:
        for note in chat_doc['notes']:
            if note.get('index') == index:
                return note
    return None

async def get_all_chats():
    """
    Retrieve all unique chat IDs with notes
    """
    unique_chats = await db.distinct('chat_id')
    return unique_chats


async def initialize_chats():
      chats = await get_all_chats()
      CHAT_IDS.extend(chats)


async def get_notes_name_by_chat(chat_id: int):
    chat_doc = await db.find_one({'chat_id': chat_id})
    if chat_doc and 'notes' in chat_doc:
          return [note['tag'] for note in chat_doc['notes'] if note.get('tag')]
    return []

async def get_note_by_tag(chat_id, tag):
    """
    Retrieve notes by tag within a specific chat
    """
    chat_doc = await db.find_one({'chat_id': chat_id})
    if chat_doc and 'notes' in chat_doc:
        return [note for note in chat_doc['notes'] if note.get('tag') == tag]
    return []

async def delete_note_by_index(chat_id, index):
    """
    Delete a specific note by index and chat ID
    """
    result = await db.update_one(
        {'chat_id': chat_id},
        {'$pull': {'notes': {'index': index}}}
    )
    return result.modified_count > 0

async def delete_note_by_tag(chat_id, tag):
    """
    Delete all notes with a specific tag in a chat
    """
    result = await db.update_one(
        {'chat_id': chat_id},
        {'$pull': {'notes': {'tag': tag}}}
    )
    return result.modified_count

async def delete_all_notes(chat_id):
    """
    Delete all notes for a specific chat
    """
    result = await db.update_one(
        {'chat_id': chat_id},
        {'$set': {'notes': []}}
    )
    return result.modified_count

async def reindex_notes(chat_id):
    """
    Reindex notes for a specific chat to ensure consecutive indexing
    """
    chat_doc = await db.find_one({'chat_id': chat_id})
    if chat_doc and 'notes' in chat_doc:
        sorted_notes = sorted(chat_doc['notes'], key=lambda x: x.get('index', 0))
        
        for idx, note in enumerate(sorted_notes, 1):
            note['index'] = idx
        
        result = await db.update_one(
            {'chat_id': chat_id},
            {'$set': {'notes': sorted_notes}}
        )
        return result.modified_count > 0
    return False
