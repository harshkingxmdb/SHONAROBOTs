import shortuuid
from AloneX import database
from datetime import datetime, timezone

# Collections
feds_db = database['federations']
chat_fed_db = database['chat_federations']

async def create_fed(owner_id: int, fed_name: str):
    fed_id = shortuuid.uuid()
    fed_data = {
        "fed_id": fed_id,
        "owner_id": owner_id,
        "fed_name": fed_name,
        "admins": [],
        "banned_users": {},
        "subs": [],
        "log_channel": None,
        "reason_required": True,
        "notifications": True,
        "lang": "en"
    }
    await feds_db.insert_one(fed_data)
    return fed_id

async def delete_fed(fed_id: str):
    await feds_db.delete_one({"fed_id": fed_id})
    await chat_fed_db.delete_many({"fed_id": fed_id})

async def get_fed_info(fed_id: str):
    return await feds_db.find_one({"fed_id": fed_id})

async def get_fed_by_owner(owner_id: int):
    return await feds_db.find_one({"owner_id": owner_id})

async def rename_fed(fed_id: str, new_name: str):
    await feds_db.update_one({"fed_id": fed_id}, {"$set": {"fed_name": new_name}})

async def transfer_fed(fed_id: str, new_owner_id: int):
    await feds_db.update_one({"fed_id": fed_id}, {"$set": {"owner_id": new_owner_id}})

async def add_fed_admin(fed_id: str, user_id: int):
    await feds_db.update_one({"fed_id": fed_id}, {"$addToSet": {"admins": user_id}})

async def remove_fed_admin(fed_id: str, user_id: int):
    await feds_db.update_one({"fed_id": fed_id}, {"$pull": {"admins": user_id}})

async def fban_user(fed_id: str, user_id: int, reason: str):
    await feds_db.update_one(
        {"fed_id": fed_id},
        {"$set": {f"banned_users.{user_id}": {"reason": reason, "time": datetime.now(timezone.utc)}}}
    )

async def unfban_user(fed_id: str, user_id: int):
    await feds_db.update_one(
        {"fed_id": fed_id},
        {"$unset": {f"banned_users.{user_id}": ""}}
    )

async def is_user_fban(fed_id: str, user_id: int):
    fed = await feds_db.find_one({"fed_id": fed_id})
    if not fed:
        return False, None

    # Check current fed
    ban_info = fed.get("banned_users", {}).get(str(user_id))
    if ban_info:
        return True, ban_info.get("reason")

    # Check subscriptions
    for sub_id in fed.get("subs", []):
        is_banned, reason = await is_user_fban(sub_id, user_id)
        if is_banned:
            return True, f"(SubFed: {sub_id}) {reason}"

    return False, None

async def subscribe_fed(fed_id: str, sub_id: str):
    await feds_db.update_one({"fed_id": fed_id}, {"$addToSet": {"subs": sub_id}})

async def unsubscribe_fed(fed_id: str, sub_id: str):
    await feds_db.update_one({"fed_id": fed_id}, {"$pull": {"subs": sub_id}})

async def set_fed_log(fed_id: str, log_channel: int):
    await feds_db.update_one({"fed_id": fed_id}, {"$set": {"log_channel": log_channel}})

async def unset_fed_log(fed_id: str):
    await feds_db.update_one({"fed_id": fed_id}, {"$set": {"log_channel": None}})

async def set_fed_reason(fed_id: str, state: bool):
    await feds_db.update_one({"fed_id": fed_id}, {"$set": {"reason_required": state}})

async def set_fed_notif(fed_id: str, state: bool):
    await feds_db.update_one({"fed_id": fed_id}, {"$set": {"notifications": state}})

async def set_fed_lang(fed_id: str, lang: str):
    await feds_db.update_one({"fed_id": fed_id}, {"$set": {"lang": lang}})

# Chat-Fed
async def join_fed(chat_id: int, fed_id: str):
    await chat_fed_db.update_one(
        {"chat_id": chat_id},
        {"$set": {"fed_id": fed_id}},
        upsert=True
    )

async def leave_fed(chat_id: int):
    await chat_fed_db.delete_one({"chat_id": chat_id})

async def get_chat_fed(chat_id: int):
    res = await chat_fed_db.find_one({"chat_id": chat_id})
    return res.get("fed_id") if res else None

async def set_quiet_fed(chat_id: int, state: bool):
    await chat_fed_db.update_one(
        {"chat_id": chat_id},
        {"$set": {"quiet": state}},
        upsert=True
    )

async def is_quiet_fed(chat_id: int):
    res = await chat_fed_db.find_one({"chat_id": chat_id})
    return res.get("quiet", False) if res else False

async def get_user_feds(user_id: int):
    owned = await feds_db.find({"owner_id": user_id}).to_list(length=100)
    admin_in = await feds_db.find({"admins": user_id}).to_list(length=100)
    return owned + admin_in
