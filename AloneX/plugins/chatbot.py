import asyncio
import logging
import re
import time
from collections import deque, defaultdict
from contextlib import suppress
from io import BytesIO

import aiohttp
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM, Message, CallbackQuery
from pyrogram.enums import ButtonStyle, ChatMemberStatus
from AloneX import pbot, prefix_cmds, font, init_aiohttp_session
import AloneX
from AloneX.helpers.decorator import protected_ids
from AloneX.db.chatbot import add_chat, remove_chat, CHAT_IDS

__module__ = "𝐂ʜᴀᴛ-𝐁ᴏᴛ🤖"
__help__ = """
❂ *Chatbot Module* — A human-like AI chatbot that talks to you.

*Commands:*
❂ /chatbot — Toggle chatbot in the current chat.

*Notes:*
- In groups, the bot responds only when you REPLY to its message or @mention it.
- In private, the bot responds to all messages (must be enabled via /chatbot).
- The bot remembers the last 30 messages of the chat, so it knows who said what.
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
The person talking to you right now is {user_name}.
"""

LOGGER = logging.getLogger(__name__)

# ── Chatbot API (url + key live here, in this file) ──────────────────────────
API_URL = "https://chatbot.riteshyt.in/api/chat"
API_KEY = "ritesh-8179b3a5da99f300be2d50e1e9789729"

MAX_RETRIES = 3
HISTORY_SIZE = 30      # last N messages kept per chat, sent to the AI as context
HISTORY_CLIP = 600     # one long message must not blow up the whole prompt

# chat_id -> last 30 messages ("[Name]: text"), so the AI knows who said what
chat_histories = defaultdict(lambda: deque(maxlen=HISTORY_SIZE))
_notice_sent: dict = {}   # chat_id -> time of the last "AI is not working" notice

# "/start", "!help", ".ping" ... -> a command for some other module, not a chat message
_CMD_RE = re.compile(r"^[" + re.escape("".join(prefix_cmds)) + r"][A-Za-z]")

_EXT = {
    "python": ".py", "py": ".py", "javascript": ".js", "js": ".js", "html": ".html",
    "css": ".css", "json": ".json", "cpp": ".cpp", "c++": ".cpp", "bash": ".sh", "sh": ".sh",
}


def suppress_errors():
    return suppress(Exception)


def _clip(text: str, limit: int = HISTORY_CLIP) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "…"


async def get_chatbot_reply(user_name: str, text: str, history):
    """Send system prompt + recent chat + the new message to the API. Returns the reply or None."""
    if AloneX.aiohttpsession is None or AloneX.aiohttpsession.closed:
        await init_aiohttp_session()

    prompt = CHATBOT_PROMPT.strip().replace("{user_name}", user_name)
    history_str = "\n".join(history)
    formatted_prompt = (
        f"System: {prompt}\n\n"
        f"Recent Chat Context:\n{history_str}\n\n"
        f"User: {text}\nAssistant:"
    )
    payload = {"prompt": formatted_prompt}
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    for attempt in range(MAX_RETRIES):
        try:
            async with AloneX.aiohttpsession.post(
                API_URL, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                status = response.status
                if status == 200:
                    data = await response.json(content_type=None)
                    reply = data.get("response") if isinstance(data, dict) else None
                    if reply and "503" not in reply and "系统通知" not in reply:
                        return reply
                    LOGGER.warning("[Chatbot] API returned an empty/error reply")
                elif status in (500, 502, 503, 429):
                    LOGGER.warning(f"[Chatbot] API HTTP {status}, retry {attempt + 1}/{MAX_RETRIES}")
                else:
                    body = re.sub(r"\s+", " ", await response.text()).strip()[:160]
                    LOGGER.error(f"[Chatbot] API HTTP {status}: {body}")
                    return None            # key rejected / bad request -> retrying will not help
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            LOGGER.warning(f"[Chatbot] API request failed ({type(e).__name__}), retry {attempt + 1}/{MAX_RETRIES}")

        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(2)
    return None


def _split_long_code(reply: str):
    """Code blocks longer than 5 lines are taken out of the text and returned as files."""
    files = []

    def _swap(match):
        lang, code = match.group(1), match.group(2).strip()
        if len(code.split("\n")) <= 5:
            return match.group(0)
        name = f"code_snippet_{len(files) + 1}{_EXT.get(lang.lower(), f'.{lang}' if lang else '.txt')}"
        file_obj = BytesIO(code.encode("utf-8"))
        file_obj.name = name
        files.append(file_obj)
        return f"**[Long code block sent as file: {name}]**"

    text = re.sub(r"```([\w+#.-]*)\n(.*?)```", _swap, reply, flags=re.DOTALL)
    return text, files


@pbot.on_message((filters.text | filters.caption) & ~filters.bot, group=10)
async def chatbot_handler(_, message: Message):
    chat_id = message.chat.id

    if chat_id not in CHAT_IDS or not message.from_user:
        return

    input_text = (message.text or message.caption or "").strip()
    if not input_text or _CMD_RE.match(input_text):
        return

    # Remove bot mention from text if present
    if pbot.me and pbot.me.username:
        input_text = input_text.replace(f"@{pbot.me.username}", "").strip()
        if not input_text:
            return

    user_name = message.from_user.first_name or "Unknown"

    # Context = what was said BEFORE this message (this message is sent separately as "User:")
    history = list(chat_histories[chat_id])
    # Always log the message, even when the bot does not answer it
    chat_histories[chat_id].append(f"[{user_name}]: {_clip(input_text)}")

    # In groups, answer only to a reply to the bot or a mention
    if message.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
        is_reply_to_bot = (
            message.reply_to_message
            and message.reply_to_message.from_user
            and message.reply_to_message.from_user.is_self
        )
        if not (is_reply_to_bot or message.mentioned):
            return

    await pbot.send_chat_action(chat_id, enums.ChatAction.TYPING)
    reply = await get_chatbot_reply(user_name, input_text, history)

    if not reply:
        # No AI answered. Tell the chat (at most once every 10 minutes) instead of staying silent.
        now = time.time()
        if now - _notice_sent.get(chat_id, 0) > 600:
            _notice_sent[chat_id] = now
            with suppress_errors():
                await message.reply_text(
                    "⚠️ ᴀɪ ɪs ɴᴏᴛ ᴡᴏʀᴋɪɴɢ ʀɪɢʜᴛ ɴᴏᴡ. ᴛʜᴇ ʙᴏᴛ ᴏᴡɴᴇʀ ɴᴇᴇᴅs ᴛᴏ ᴄʜᴇᴄᴋ ᴛʜᴇ ᴄʜᴀᴛʙᴏᴛ ᴀᴘɪ."
                )
        return

    chat_histories[chat_id].append(f"[Assistant]: {_clip(reply)}")

    try:
        text, files = _split_long_code(reply)
        text = text.strip()
        for i in range(0, len(text), 4000):          # Telegram limit is 4096 chars
            await message.reply_text(text[i:i + 4000])
        for f in files:
            await message.reply_document(document=f)
    except Exception as e:
        LOGGER.error(f"[Chatbot] failed to send reply: {type(e).__name__}: {e}")
