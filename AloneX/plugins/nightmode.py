import asyncio
import logging
from datetime import datetime, time, timezone, timedelta
from telegram.ext import ContextTypes
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM, Message, CallbackQuery, ChatPermissions as PyroChatPermissions
from pyrogram.enums import ButtonStyle, ChatMemberStatus
from AloneX import app, prefix_cmds, BOT_ID, font, pbot
from AloneX.helpers.decorator import protected_ids
from AloneX.db.nightmode_db import add_nightmode, rm_nightmode, is_nightmode, get_all_nightmode_chats

__module__ = "𝐍ɪɢʜᴛ-𝐌ᴏᴅᴇ🌙"
__help__ = """
*Night Mode🌙*

*Description:*
Automatically closes the group at night (12 AM IST) and reopens it in the morning (6 AM IST) to prevent night spam.

*Commands:*
• `/nightmode` — Toggle Night Mode or check status.
• `/nightmode <close_hour> <open_hour>` — Set custom hours (24h format).
  Example: `/nightmode 23 7` (Close at 11 PM, Open at 7 AM).
"""

IST = timezone(timedelta(hours=5, minutes=30))

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

async def get_nightmode_keyboard(chat_id: int):
    is_enabled = await is_nightmode(chat_id)
    if is_enabled:
        text = "🟢 Night Mode: ON"
        style = ButtonStyle.SUCCESS
    else:
        text = "🔴 Night Mode: OFF"
        style = ButtonStyle.DANGER

    return IKM([[IKB(font(text), callback_data="nm_toggle", style=style)]])

@pbot.on_message(filters.command("nightmode", prefixes=prefix_cmds) & filters.group)
async def nightmode_cmd(_, message: Message):
    if not message.from_user:
        return
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    if len(message.command) == 3:
        try:
            close_h = int(message.command[1])
            open_h = int(message.command[2])
            if not (0 <= close_h <= 23 and 0 <= open_h <= 23):
                return await message.reply_text(font("❌ Hours must be between 0 and 23."))
            if close_h == open_h:
                return await message.reply_text(font("❌ Close and Open hours cannot be the same."))

            await add_nightmode(message.chat.id, close_h, open_h)
            return await message.reply_text(
                font(f"✅ Night Mode Enabled with custom hours!\n\nClose: {close_h}:00 IST\nOpen: {open_h}:00 IST"),
                reply_markup=await get_nightmode_keyboard(message.chat.id),
                parse_mode=enums.ParseMode.HTML
            )
        except ValueError:
            return await message.reply_text(font("❌ Invalid format! Use: /nightmode <close_hour> <open_hour>"))

    is_enabled = await is_nightmode(message.chat.id)
    from AloneX.db.nightmode_db import get_nightmode_data
    data = await get_nightmode_data(message.chat.id)
    close_h = data.get("close_hour", 0) if data else 0
    open_h = data.get("open_hour", 6) if data else 6

    status_text = "Enabled" if is_enabled else "Disabled"
    await message.reply_text(
        font(f"🌙 Night Mode Status: {status_text}\n\nClose Time: {close_h}:00 IST\nOpen Time: {open_h}:00 IST\n\nClick the button below to toggle."),
        reply_markup=await get_nightmode_keyboard(message.chat.id),
        parse_mode=enums.ParseMode.HTML
    )

@pbot.on_callback_query(filters.regex(r"^nm_toggle$"))
async def nm_toggle_callback(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(font("❌ This button is for admins only!"), show_alert=True)

    is_enabled = await is_nightmode(chat_id)
    new_state = not is_enabled
    if new_state:
        await add_nightmode(chat_id)
    else:
        await rm_nightmode(chat_id)

    from AloneX.db.nightmode_db import get_nightmode_data
    data = await get_nightmode_data(chat_id)
    close_h = data.get("close_hour", 0) if data else 0
    open_h = data.get("open_hour", 6) if data else 6

    status_text = "Enabled" if new_state else "Disabled"
    await query.message.edit_text(
        font(f"🌙 Night Mode Status: {status_text}\n\nClose Time: {close_h}:00 IST\nOpen Time: {open_h}:00 IST\n\nClick the button below to toggle."),
        reply_markup=await get_nightmode_keyboard(chat_id),
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer(font(f"Night Mode {'Enabled' if new_state else 'Disabled'}"))

async def night_mode_checker(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(IST)
    current_hour = now.hour

    chats = await get_all_nightmode_chats()
    for chat_data in chats:
        chat_id = chat_data['chat_id']
        close_h = chat_data.get('close_hour', 0)
        open_h = chat_data.get('open_hour', 6)

        try:
            if current_hour == close_h:
                await pbot.set_chat_permissions(
                    chat_id,
                    PyroChatPermissions(can_send_messages=False)
                )
                await pbot.send_message(
                    chat_id,
                    font(f"🌙 Night Mode Active!\nThis group is now closed for the night. See you at {open_h}:00 IST!")
                )
            elif current_hour == open_h:
                await pbot.set_chat_permissions(
                    chat_id,
                    PyroChatPermissions(
                        can_send_messages=True,
                        can_send_photos=True,
                        can_send_videos=True,
                        can_send_audios=True,
                        can_send_documents=True,
                        can_send_video_notes=True,
                        can_send_voice_notes=True,
                        can_send_polls=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True,
                        can_invite_users=True
                    )
                )
                await pbot.send_message(
                    chat_id,
                    font("☀️ Good Morning!\nNight Mode is now over. The group is open for conversation!")
                )
        except Exception as e:
            logging.error(f"Error in Night Mode check for {chat_id}: {e}")

# Initialize the job queue task to run every hour
if app.job_queue:
    app.job_queue.run_repeating(night_mode_checker, interval=3600, first=time(minute=0, tzinfo=IST))
