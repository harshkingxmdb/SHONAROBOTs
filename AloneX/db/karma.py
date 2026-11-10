from AloneX import database as db 
import os

karma_settings = db["karma_settings"]
karma_data = db["karma_data"]


async def get_karma_status(chat_id: int) -> bool:
    """Check if karma system is enabled for a chat."""
    doc = await karma_settings.find_one({"chat_id": chat_id})
    if doc:
        return doc.get("enabled", False)
    return False


async def set_karma_status(chat_id: int, enabled: bool) -> None:
    """Enable or disable karma system for a chat."""
    await karma_settings.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": enabled}},
        upsert=True
    )


async def get_user_karma(chat_id: int, user_id: int) -> int:
    """Get karma points for a user in a chat."""
    doc = await karma_data.find_one({"chat_id": chat_id, "user_id": user_id})
    if doc:
        return doc.get("karma", 0)
    return 0


async def change_karma(chat_id: int, user_id: int, delta: int) -> int:
    """
    Change karma for a user by delta amount.
    Returns the new karma value.
    """
    result = await karma_data.find_one_and_update(
        {"chat_id": chat_id, "user_id": user_id},
        {"$inc": {"karma": delta}},
        upsert=True,
        return_document=True
    )
    return result.get("karma", delta)


async def get_leaderboard(chat_id: int, limit: int = 10) -> list[tuple[int, int]]:
    """
    Get karma leaderboard for a chat.
    Returns list of tuples: [(user_id, karma), ...]
    """
    cursor = karma_data.find({"chat_id": chat_id}).sort("karma", -1).limit(limit)
    leaderboard = []
    async for doc in cursor:
        leaderboard.append((doc["user_id"], doc["karma"]))
    return leaderboard


async def reset_karma(chat_id: int, user_id: int = None) -> None:
    """Reset karma for a user or entire chat."""
    if user_id:
        await karma_data.delete_one({"chat_id": chat_id, "user_id": user_id})
    else:
        await karma_data.delete_many({"chat_id": chat_id})
