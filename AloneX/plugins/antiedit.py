import asyncio
import html
import re
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM, Message, CallbackQuery
from pyrogram.enums import ButtonStyle, ChatMemberStatus
from cachetools import TTLCache

from AloneX import pbot, font, prefix_cmds, LOGS_CHANNEL
from AloneX.db.antiedit_db import get_antiedit, set_antiedit, save_msg_content, get_msg_content
from AloneX.helpers.decorator import protected_ids

# TTL of 2 hours, max size of 10k messages
CACHE = TTLCache(maxsize=10000, ttl=7200)

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

async def get_antiedit_keyboard(chat_id: int):
    enabled = await get_antiedit(chat_id)
    if enabled:
        text = "🟢 Anti-Edit: ON"
    else:
        text = "🔴 Anti-Edit: OFF"

    return IKM([[IKB(font(text), callback_data="antiedit_toggle", style=ButtonStyle.SUCCESS if enabled else ButtonStyle.DANGER)]])

@pbot.on_message(filters.command("antiedit", prefixes=prefix_cmds) & filters.group)
async def antiedit_cmd(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    if len(message.command) > 1:
        arg = message.command[1].lower()
        if arg == "on":
            await set_antiedit(message.chat.id, True)
            return await message.reply_text(font("✅ Anti-Edit <b>Enabled</b>."), reply_markup=await get_antiedit_keyboard(message.chat.id), parse_mode=enums.ParseMode.HTML)
        elif arg == "off":
            await set_antiedit(message.chat.id, False)
            return await message.reply_text(font("❌ Anti-Edit <b>Disabled</b>."), reply_markup=await get_antiedit_keyboard(message.chat.id), parse_mode=enums.ParseMode.HTML)

    enabled = await get_antiedit(message.chat.id)
    status = "Enabled" if enabled else "Disabled"
    await message.reply_text(
        font(f"✒️ <b>Anti-Edit Status:</b> {status}\n\nClick the button below to toggle."),
        reply_markup=await get_antiedit_keyboard(message.chat.id),
        parse_mode=enums.ParseMode.HTML
    )

@pbot.on_callback_query(filters.regex(r"^antiedit_toggle$"))
async def antiedit_toggle_cb(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(font("❌ This button is for admins only!"), show_alert=True)

    enabled = await get_antiedit(chat_id)
    new_state = not enabled
    await set_antiedit(chat_id, new_state)

    status = "Enabled" if new_state else "Disabled"
    await query.message.edit_text(
        font(f"✒️ <b>Anti-Edit Status:</b> {status}\n\nClick the button below to toggle."),
        reply_markup=await get_antiedit_keyboard(chat_id),
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer(font(f"Anti-Edit {'Enabled' if new_state else 'Disabled'}"))

@pbot.on_message(filters.group & ~filters.bot, group=-100)
async def save_message_pyro(_, message: Message):
    if not message.from_user:
        return

    chat_id = message.chat.id

    # Ignore commands
    if message.text and any(message.text.startswith(p) for p in prefix_cmds):
        return

    content = message.text or message.caption
    if content:
        # Local cache
        CACHE[(chat_id, message.id)] = content
        # Persistent storage
        await save_msg_content(chat_id, message.id, content)

@pbot.on_edited_message(filters.group & ~filters.bot, group=-101)
async def anti_edit_handler_pyro(client, message: Message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await get_antiedit(chat_id):
        return

    # Ignore sudo users and admins
    if await is_user_admin(chat_id, user_id):
        return

    key = (chat_id, message.id)
    old = CACHE.get(key)

    # If not in local cache, try fetching from DB
    if not old:
        old = await get_msg_content(chat_id, message.id)

    new = message.text or message.caption

    # reaction edit or no content change ignore
    if not old or not new or old.strip() == new.strip():
        return

    try:
        await message.delete()
    except:
        return

    mention = f"<a href='tg://user?id={user_id}'>{html.escape(message.from_user.first_name)}</a>"

    # Escape content to prevent HTML injection
    old_text = html.escape(old)
    new_text = html.escape(new)

    report = await client.send_message(
        chat_id,
        f"🚫 <b>Edited Message Deleted</b>\n"
        f"👤 <b>User:</b> {mention}\n"
        f"📌 <b>Original:</b> {old_text}\n"
        f"✏️ <b>Edited:</b> {new_text}",
        parse_mode=enums.ParseMode.HTML
    )

    # Update cache and DB to handle subsequent edits
    CACHE[key] = new
    await save_msg_content(chat_id, message.id, new)

    await asyncio.sleep(60)
    try:
        await report.delete()
    except:
        pass

__module__ = "𝐀ɴᴛɪ-𝐄ᴅɪᴛ🖋"
__help__ = """
*Anti-Edit🖋 — Protect your group from ghost edits*

Automatically deletes edited messages and shows the original content.

• `/antiedit` — Toggle anti-edit or check status.
"""
