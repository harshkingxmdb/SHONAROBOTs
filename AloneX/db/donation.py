from AloneX import database as db

stars_col = db.stars

async def add_stars(user_id: int, amount: int, name=None, username=None):
    await stars_col.update_one(
        {"user_id": user_id},
        {
            "$inc": {"stars": amount},
            "$set": {"name": name, "username": username}
        },
        upsert=True
    )

async def remove_stars(user_id: int, amount: int):
    await stars_col.update_one(
        {"user_id": user_id},
        {"$inc": {"stars": -amount}}
    )

async def get_user_stars(user_id: int) -> int:
    doc = await stars_col.find_one({"user_id": user_id})
    return doc["stars"] if doc and "stars" in doc else 0

async def get_top_donors(limit: int = 10):
    cursor = stars_col.find({"stars": {"$gt": 0}})
    donors = []
    async for doc in cursor:
        donors.append((
            doc["user_id"],
            doc["stars"],
            doc.get("name", "User"),
            doc.get("username")
        ))
    donors.sort(key=lambda x: x[1], reverse=True)
    return donors[:limit]
