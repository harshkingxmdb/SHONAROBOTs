import re
import asyncio
import logging
import html
from pyrogram import filters, enums, StopPropagation
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM, Message, CallbackQuery
from pyrogram.enums import ButtonStyle, ChatMemberStatus
from AloneX import pbot, prefix_cmds, BOT_USERNAME, font, LOGS_CHANNEL
from AloneX.db.abuse_db import set_abuse_state, is_abuse_enabled
from AloneX.helpers.decorator import protected_ids
import config

__module__ = "𝐀ɴᴛɪ-𝐀ʙᴜsᴇ🚫"
__help__ = """
*Abuse Filter🚫* — Protect your group from offensive content

• `/abuse` — Toggle abuse filter or check status.

*Main feature:*
Automatically deletes messages containing 18+ or offensive words and notifies admins in the logs.
"""

# List of 18+ or abusive words
BAD_WORDS = [
    # 18+ related words
    "18+", "sex", "porn", "nude", "blowjob", "boobs", "bobs", "condom", "xxx", "adult", "nangi", "randi", 

    # Common gaaliyan & offensive words (Hindi/English)
    "bc", "chutmaarfucker", "maadharpille", "madarchod", "bsdk", "land", "chutiya", "madarchod", "bhenchod", "gaand", "gand", "lund", "ch**d", "g***i",
    "d'esi", "doodh", "gaand", "mulle", "mulla", "laude", ".raid", "pussy", "chuchi", ".replyraid", "maderchodo", "maadharchod", "madharchod", "lundoo", "lodu", "bhains", "chod", "randi", "randa", "randi ka bacha",
    "chut", "desi", "chod", "fuck", "bsdkk", "chodu", "chudd", "chumt", "randii", "randwa", "bsdkk", "fingering", "bhosdiwala", "bhosdike", "mc", "mcchod", "randi ki aulaad", "gand mara", "lund mar", "lauda", "loda",
    "bhosda", "sexchat", "service", "maachuda", "gandmara", "chodu", "chut", "chutiyapa", "chutiye", "chut ke", "chut ke laude", "chut ke bache", "bhosadike",
    
    # Slang variations with stars (to catch censored forms)
    "ch**d", "g***i", "m**ch*d", "b**chod", "b***chod"
]

BAD_PATTERN = re.compile(r"|".join([re.escape(word) for word in BAD_WORDS]), re.IGNORECASE)

async def is_user_admin(chat_id: int, user_id: int):
    from AloneX.helpers.decorator import user_admin_cache
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

async def get_abuse_keyboard(chat_id: int):
    enabled = await is_abuse_enabled(chat_id)
    if enabled:
        text = "🟢 Abuse Filter: ON"
    else:
        text = "🔴 Abuse Filter: OFF"

    return IKM([[IKB(font(text), callback_data="abuse_toggle", style=ButtonStyle.SUCCESS if enabled else ButtonStyle.DANGER)]])

@pbot.on_message(filters.command("abuse", prefixes=prefix_cmds) & filters.group)
async def abuse_cmd(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    if len(message.command) > 1:
        arg = message.command[1].lower()
        if arg == "on":
            await set_abuse_state(message.chat.id, True)
            return await message.reply_text(font("✅ Abuse Filter <b>Enabled</b>."), reply_markup=await get_abuse_keyboard(message.chat.id), parse_mode=enums.ParseMode.HTML)
        elif arg == "off":
            await set_abuse_state(message.chat.id, False)
            return await message.reply_text(font("❌ Abuse Filter <b>Disabled</b>."), reply_markup=await get_abuse_keyboard(message.chat.id), parse_mode=enums.ParseMode.HTML)

    enabled = await is_abuse_enabled(message.chat.id)
    status = "Enabled" if enabled else "Disabled"
    await message.reply_text(
        font(f"🚫 <b>Abuse Filter Status:</b> {status}\n\nClick the button below to toggle."),
        reply_markup=await get_abuse_keyboard(message.chat.id),
        parse_mode=enums.ParseMode.HTML
    )

@pbot.on_callback_query(filters.regex(r"^abuse_toggle$"))
async def abuse_toggle_cb(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(font("❌ This button is for admins only!"), show_alert=True)

    enabled = await is_abuse_enabled(chat_id)
    new_state = not enabled
    await set_abuse_state(chat_id, new_state)

    status = "Enabled" if new_state else "Disabled"
    await query.message.edit_text(
        font(f"🚫 <b>Abuse Filter Status:</b> {status}\n\nClick the button below to toggle."),
        reply_markup=await get_abuse_keyboard(chat_id),
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer(font(f"Abuse Filter {'Enabled' if new_state else 'Disabled'}"))

@pbot.on_message((filters.text | filters.caption) & filters.group & ~filters.bot, group=8)
async def filter_bad_words_pyro(client, message: Message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    if not await is_abuse_enabled(chat_id):
        return

    text = message.text or message.caption or ""
    if not BAD_PATTERN.search(text):
        return

    user_id = message.from_user.id

    # Check if admin (skip moderation)
    if await is_user_admin(chat_id, user_id):
        return

    try:
        await message.delete()
    except:
        return

    # Send warning in group
    mention = f"<a href='tg://user?id={user_id}'>{html.escape(message.from_user.first_name)}</a>"
    warn_text = f"⚠️ {mention}, {font('<b>18+ or abusive messages are not allowed here!</b>')}"

    try:
        warn = await message.reply_text(warn_text, parse_mode=enums.ParseMode.HTML)
        asyncio.create_task(auto_delete_msg(warn))
    except:
        pass

    # Logging
    if config.LOGS_CHANNEL:
        username = f"@{message.from_user.username}" if message.from_user.username else "No username"
        log_text = f"""
<b>🚫 Abuse Filter: Message Deleted</b>

<b>👤 User:</b> {mention}
<b>🆔 User ID:</b> <code>{user_id}</code>
<b>🔗 Username:</b> {html.escape(username)}
<b>🏷️ Group:</b> <code>{html.escape(message.chat.title)}</code>
<b>🆔 Chat ID:</b> <code>{chat_id}</code>
<b>💬 Message:</b> <code>{html.escape(text)}</code>

<b>🤖 Bot:</b> {BOT_USERNAME}
"""
        try:
            await client.send_message(config.LOGS_CHANNEL, log_text, parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            logging.error(f"[ABUSE LOG ERROR] {e}")

    raise StopPropagation

async def auto_delete_msg(msg):
    await asyncio.sleep(10)
    try:
        await msg.delete()
    except:
        pass
