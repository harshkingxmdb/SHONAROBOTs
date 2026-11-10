from AloneX import database as db

approval_collection = db.approvals
CHAT_IDS = []  # Add this

async def approve_user(chat_id: int, user_id: int):
    await approval_collection.update_one(
        {"chat_id": chat_id},
        {"$addToSet": {"approved": user_id}},
        upsert=True
    )

async def unapprove_user(chat_id: int, user_id: int):
    await approval_collection.update_one(
        {"chat_id": chat_id},
        {"$pull": {"approved": user_id}}
    )

async def is_user_approved(chat_id: int, user_id: int) -> bool:
    data = await approval_collection.find_one({"chat_id": chat_id})
    return data and user_id in data.get("approved", [])

async def get_all_approved_users(chat_id: int):
    data = await approval_collection.find_one({"chat_id": chat_id})
    return data.get("approved", []) if data else []

async def remove_all_approved_users(chat_id: int):
    await approval_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"approved": []}}
    )

async def count_chats() -> int:
    """Count chats with approved users"""
    return len(await approval_collection.distinct("chat_id"))

async def initialize_chats():
    """Initialize approval chats"""
    try:
        chats = await approval_collection.distinct("chat_id")
        CHAT_IDS.extend(chats)
        print(f"Initialized {len(chats)} approval chats")
    except Exception as e:
        print(f"Error initializing approval chats: {e}")

# ✅ Ye adb (aggregation DB query) ka code hai:
async def approvals_summary() -> str:
    """Return summary like '7528 approved, across 1107 chats'"""
    try:
        # count total unique chats
        chat_count = len(await approval_collection.distinct("chat_id"))

        # aggregate to count total approved users
        pipeline = [
            {"$project": {"count": {"$size": {"$ifNull": ["$approved", []]}}}},
            {"$group": {"_id": None, "total": {"$sum": "$count"}}}
        ]
        result = await approval_collection.aggregate(pipeline).to_list(length=1)

        total_approved = result[0]["total"] if result else 0
        return f"{total_approved} approved, across {chat_count} chats."
    except Exception as e:
        return f"Error fetching approvals summary: {e}"
