import asyncio
import logging
import re
import time

import aiohttp
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM, Message, CallbackQuery
from pyrogram.enums import ButtonStyle, ChatMemberStatus
from AloneX import pbot, prefix_cmds, font, init_aiohttp_session
import AloneX
from AloneX.helpers.decorator import protected_ids
from AloneX.db.chatbot import add_chat, remove_chat, CHAT_IDS
import config

__module__ = "𝐂ʜᴀᴛ-𝐁ᴏᴛ🤖"
__help__ = """
❂ *Chatbot Module* — A human-like AI chatbot that talks to you.

*Commands:*
❂ /chatbot — Toggle chatbot in the current chat.

*Notes:*
- In groups, the bot responds only when you REPLY to its message or @mention it.
- Works with a GROQ_API_KEY; if Groq fails it uses GEMINI_API_KEY.
- In private, the bot responds to all messages (must be enabled via /chatbot).
- Supports Hinglish and has a friendly, human-like persona.
"""

async def is_user_admin(chat_id: int, user_id: int):
    from AloneX.helpers.decorator import user_admin_cache
    if chat_id == user_id: # Private chat
        return True
    if user_id in protected_ids:
        return True
    k = (chat_id, user_id, 'a')
    res = user_admin_cache.get(k)
    if res is not None:
        return res
    try:
        member = await pbot.get_chat_member(chat_id, user_id)
        res = member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
        user_admin_cache[k] = res
        return res
    except:
        return False

async def get_chatbot_keyboard(chat_id: int):
    enabled = chat_id in CHAT_IDS
    if enabled:
        text = "🟢 Chatbot: ON"
        style = ButtonStyle.SUCCESS
    else:
        text = "🔴 Chatbot: OFF"
        style = ButtonStyle.DANGER

    return IKM([[IKB(font(text), callback_data="chatbot_toggle", style=style)]])

@pbot.on_message(filters.command("chatbot", prefixes=prefix_cmds))
async def chatbot_toggle_cmd(_, message: Message):
    if not message.from_user:
        return
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    enabled = message.chat.id in CHAT_IDS
    status = "Enabled" if enabled else "Disabled"

    await message.reply_text(
        font(f"🤖 **Chatbot Status:** {status}\n\nWhen enabled, I will respond to mentions and replies with a human-like personality."),
        reply_markup=await get_chatbot_keyboard(message.chat.id)
    )

@pbot.on_callback_query(filters.regex(r"^chatbot_toggle$"))
async def chatbot_toggle_callback(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(font("❌ This button is for admins only!"), show_alert=True)

    enabled = chat_id in CHAT_IDS
    if enabled:
        await remove_chat(chat_id)
        if chat_id in CHAT_IDS:
            CHAT_IDS.remove(chat_id)
        new_state = False
    else:
        await add_chat(chat_id)
        if chat_id not in CHAT_IDS:
            CHAT_IDS.append(chat_id)
        new_state = True

    status_text = "Enabled" if new_state else "Disabled"
    await query.message.edit_text(
        font(f"🤖 **Chatbot Status:** {status_text}\n\nWhen enabled, I will respond to mentions and replies with a human-like personality."),
        reply_markup=await get_chatbot_keyboard(chat_id)
    )
    await query.answer(font(f"Chatbot {'Enabled' if new_state else 'Disabled'}"))

CHATBOT_PROMPT = """
Your name is ShonaX. You are a human-like, friendly, and cool AI chatbot.
You talk like a real person, not like a formal AI assistant.
You can speak in English and Hinglish (mixed Hindi and English).
Be helpful, sometimes witty, and very natural in conversation.
Keep your responses relatively short and engaging.
If someone asks who made you, say you were created by AloneX Team.
Use emojis occasionally to feel more human.
"""

LOGGER = logging.getLogger(__name__)

from contextlib import suppress


def suppress_errors():
    return suppress(Exception)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS = ("llama-3.3-70b-versatile", "llama-3.1-8b-instant")
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODELS = (
    "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash",
    "gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-2.5-flash",
)

_groq_dead_until = 0.0        # a rejected key is not retried on every message
_gemini_dead_until = 0.0
_gemini_model = None          # the model that worked last
_groq_model = GROQ_MODELS[0]
_notice_sent: dict = {}       # chat_id -> time of the last "AI is not working" notice


def _short(body, limit: int = 160) -> str:
    """Error body -> one safe line for the log (never contains the key)."""
    return re.sub(r"\s+", " ", str(body)).strip()[:limit]


async def _groq_reply(text: str):
    global _groq_dead_until, _groq_model
    key = getattr(config, "GROQ_API_KEY", "")
    if not key or time.time() < _groq_dead_until:
        return None

    models = [_groq_model] + [m for m in GROQ_MODELS if m != _groq_model]
    headers = {"Authorization": f"Bearer {key}"}
    for model in models:
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": CHATBOT_PROMPT},
                {"role": "user", "content": text},
            ],
        }
        try:
            async with AloneX.aiohttpsession.post(
                GROQ_URL, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=40)
            ) as response:
                if response.status == 200:
                    res_json = await response.json()
                    content = ((res_json.get("choices") or [{}])[0].get("message") or {}).get("content")
                    if content:
                        _groq_model = model
                        return content
                    return None
                body = await response.text()
                if response.status in (401, 403):             # key rejected -> stop asking Groq for 10 minutes
                    _groq_dead_until = time.time() + 600
                    LOGGER.error(f"[Chatbot] Groq rejected GROQ_API_KEY (HTTP {response.status}): {_short(body)}")
                    return None
                if response.status == 429:
                    _groq_dead_until = time.time() + 30
                    LOGGER.warning("[Chatbot] Groq rate limit (HTTP 429)")
                    return None
                LOGGER.warning(f"[Chatbot] Groq {model} HTTP {response.status}: {_short(body)}")
                continue                                      # e.g. model removed -> try the next one
        except Exception as e:
            LOGGER.warning(f"[Chatbot] Groq request failed: {type(e).__name__}")
            return None
    return None


