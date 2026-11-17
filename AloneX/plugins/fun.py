# Fun percentage commands: /cutie /horny /hot /sexy /gay /lesbian /boob /cock
# Reply to someone to rate them, or use the command alone to rate yourself.

import html
import logging
import random
import time

from pyrogram import enums, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from AloneX import SUPPORT_CHAT, pbot, prefix_cmds

__module__ = "𝐅ᴜɴ🎉"
__help__ = """
*𝐅ᴜɴ🎉* — Random percentage fun commands

• `/cutie` — How cute are you?
• `/hot` — How hot are you?
• `/sexy` — How sexy are you?
• `/horny` — How horny are you?
• `/gay` — How gay are you?
• `/lesbian` — How lesbian are you?
• `/boob` — Random boob size.
• `/cock` — Random cock size.

*Usage:*
Send a command alone to rate yourself, or reply to someone's message to rate that person. The result is random, just for fun.
"""

LOGGER = logging.getLogger(__name__)

_support = SUPPORT_CHAT if str(SUPPORT_CHAT).startswith("http") else f"https://t.me/{str(SUPPORT_CHAT).lstrip('@')}"
BUTTON = InlineKeyboardMarkup([[InlineKeyboardButton("ꜱᴜᴘᴘᴏʀᴛ", url=_support)]])

# Media links come from the original plugin. Replace them with your own GIF / mp4 links,
# or set a value to "" to send that command as text only. If a link is dead the bot answers with text.
MEDIA = {
    "cutie": "https://graph.org/file/24375c6e54609c0e4621c.mp4",
    "horny": "https://graph.org/file/eaa834a1cbfad29bd1fe4.mp4",
    "hot": "https://graph.org/file/745ba3ff07c1270958588.mp4",
    "sexy": "https://graph.org/file/58da22eb737af2f8963e6.mp4",
    "gay": "https://graph.org/file/850290f1f974c5421ce54.mp4",
    "lesbian": "https://graph.org/file/ff258085cf31f5385db8a.mp4",
    "boob": "https://i.gifer.com/8ZUg.gif",
    "cock": "https://telegra.ph/file/423414459345bf18310f5.gif",
}

TEMPLATES = {
    "cutie": "🍑 {mention} ɪꜱ {percent}% ᴄᴜᴛᴇ ʙᴀʙʏ🥀",
    "horny": "🔥 {mention} ɪꜱ {percent}% ʜᴏʀɴʏ!",
    "hot": "🔥 {mention} ɪꜱ {percent}% ʜᴏᴛ!",
    "sexy": "💋 {mention} ɪꜱ {percent}% ꜱᴇxʏ!",
    "gay": "🍷 {mention} ɪꜱ {percent}% ɢᴀʏ!",
    "lesbian": "💜 {mention} ɪꜱ {percent}% ʟᴇꜱʙɪᴀɴ!",
    "boob": "🍒 {mention}ꜱ ʙᴏᴏʙ ꜱɪᴢᴇ ɪꜱ {percent}!",
    "cock": "🍆 {mention} ᴄᴏᴄᴋ ꜱɪᴢᴇ ɪꜱ {percent}ᴄᴍ!",
}

_COOLDOWN = 3          # seconds between two uses by the same person in the same chat
_last_use: dict = {}


def get_user_mention(message: Message) -> str:
    """HTML mention of the replied-to user, else of the sender. Names are escaped."""
    reply = message.reply_to_message
    user = (reply.from_user if reply and reply.from_user else None) or message.from_user
    if user:
        return f'<a href="tg://user?id={user.id}">{html.escape(user.first_name or "User")}</a>'
    chat = (reply.sender_chat if reply and reply.sender_chat else None) or message.sender_chat
    return html.escape((chat.title if chat else None) or "User")


def get_reply_id(message: Message) -> int:
    """Answer under the replied-to message, otherwise under the command itself (keeps forum topics right)."""
    return message.reply_to_message.id if message.reply_to_message else message.id


def _too_fast(message: Message) -> bool:
    who = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    key = (message.chat.id, who)
    now = time.time()
    if now - _last_use.get(key, 0) < _COOLDOWN:
        return True
    _last_use[key] = now
    if len(_last_use) > 5000:                      # keep memory small
        for k in [k for k, t in _last_use.items() if now - t > 60]:
            _last_use.pop(k, None)
    return False


@pbot.on_message(filters.command(list(TEMPLATES), prefixes=prefix_cmds) & ~filters.bot & ~filters.via_bot)
async def handle_percentage_command(_, message: Message):
    command = message.command[0].lower()
    if command not in TEMPLATES or _too_fast(message):
        return

    text = TEMPLATES[command].format(mention=get_user_mention(message), percent=random.randint(1, 100))
    media_url = MEDIA.get(command)
    chat_id, reply_id = message.chat.id, get_reply_id(message)
    kwargs = dict(
        caption=text,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=BUTTON,
        reply_to_message_id=reply_id,
    )

    if media_url:
        for sender in (pbot.send_animation, pbot.send_document):
            try:
                return await sender(chat_id, media_url, **kwargs)
            except Exception as e:
                LOGGER.warning(f"[Fun] {command}: {sender.__name__} failed: {type(e).__name__}: {e}")

    # no media, or the link is dead / refused: the answer must still arrive
    try:
        await pbot.send_message(
            chat_id,
            text,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=BUTTON,
            reply_to_message_id=reply_id,
        )
    except Exception as e:
        LOGGER.warning(f"[Fun] {command}: could not answer: {type(e).__name__}: {e}")
