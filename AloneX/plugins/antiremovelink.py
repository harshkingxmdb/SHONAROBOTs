import asyncio
import re
import logging
from pyrogram import filters, enums
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ChatMemberStatus, ButtonStyle
from AloneX import pbot, font, prefix_cmds
from AloneX.db.antiremovelink_db import is_antilink_enabled, set_antilink_status
from AloneX.helpers.decorator import protected_ids

LOGGER = logging.getLogger(__name__)

__module__ = "𝐀ɴ𝐓ɪ-𝐋ɪ𝐍𝐊🔗"

__help__ = """
*Anti-Link Module* 🔗

• `/antilink` — Toggle anti-link feature.

*Note:* When enabled, the bot will delete all links sent in the group by EVERYONE (Including Admins And Owner Users Link Deleted).
Only the bot itself is exempt.
"""

# More aggressive regex for links
URL_PATTERN = re.compile(r"(https?://|www\.)[^\s]+", re.IGNORECASE)
TELEGRAM_PATTERN = re.compile(r"(t\.me|telegram\.me|telegram\.dog)/[^\s]+", re.IGNORECASE)

async def is_user_admin(chat_id: int, user_id: int):
    if user_id in protected_ids:
        return True
    try:
        member = await pbot.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except:
        return False

async def get_antilink_keyboard(chat_id: int):
    enabled = await is_antilink_enabled(chat_id)
    text = "🟢 Anti-Link: ON" if enabled else "🔴 Anti-Link: OFF"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            font(text),
            callback_data="antilink_toggle",
            style=ButtonStyle.SUCCESS if enabled else ButtonStyle.DANGER
        )
    ]])

@pbot.on_message(filters.command("antilink", prefix_cmds) & filters.group)
async def antilink_cmd(_, message: Message):
    if not message.from_user:
        if message.sender_chat and message.sender_chat.id == message.chat.id:
            pass
        else:
            return

    if not await is_user_admin(message.chat.id, message.from_user.id if message.from_user else 0):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    enabled = await is_antilink_enabled(message.chat.id)
    status = "Enabled" if enabled else "Disabled"
    await message.reply_text(
        font(f"🔗 <b>Anti-Link Status:</b> {status}\n\nClick the button below to toggle."),
        reply_markup=await get_antilink_keyboard(message.chat.id),
        parse_mode=enums.ParseMode.HTML
    )

@pbot.on_callback_query(filters.regex(r"^antilink_toggle$"))
async def antilink_toggle_cb(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(font("❌ This button is for admins only!"), show_alert=True)

    enabled = await is_antilink_enabled(chat_id)
    new_state = not enabled
    await set_antilink_status(chat_id, new_state)

    status = "Enabled" if new_state else "Disabled"
    await query.message.edit_text(
        font(f"🔗 <b>Anti-Link Status:</b> {status}\n\nClick the button below to toggle."),
        reply_markup=await get_antilink_keyboard(chat_id),
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer(font(f"Anti-Link {'Enabled' if new_state else 'Disabled'}"))

@pbot.on_message(filters.group & ~filters.service, group=-1001)
async def antilink_handler(client, message: Message):
    chat_id = message.chat.id

    if not await is_antilink_enabled(chat_id):
        return

    # Exempt ONLY the bot itself
    if message.from_user and message.from_user.is_self:
        return

    has_link = False

    # 1. Check entities
    entities = message.entities or message.caption_entities
    if entities:
        for entity in entities:
            if entity.type in [enums.MessageEntityType.URL, enums.MessageEntityType.TEXT_LINK]:
                has_link = True
                break

    # 2. Check reply_markup (buttons)
    if not has_link and message.reply_markup:
        for row in message.reply_markup.inline_keyboard:
            for button in row:
                if button.url:
                    has_link = True
                    break
            if has_link: break

    # 3. Regex fallback
    if not has_link:
        content = message.text or message.caption
        if content:
            if re.search(URL_PATTERN, content) or re.search(TELEGRAM_PATTERN, content):
                has_link = True

    if has_link:
        try:
            await message.delete()
            from pyrogram import StopPropagation
            raise StopPropagation
        except StopPropagation:
            raise
        except Exception as e:
            LOGGER.error(f"Failed to delete link in {chat_id}: {e}")
