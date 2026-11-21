# Auto quiz for AloneX (Pyrogram)
# Every hour a trivia quiz poll is sent to each group where /quizon was used.

import asyncio
import html
import random

import aiohttp
import AloneX
from pyrogram import filters, enums
from pyrogram.enums import ChatMemberStatus, PollType
from pyrogram.types import Message

from AloneX import pbot as app, prefix_cmds, LOGGER, database, init_aiohttp_session

__module__ = "𝐐ᴜɪᴢ🧠"

__help__ = """
**Auto Quiz 🧠**

Sends a trivia quiz every hour in the group.

❂ `/quizon` – Enable auto quiz in this group (admins).
❂ `/quizoff` – Disable auto quiz in this group (admins).
"""

QUIZ_API = "https://opentdb.com/api.php?amount=1&type=multiple"
GAP_BETWEEN_CHATS = 5          # seconds between two groups, so the quiz API and Telegram are not flooded
HOUR = 3600

COLL = database["quiz_settings"]
_loop_task = None


async def is_admin(message: Message, user_id: int) -> bool:
    try:
        member = await app.get_chat_member(message.chat.id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


async def fetch_question():
    """One random multiple-choice question from opentdb.com, or None."""
    if AloneX.aiohttpsession is None or AloneX.aiohttpsession.closed:
        await init_aiohttp_session()
    try:
        async with AloneX.aiohttpsession.get(QUIZ_API, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status != 200:
                return None
            data = await r.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("response_code") != 0 or not data.get("results"):
        return None
    return data["results"][0]


async def send_quiz(chat_id: int):
    q = await fetch_question()
    if not q:
        return
    question = html.unescape(q["question"])
    correct = html.unescape(q["correct_answer"])[:100]          # Telegram: option max 100 chars
    wrong = [html.unescape(x)[:100] for x in q["incorrect_answers"]]

    options = wrong + [correct]
    random.shuffle(options)
    try:
        await app.send_poll(
            chat_id=chat_id,
            question=f"🧠 AUTO QUIZ\n\n{question}"[:300],       # Telegram: question max 300 chars
            options=options,
            type=PollType.QUIZ,
            correct_option_id=options.index(correct),
        )
    except Exception as e:
        LOGGER.error(f"[quiz] could not send to {chat_id}: {type(e).__name__}: {e}")


async def _quiz_loop():
    await asyncio.sleep(15)
    while True:
        try:
            chats = [doc["chat_id"] async for doc in COLL.find({"quiz": True})]
            for chat_id in chats:
                await send_quiz(chat_id)
                await asyncio.sleep(GAP_BETWEEN_CHATS)
            await asyncio.sleep(HOUR if chats else 60)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            LOGGER.error(f"[quiz] loop error: {type(e).__name__}: {e}")
            await asyncio.sleep(60)


def _ensure_loop():
    """Start the loop once. It is started by /quizon, and again by any group message after a restart."""
    global _loop_task
    if _loop_task is None or _loop_task.done():
        _loop_task = asyncio.create_task(_quiz_loop())


@app.on_message(filters.command("quizon", prefixes=prefix_cmds) & filters.group)
async def quiz_on(client, message: Message):
    if not message.from_user or not await is_admin(message, message.from_user.id):
        return await message.reply_text("❗ Admins only.")
    await COLL.update_one({"chat_id": message.chat.id}, {"$set": {"quiz": True}}, upsert=True)
    _ensure_loop()
    await message.reply_text("✅ Auto Quiz ENABLED in this group")


@app.on_message(filters.command("quizoff", prefixes=prefix_cmds) & filters.group)
async def quiz_off(client, message: Message):
    if not message.from_user or not await is_admin(message, message.from_user.id):
        return await message.reply_text("❗ Admins only.")
    await COLL.update_one({"chat_id": message.chat.id}, {"$set": {"quiz": False}}, upsert=True)
    await message.reply_text("❌ Auto Quiz DISABLED in this group")


@app.on_message(filters.group & ~filters.bot, group=999)
async def resume_quiz_loop(client, message: Message):
    # after a restart the loop is not running yet; any group message starts it again (cheap no-op later)
    _ensure_loop()
