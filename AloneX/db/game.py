
from AloneX import database2 as database

db = database['game']


async def delete_data(user_id: int) -> bool:
       user_filter = {"user_id": user_id}
       await db.delete_one(user_filter)
       return True

async def update_cash(user_id: int, cash: int = 0) -> bool:
       user_filter = {"user_id": user_id}
       cash_update = {"$inc": {"cash": cash}}
       okay = await db.update_one(user_filter, cash_update, upsert=True)
       return True


async def get_cash(user_id: int) -> int:
      user_filter = {"user_id": user_id}
      user = await db.find_one(user_filter)
      return user.get('cash', 0) if user else 0
      
async def get_steal_date(user_id: int, target_user_id: int) -> int:
    user_filter = {"user_id": user_id}
    user = await db.find_one(user_filter)
    return user.get("users", {}).get(str(target_user_id)) if user else None

async def update_steal_date(user_id: int, target_user_id: int, steal_date: int) -> bool:
    user_filter = {"user_id": user_id}
    steal_filter = {"$set": {f"users.{target_user_id}": steal_date}}
    okay = await db.update_one(user_filter, steal_filter)
    return True 

async def update_name(user_id: int, name: str) -> bool:
    user_filter = {"user_id": user_id}
    name_filter = {"$set": {"name": name}}
    okay = await db.update_one(user_filter, name_filter)
    return True

async def get_top_users(limit: int = 10):
    top_users = await db.find().sort("cash", -1).limit(limit).to_list(limit)
    return top_users

