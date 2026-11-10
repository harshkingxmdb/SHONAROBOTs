# AloneX/db/birthday.py
from AloneX import database  # Motor database instance
bday_collection = database["AloneX"]["Birthdays"]

# ➕ Save or update birthday
async def save_birthday(user_id: int, name: str, date: str):
    await bday_collection.update_one(
        {"id": user_id},
        {"$set": {"name": name, "date": date}},
        upsert=True
    )

# ❌ Remove birthday
async def remove_birthday(user_id: int):
    await bday_collection.delete_one({"id": user_id})

# 📥 Get all saved birthdays
async def get_birthdays():
    return await bday_collection.find().to_list(length=1000)
