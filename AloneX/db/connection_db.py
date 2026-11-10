from AloneX import database as db

connection_coll = db.connections

async def connect(user_id: int, chat_id: int):
    await connection_coll.update_one(
        {"user_id": user_id},
        {
            "$set": {"chat_id": chat_id, "prev_chat_id": chat_id},
            "$addToSet": {"history": chat_id}
        },
        upsert=True
    )

async def disconnect(user_id: int):
    doc = await connection_coll.find_one({"user_id": user_id})
    if doc:
        prev_chat_id = doc.get("chat_id")
        await connection_coll.update_one(
            {"user_id": user_id},
            {"$set": {"chat_id": None, "prev_chat_id": prev_chat_id}}
        )
        return prev_chat_id
    return None

async def reconnect(user_id: int):
    doc = await connection_coll.find_one({"user_id": user_id})
    if doc and doc.get("prev_chat_id"):
        prev = doc.get("prev_chat_id")
        await connection_coll.update_one(
            {"user_id": user_id},
            {"$set": {"chat_id": prev}}
        )
        return prev
    return None

async def get_connected_chat(user_id: int):
    doc = await connection_coll.find_one({"user_id": user_id})
    if doc:
        return doc.get("chat_id")
    return None

async def get_history(user_id: int):
    doc = await connection_coll.find_one({"user_id": user_id})
    if doc:
        history = doc.get("history", [])
        if not history and doc.get("prev_chat_id"):
            return [doc.get("prev_chat_id")]
        return history[-10:] # Return last 10
    return []
