import logging
import asyncio
import re
from datetime import datetime, timedelta
from pyrogram import filters, enums
from pyrogram.types import Message, ChatPermissions, ChatPrivileges, InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM, CallbackQuery
from pyrogram.enums import ChatMemberStatus, ButtonStyle
from AloneX import pbot, font, prefix_cmds
from AloneX.db.joinmute_db import get_joinmute_duration, set_joinmute_duration
from AloneX.helpers.decorator import protected_ids, only_groups

LOGGER = logging.getLogger(__name__)

__module__ = "𝐉ᴏɪɴ-𝐌ᴜᴛᴇ🤐"

__help__ = """
*Join-Mute Module* 🤐

Automatically mutes new members who join the group for a specific duration. This helps prevent "join-and-spam" attacks.

• `/joinmute <time>` — Set the mute duration for new members (e.g., `10m`, `1h`, `1d`).
• `/joinmute` — Enable / Disable auto-mute for new members.

*Example:* `/joinmute 15m`
"""

def parse_time(time_str: str) -> int:
    if not time_str:
        return 0
    time_str = time_str.lower().strip()
    match = re.match(r"(\d+)([smhd])", time_str)
    if not match:
        return 0
    value, unit = int(match.group(1)), match.group(2)
    if unit == 's': return value
    if unit == 'm': return value * 60
    if unit == 'h': return value * 3600
    if unit == 'd': return value * 86400
    return 0

def format_time(seconds: int) -> str:
    if seconds < 60: return f"{seconds}s"
    if seconds < 3600: return f"{seconds // 60}m"
    if seconds < 86400: return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"

async def get_joinmute_keyboard(chat_id: int):
    duration = await get_joinmute_duration(chat_id)
    if duration > 0:
        text = "🟢 Join-Mute: ON"
        style = ButtonStyle.SUCCESS
    else:
        text = "🔴 Join-Mute: OFF"
        style = ButtonStyle.DANGER

    return IKM([[IKB(font(text), callback_data="joinmute_toggle", style=style)]])

async def is_user_admin(chat_id: int, user_id: int):
    if user_id in protected_ids:
        return True
    try:
        member = await pbot.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except:
        return False

@pbot.on_message(filters.command("joinmute", prefix_cmds) & filters.group)
async def joinmute_cmd(_, message: Message):
    if not message.from_user:
        return

    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    if len(message.command) < 2:
        duration = await get_joinmute_duration(message.chat.id)
        status = f"Enabled ({format_time(duration)})" if duration > 0 else "Disabled"
        return await message.reply_text(
            font(f"🤐 <b>Join-Mute Status:</b> {status}\n\nUsage: `/joinmute <time|off>` (e.g., 10m, 1h)"),
            reply_markup=await get_joinmute_keyboard(message.chat.id)
        )

    arg = message.command[1].lower()
    if arg == "off":
        await set_joinmute_duration(message.chat.id, 0)
        return await message.reply_text(font("✅ Join-Mute has been disabled."))

    duration = parse_time(arg)
    if duration <= 0:
        return await message.reply_text(font("❌ Invalid time format. Use e.g., 10m, 1h, 1d."))

    if duration < 30:
        return await message.reply_text(font("❌ Minimum duration is 30 seconds."))

    await set_joinmute_duration(message.chat.id, duration)
    await message.reply_text(font(f"✅ New members will be muted for <b>{format_time(duration)}</b> upon joining."))

@pbot.on_message(filters.new_chat_members, group=-1003)
async def joinmute_handler(client, message: Message):
    chat_id = message.chat.id
    duration = await get_joinmute_duration(chat_id)

    if duration <= 0:
        return

    # Check if bot is admin
    try:
        me = await client.get_chat_member(chat_id, "me")
        if not me.privileges or not me.privileges.can_restrict_members:
            return
    except:
        return

    for user in message.new_chat_members:
        if user.id in protected_ids or user.is_bot:
            continue

        try:
            until_date = datetime.utcnow() + timedelta(seconds=duration)
            await client.restrict_chat_member(
                chat_id,
                user.id,
                ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            # Notify
            await message.reply_text(
                font(f"🔇 {user.mention} has been automatically muted for <b>{format_time(duration)}</b>. This is a security measure for new members."),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            LOGGER.error(f"Failed to joinmute {user.id} in {chat_id}: {e}")

@pbot.on_callback_query(filters.regex(r"^joinmute_toggle$"))
async def joinmute_toggle_callback(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(font("❌ This button is for admins only!"), show_alert=True)

    duration = await get_joinmute_duration(chat_id)
    if duration > 0:
        new_duration = 0
    else:
        new_duration = 900 # Default 15 minutes

    await set_joinmute_duration(chat_id, new_duration)

    status = f"Enabled ({format_time(new_duration)})" if new_duration > 0 else "Disabled"
    await query.message.edit_text(
          (f"🤐 <b>𝐉ᴏɪɴ-𝐌ᴜᴛᴇ 𝐒ᴛᴀᴛᴜꜱ:</b> {status}\n\n𝐔ꜱᴀɢᴇ: `/joinmute <time|off>` (e.g., 10m, 1h)"),
        reply_markup=await get_joinmute_keyboard(chat_id)
    )
    await query.answer(font(f"Join-Mute {'Enabled' if new_duration > 0 else 'Disabled'}"))
