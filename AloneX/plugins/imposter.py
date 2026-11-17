# Imposter / Pretender detector
# Tells the group when a member changes their username, first name or last name.
# One self-contained file: database helpers are included, text replies only (no photo).

import html
import logging
from collections import OrderedDict

from pyrogram import enums, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import Message

from AloneX import database, pbot, prefix_cmds

__module__ = "𝐈ᴍᴘᴏsᴛᴇʀ🕵️"
__help__ = """
*𝐈ᴍᴘᴏsᴛᴇʀ🕵️* — Detect members who change their name or username

• `/imposter enable` — Turn the detector ON in this group.
• `/imposter disable` — Turn the detector OFF in this group.
• `/imposter` — Show usage and the current status.

*Behavior:*
When a member changes their username, first name or last name, the bot posts a short text alert showing the old and the new value.
Only group admins can change the setting.
"""

LOGGER = logging.getLogger(__name__)

# ------------------------------------------------------------------ database ----
_CHATS = database["imposter_chats"]   # {_id: chat_id}                     -> chats where it is ON
_USERS = database["imposter_users"]   # {_id: user_id, username, first_name, last_name}

_enabled_chats: set = set()
_enabled_loaded = False

_USER_CACHE: "OrderedDict[int, tuple]" = OrderedDict()   # bounded, so RAM stays small on Heroku
_USER_CACHE_MAX = 30000


async def _load_enabled() -> None:
    """Load the ON-chats once; after that every message is answered from memory."""
    global _enabled_loaded
    if _enabled_loaded:
        return
    try:
        async for doc in _CHATS.find({}, {"_id": 1}):
            _enabled_chats.add(doc["_id"])
        _enabled_loaded = True
    except Exception as e:  # try again on the next message
        LOGGER.warning(f"[Imposter] could not load enabled chats: {e}")


async def imposter_is_on(chat_id: int) -> bool:
    await _load_enabled()
    return chat_id in _enabled_chats


async def imposter_on(chat_id: int) -> bool:
    """Enable. Returns True if it was already enabled."""
    await _load_enabled()
    if chat_id in _enabled_chats:
        return True
    await _CHATS.update_one({"_id": chat_id}, {"$set": {"_id": chat_id}}, upsert=True)
    _enabled_chats.add(chat_id)
    return False


async def imposter_off(chat_id: int) -> bool:
    """Disable. Returns True if it was enabled before."""
    await _load_enabled()
    if chat_id not in _enabled_chats:
        return False
    await _CHATS.delete_one({"_id": chat_id})
    _enabled_chats.discard(chat_id)
    return True


def _snapshot(user) -> tuple:
    """(username, first_name, last_name) with '' normalised to None."""
    return (user.username or None, user.first_name or None, user.last_name or None)


def _remember(user_id: int, data: tuple) -> None:
    _USER_CACHE[user_id] = data
    _USER_CACHE.move_to_end(user_id)
    while len(_USER_CACHE) > _USER_CACHE_MAX:
        _USER_CACHE.popitem(last=False)


async def _get_saved(user_id: int):
    if user_id in _USER_CACHE:
        _USER_CACHE.move_to_end(user_id)
        return _USER_CACHE[user_id]
    doc = await _USERS.find_one({"_id": user_id})
    if not doc:
        return None
    data = (doc.get("username") or None, doc.get("first_name") or None, doc.get("last_name") or None)
    _remember(user_id, data)
    return data


async def _save(user_id: int, data: tuple) -> None:
    _remember(user_id, data)
    await _USERS.update_one(
        {"_id": user_id},
        {"$set": {"username": data[0], "first_name": data[1], "last_name": data[2]}},
        upsert=True,
    )


# ------------------------------------------------------------------- helpers ----
def _e(value) -> str:
    return html.escape(str(value))


async def _is_admin(message: Message) -> bool:
    # anonymous admin (posts as the group itself)
    if message.sender_chat and message.sender_chat.id == message.chat.id:
        return True
    if not message.from_user:
        return False

    from AloneX.helpers.decorator import protected_ids, user_admin_cache

    user_id = message.from_user.id
    if user_id in protected_ids:
        return True
    key = (message.chat.id, user_id, "a")
    cached = user_admin_cache.get(key)
    if cached is not None:
        return cached
    try:
        member = await pbot.get_chat_member(message.chat.id, user_id)
        result = member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
        user_admin_cache[key] = result
        return result
    except Exception:
        return False


