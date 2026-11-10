import re
import asyncio
import logging
import html
from pyrogram import filters, enums, StopPropagation
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM, Message, CallbackQuery
from pyrogram.enums import ButtonStyle, ChatMemberStatus
from AloneX import pbot, prefix_cmds, BOT_ID, font
from AloneX.db.mediadelete_db import set_media_delete_state, set_media_delete_delay, get_media_delete_settings
from AloneX.helpers.decorator import protected_ids

__module__ = "𝐀ɴ𝐓ɪ-𝐌ᴇᴅɪ𝐀🗑️"
__help__ = """
*Media Auto Delete🗑️* — Automatically deletes photos, videos, stickers & GIFs after a delay

• `/mediadelete` — Toggle media auto-delete or check status.
• `/setmediadelay <time>` — Set delay (e.g., `5m`, `1h`).
• `/mediastatus` — Check current settings.
"""

def parse_time(t: str) -> int:
    t = t.lower().strip()
    m = re.match(r'^(\d+)([smh])$', t)
    if not m:
        return None
    v, u = int(m.group(1)), m.group(2)
    return v * {'s': 1, 'm': 60, 'h': 3600}[u]

def format_time(s: int) -> str:
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s//60}m"
    return f"{s//3600}h"

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

async def get_mediadelete_keyboard(chat_id: int):
    settings = await get_media_delete_settings(chat_id)
    enabled = settings['enabled']
    if enabled:
        text = "🟢 Media Delete: ON"
        style = ButtonStyle.SUCCESS
    else:
        text = "🔴 Media Delete: OFF"
        style = ButtonStyle.DANGER

    return IKM([[IKB(font(text), callback_data="media_toggle", style=style)]])

@pbot.on_message(filters.command("mediadelete", prefixes=prefix_cmds) & filters.group)
async def toggle_media_delete(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    chat_id = message.chat.id
    if len(message.command) > 1:
        arg = message.command[1].lower()
        if arg in ["on", "enable"]:
            await set_media_delete_state(chat_id, True)
            return await message.reply_text(font("✅ Media Auto Delete <b>Enabled</b>."), reply_markup=await get_mediadelete_keyboard(chat_id), parse_mode=enums.ParseMode.HTML)
        elif arg in ["off", "disable"]:
            await set_media_delete_state(chat_id, False)
            return await message.reply_text(font("❌ Media Auto Delete <b>Disabled</b>."), reply_markup=await get_mediadelete_keyboard(chat_id), parse_mode=enums.ParseMode.HTML)

    settings = await get_media_delete_settings(chat_id)
    status = "Enabled" if settings['enabled'] else "Disabled"
    await message.reply_text(
        font(f"🗑️ <b>Media Auto Delete Status:</b> {status}\n\nClick the button below to toggle."),
        reply_markup=await get_mediadelete_keyboard(chat_id),
        parse_mode=enums.ParseMode.HTML
    )

@pbot.on_callback_query(filters.regex(r"^media_toggle$"))
async def media_toggle_cb(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(font("❌ This button is for admins only!"), show_alert=True)

    settings = await get_media_delete_settings(chat_id)
    new_state = not settings['enabled']
    await set_media_delete_state(chat_id, new_state)

    status = "Enabled" if new_state else "Disabled"
    await query.message.edit_text(
        font(f"🗑️ <b>Media Auto Delete Status:</b> {status}\n\nClick the button below to toggle."),
        reply_markup=await get_mediadelete_keyboard(chat_id),
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer(font(f"Media Auto Delete {'Enabled' if new_state else 'Disabled'}"))

@pbot.on_message(filters.command("setmediadelay", prefixes=prefix_cmds) & filters.group)
async def set_media_delay(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ Admin privilege required!"))

    if len(message.command) < 2:
        return await message.reply_text(font("✋ Provide a delay. Example: `/setmediadelay 5m` (5 mins), `/setmediadelay 1h` (1 hour)."))

    delay = parse_time(message.command[1])
    if delay is None or delay < 5 or delay > 86400:
        return await message.reply_text(font("❌ Invalid time format. Use values between 5s and 24h."))

    await set_media_delete_delay(message.chat.id, delay)
    await message.reply_text(f"✨ {font('<b>Media Auto Delete delay set to:</b>')} <code>{format_time(delay)}</code>", parse_mode=enums.ParseMode.HTML)

@pbot.on_message(filters.command("mediastatus", prefixes=prefix_cmds) & filters.group)
async def media_status(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ Admin privilege required!"))

    settings = await get_media_delete_settings(message.chat.id)
    status = "Enabled" if settings['enabled'] else "Disabled"
    await message.reply_text(
        f"📊 {font('<b>Media Auto Delete Status</b>')}\n\n"
        f"• Status: <code>{status}</code>\n"
        f"• Delay: <code>{format_time(settings['delay'])}</code>",
        parse_mode=enums.ParseMode.HTML
    )

@pbot.on_message((filters.photo | filters.video | filters.sticker | filters.animation | filters.document | filters.voice | filters.video_note) & filters.group & ~filters.bot, group=9)
async def media_delete_handler_pyro(client, message: Message):
    settings = await get_media_delete_settings(message.chat.id)
    if not settings['enabled']:
        return

    # Sudo/Owner ignore, but NOT regular admins (common source of "not working" reports)
    if message.from_user and message.from_user.id in protected_ids:
        return

    # Check bot's permission
    try:
        my_member = await client.get_chat_member(message.chat.id, "me")
        if not my_member.privileges.can_delete_messages:
             return
    except Exception:
        return

    asyncio.create_task(delayed_delete_pyro(client, message.chat.id, message.id, settings['delay']))

async def delayed_delete_pyro(client, chat_id, message_id, delay):
    try:
        await asyncio.sleep(delay)
        await client.delete_messages(chat_id, message_id)
    except Exception:
        pass
