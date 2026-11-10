from AloneX import database as db

rules_col = db["rules"]

async def get_rules(chat_id: int) -> str:
    data = await rules_col.find_one({"chat_id": chat_id})
    if data and "rules" in data:
        return data["rules"].replace('\\n', '\n')
    return None

async def get_rules_keyboard(chat_id: int):
    data = await rules_col.find_one({"chat_id": chat_id})
    if data and "keyboard" in data:
        return data["keyboard"]
    return None

async def set_rules(chat_id: int, rules: str, keyboard=None):
    formatted_rules = rules.replace('\n', '\\n')
    update_data = {"rules": formatted_rules}
    if keyboard is not None:
        update_data["keyboard"] = keyboard
    await rules_col.update_one(
        {"chat_id": chat_id}, 
        {"$set": update_data}, 
        upsert=True
    )

async def reset_rules(chat_id: int):
    await rules_col.delete_one({"chat_id": chat_id})

async def get_rules_button(chat_id: int) -> str:
    data = await rules_col.find_one({"chat_id": chat_id})
    return data["button"] if data and "button" in data else None

async def set_rules_button(chat_id: int, button: str):
    await rules_col.update_one(
        {"chat_id": chat_id}, {"$set": {"button": button}}, upsert=True
    )

async def reset_rules_button(chat_id: int):
    await rules_col.update_one({"chat_id": chat_id}, {"$unset": {"button": ""}})

async def get_private_rules(chat_id: int) -> bool:
    data = await rules_col.find_one({"chat_id": chat_id})
    return data.get("private", False) if data else False

async def set_private_rules(chat_id: int, value: bool):
    await rules_col.update_one(
        {"chat_id": chat_id}, {"$set": {"private": value}}, upsert=True
    )

async def count_rules_chats() -> int:
    return await rules_col.count_documents({"rules": {"$exists": True, "$ne": None}})