# ------------------------------------------------------------------- watcher ----
@pbot.on_message(filters.group & ~filters.bot & ~filters.via_bot, group=69)
async def chk_usr(_, message: Message):
    try:
        if message.sender_chat or not message.from_user:
            return
        if not await imposter_is_on(message.chat.id):
            return

        user = message.from_user
        now = _snapshot(user)
        before = await _get_saved(user.id)

        if before is None:                       # first time we see this user: just remember
            await _save(user.id, now)
            return
        if before == now:                        # nothing changed (the normal case)
            return

        old_username, old_first, old_last = before
        new_username, new_first, new_last = now

        name = _e(user.first_name or "User")
        msg = (
            "<b>🔓 ᴘʀᴇᴛᴇɴᴅᴇʀ ᴅᴇᴛᴇᴄᴛᴇᴅ 🔓</b>\n"
            "━━━━━━━━━━━━━━━\n"
            f'<b>🍊 ɴᴀᴍᴇ</b> : <a href="tg://user?id={user.id}">{name}</a>\n'
            f"<b>🍅 ᴜsᴇʀ ɪᴅ</b> : {user.id}\n"
            "━━━━━━━━━━━━━━━\n\n"
        )

        if old_username != new_username:
            bef = f"@{_e(old_username)}" if old_username else "NO USERNAME"
            aft = f"@{_e(new_username)}" if new_username else "NO USERNAME"
            msg += (
                "<b>🐻‍❄️ ᴄʜᴀɴɢᴇᴅ ᴜsᴇʀɴᴀᴍᴇ 🐻‍❄️</b>\n"
                "━━━━━━━━━━━━━━━\n"
                f"<b>🎭 ғʀᴏᴍ</b> : {bef}\n"
                f"<b>🍜 ᴛᴏ</b> : {aft}\n"
                "━━━━━━━━━━━━━━━\n\n"
            )
        if old_first != new_first:
            msg += (
                "<b>🪧 ᴄʜᴀɴɢᴇs ғɪʀsᴛ ɴᴀᴍᴇ 🪧</b>\n"
                "━━━━━━━━━━━━━━━\n"
                f"<b>🔐 ғʀᴏᴍ</b> : {_e(old_first or 'NO FIRST NAME')}\n"
                f"<b>🍓 ᴛᴏ</b> : {_e(new_first or 'NO FIRST NAME')}\n"
                "━━━━━━━━━━━━━━━\n\n"
            )
        if old_last != new_last:
            msg += (
                "<b>🪧 ᴄʜᴀɴɢᴇs ʟᴀsᴛ ɴᴀᴍᴇ 🪧</b>\n"
                "━━━━━━━━━━━━━━━\n"
                f"<b>🚏 ғʀᴏᴍ</b> : {_e(old_last or 'NO LAST NAME')}\n"
                f"<b>🍕 ᴛᴏ</b> : {_e(new_last or 'NO LAST NAME')}\n"
                "━━━━━━━━━━━━━━━\n"
            )

        await _save(user.id, now)                # save first, so a failed reply can never repeat the alert
        await message.reply_text(msg, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        LOGGER.warning(f"[Imposter] watcher error in {getattr(message.chat, 'id', '?')}: {type(e).__name__}: {e}")


# ------------------------------------------------------------------ commands ----
@pbot.on_message(
    filters.command(["imposter", "pretender"], prefixes=prefix_cmds)
    & filters.group
    & ~filters.bot
    & ~filters.via_bot
)
async def set_mataa(_, message: Message):
    if not await _is_admin(message):
        return await message.reply_text("❌ ʏᴏᴜ ᴍᴜsᴛ ʙᴇ ᴀɴ ᴀᴅᴍɪɴ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.")

    chat_id = message.chat.id
    arg = message.command[1].lower() if len(message.command) > 1 else ""

    if arg in ("enable", "on"):
        if await imposter_on(chat_id):
            await message.reply_text("<b>ᴘʀᴇᴛᴇɴᴅᴇʀ ᴍᴏᴅᴇ ɪs ᴀʟʀᴇᴀᴅʏ ᴇɴᴀʙʟᴇᴅ.</b>", parse_mode=enums.ParseMode.HTML)
        else:
            await message.reply_text(
                f"<b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴇɴᴀʙʟᴇᴅ ᴘʀᴇᴛᴇɴᴅᴇʀ ᴍᴏᴅᴇ ғᴏʀ</b> {_e(message.chat.title)}",
                parse_mode=enums.ParseMode.HTML,
            )
    elif arg in ("disable", "off"):
        if await imposter_off(chat_id):
            await message.reply_text(
                f"<b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴅɪsᴀʙʟᴇᴅ ᴘʀᴇᴛᴇɴᴅᴇʀ ᴍᴏᴅᴇ ғᴏʀ</b> {_e(message.chat.title)}",
                parse_mode=enums.ParseMode.HTML,
            )
        else:
            await message.reply_text("<b>ᴘʀᴇᴛᴇɴᴅᴇʀ ᴍᴏᴅᴇ ɪs ᴀʟʀᴇᴀᴅʏ ᴅɪsᴀʙʟᴇᴅ.</b>", parse_mode=enums.ParseMode.HTML)
    else:
        state = "🟢 ON" if await imposter_is_on(chat_id) else "🔴 OFF"
        await message.reply_text(
            "ᴅᴇᴛᴇᴄᴛ ᴘʀᴇᴛᴇɴᴅᴇʀ ᴜsᴇʀs <b>ᴜsᴀɢᴇ:</b> <code>/imposter enable|disable</code>\n"
            f"<b>sᴛᴀᴛᴜs:</b> {state}",
            parse_mode=enums.ParseMode.HTML,
  )
