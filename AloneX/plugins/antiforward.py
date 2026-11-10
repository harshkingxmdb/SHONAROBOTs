import logging
from pyrogram import filters, enums, StopPropagation
from pyrogram.errors import MessageDeleteForbidden
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ChatMemberStatus, ButtonStyle
from AloneX import pbot, font, prefix_cmds
from AloneX.db.antiforward_db import is_antiforward_enabled, set_antiforward_status
from AloneX.helpers.decorator import protected_ids, only_groups
from AloneX.db.approval_db import is_user_approved

LOGGER = logging.getLogger(__name__)

__module__ = "𝐀ɴᴛɪ-𝐅ᴏʀᴡᴀʀᴅ⏩"

__help__ = """
*Anti-Forward Module* ⏩

Prevents users from sending forwarded messages from any source.

• `/antiforward` — Toggle anti-forward protection.

*Note:* When enabled, the bot will delete all forwarded messages sent in the group by EVERYONE (Including Admins And Owner).
Only the bot itself is exempt.
"""

async def is_user_admin(chat_id: int, user_id: int):
    if user_id in protected_ids:
        return True
    try:
        member = await pbot.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except:
        return False

async def get_antiforward_keyboard(chat_id: int):
    enabled = await is_antiforward_enabled(chat_id)
    text = "🟢 Anti-Forward: ON" if enabled else "🔴 Anti-Forward: OFF"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            font(text),
            callback_data="antiforward_toggle",
            style=ButtonStyle.SUCCESS if enabled else ButtonStyle.DANGER
        )
    ]])

@pbot.on_message(filters.command("antiforward", prefix_cmds) & filters.group)
async def antiforward_cmd(_, message: Message):
    if not message.from_user:
        return

    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    enabled = await is_antiforward_enabled(message.chat.id)
    status = "Enabled" if enabled else "Disabled"
    await message.reply_text(
        font(f"⏩ <b>Anti-Forward Status:</b> {status}\n\nClick the button below to toggle."),
        reply_markup=await get_antiforward_keyboard(message.chat.id),
        parse_mode=enums.ParseMode.HTML
    )

@pbot.on_callback_query(filters.regex(r"^antiforward_toggle$"))
async def antiforward_toggle_cb(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(font("❌ This button is for admins only!"), show_alert=True)

    enabled = await is_antiforward_enabled(chat_id)
    new_state = not enabled
    await set_antiforward_status(chat_id, new_state)

    status = "Enabled" if new_state else "Disabled"
    await query.message.edit_text(
        font(f"⏩ <b>Anti-Forward Status:</b> {status}\n\nClick the button below to toggle."),
        reply_markup=await get_antiforward_keyboard(chat_id),
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer(font(f"Anti-Forward {'Enabled' if new_state else 'Disabled'}"))

@pbot.on_message(filters.group & filters.forwarded, group=-1004)
async def antiforward_handler(client, message: Message):
    chat_id = message.chat.id

    if not await is_antiforward_enabled(chat_id):
        return

    # Exempt ONLY the bot itself to prevent self-deletion loops
    if message.from_user and message.from_user.is_self:
        return

    try:
        await message.delete()
        raise StopPropagation
    except MessageDeleteForbidden:
        pass
    except StopPropagation:
        raise
    except Exception as e:
        LOGGER.error(f"Failed to delete forwarded message in {chat_id}: {e}")
