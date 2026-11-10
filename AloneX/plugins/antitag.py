import logging
from pyrogram import filters, enums
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ChatMemberStatus, ButtonStyle
from AloneX import pbot, font, prefix_cmds
from AloneX.db.antitag_db import get_antitag_limit, set_antitag_limit
from AloneX.helpers.decorator import protected_ids

LOGGER = logging.getLogger(__name__)

__module__ = "𝐀ɴ𝐓ɪ-𝐓ᴀ𝐆🏷️"

__help__ = """
*Anti-Tag Protection* 🏷️

Automatically deletes messages that contain too many mentions or tags to prevent mass-tagging spam.

• `/antitag` — View status and settings.
• `/antitag <number>` — Set mention limit (e.g., `/antitag 5`).
• `/antitag off` — Disable anti-tag protection.
"""

async def is_user_admin(chat_id: int, user_id: int):
    if user_id in protected_ids:
        return True
    try:
        member = await pbot.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except:
        return False

@pbot.on_message(filters.command("antitag", prefix_cmds) & filters.group)
async def antitag_cmd(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id if message.from_user else 0):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    chat_id = message.chat.id
    if len(message.command) > 1:
        arg = message.command[1].lower()
        if arg in ["off", "disable", "0"]:
            await set_antitag_limit(chat_id, 0)
            return await message.reply_text(font("✅ Anti-Tag protection <b>Disabled</b>."), parse_mode=enums.ParseMode.HTML)

        if arg.isdigit():
            limit = int(arg)
            if limit < 1:
                return await message.reply_text(font("❌ Limit must be at least 1."))
            await set_antitag_limit(chat_id, limit)
            return await message.reply_text(font(f"✅ Anti-Tag limit set to <b>{limit}</b>."), parse_mode=enums.ParseMode.HTML)

    limit = await get_antitag_limit(chat_id)
    status = f"Enabled (Limit: {limit})" if limit > 0 else "Disabled"
    await message.reply_text(
        font(f"🏷️ <b>Anti-Tag Status:</b> {status}\n\nTo change, use: `/antitag <number>` or `/antitag off`"),
        parse_mode=enums.ParseMode.HTML
    )

@pbot.on_message(filters.group & ~filters.service, group=-1002)
async def antitag_handler(client, message: Message):
    chat_id = message.chat.id
    limit = await get_antitag_limit(chat_id)

    if limit <= 0:
        return

    # Count mentions
    count = 0
    entities = message.entities or message.caption_entities
    if entities:
        for entity in entities:
            if entity.type in [enums.MessageEntityType.MENTION, enums.MessageEntityType.TEXT_MENTION]:
                count += 1

    if count > limit:
        # Check if admin (admins are exempt from being deleted by anti-tag usually, or as per requirement)
        if await is_user_admin(chat_id, message.from_user.id if message.from_user else 0):
            return

        try:
            await message.delete()
            from pyrogram import StopPropagation
            raise StopPropagation
        except StopPropagation:
            raise
        except Exception as e:
            LOGGER.error(f"Failed to delete mass-tag in {chat_id}: {e}")