async def _gemini_reply(text: str):
    global _gemini_dead_until, _gemini_model
    key = getattr(config, "GEMINI_API_KEY", "")
    if not key or time.time() < _gemini_dead_until:
        return None

    models = list(GEMINI_MODELS)
    if _gemini_model in models:
        models.remove(_gemini_model)
        models.insert(0, _gemini_model)

    payload = {
        "systemInstruction": {"parts": [{"text": CHATBOT_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": text}]}],
    }
    headers = {"Content-Type": "application/json", "x-goog-api-key": key}
    refused = []
    for model in models:
        try:
            async with AloneX.aiohttpsession.post(
                f"{GEMINI_BASE}/models/{model}:generateContent",
                headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=40),
            ) as response:
                status = response.status
                body = await response.json(content_type=None) if status == 200 else await response.text()
        except Exception as e:
            LOGGER.warning(f"[Chatbot] Gemini request failed: {type(e).__name__}")
            return None

        if status == 200:
            parts = (((body.get("candidates") or [{}])[0]).get("content") or {}).get("parts") or []
            reply = "".join(p.get("text", "") for p in parts).strip()
            if reply:
                _gemini_model = model
                return reply
            return None
        if status == 404:                      # model does not exist (any more)
            continue
        if status in (400, 401, 403):          # key refused, maybe only by THIS model -> try the next one
            refused.append((status, _short(body)))
            continue
        if status == 429:
            _gemini_dead_until = time.time() + 30
            LOGGER.warning("[Chatbot] Gemini rate limit (HTTP 429)")
            return None
        LOGGER.warning(f"[Chatbot] Gemini {model} HTTP {status}: {_short(body)}")
        return None

    if refused:                                # no model accepted the key
        _gemini_dead_until = time.time() + 600
        LOGGER.error(f"[Chatbot] Gemini rejected GEMINI_API_KEY (HTTP {refused[-1][0]}): {refused[-1][1]}")
    return None


async def get_chatbot_reply(text: str):
    if AloneX.aiohttpsession is None:
        await init_aiohttp_session()

    for backend in (_groq_reply, _gemini_reply):
        try:
            reply = await backend(text)
        except Exception as e:
            LOGGER.warning(f"[Chatbot] {backend.__name__} error: {type(e).__name__}")
            reply = None
        if reply:
            return reply
    return None

@pbot.on_message(
    (filters.text | filters.caption)
    & ~filters.bot
    & ~filters.command(["chatbot", "AloneX", "gpt", "groq", "google", "gemini"])
    , group=10
)
async def chatbot_handler(_, message: Message):
    chat_id = message.chat.id

    if chat_id not in CHAT_IDS:
        return

    # In groups, check if it's a mention or reply to bot
    if message.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
        is_reply_to_bot = (
            message.reply_to_message
            and message.reply_to_message.from_user
            and message.reply_to_message.from_user.is_self
        )
        is_mentioned = message.mentioned

        if not (is_reply_to_bot or is_mentioned):
            return

    input_text = message.text or message.caption
    if not input_text:
        return

    # Remove bot mention from text if present
    if f"@{pbot.me.username}" in input_text:
        input_text = input_text.replace(f"@{pbot.me.username}", "").strip()

    await pbot.send_chat_action(chat_id, enums.ChatAction.TYPING)
    reply = await get_chatbot_reply(input_text)

    if reply:
        return await message.reply_text(reply)

    # No AI answered. Tell the chat (at most once every 10 minutes) instead of staying silent.
    now = time.time()
    if now - _notice_sent.get(chat_id, 0) > 600:
        _notice_sent[chat_id] = now
        with suppress_errors():
            await message.reply_text(
                "⚠️ ᴀɪ ɪs ɴᴏᴛ ᴡᴏʀᴋɪɴɢ ʀɪɢʜᴛ ɴᴏᴡ. ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ɴᴇᴇᴅs ᴛᴏ ᴄʜᴇᴄᴋ ᴛʜᴇ ɢʀᴏǫ / ɢᴇᴍɪɴɪ ᴀᴘɪ ᴋᴇʏ."
            )
