import re
import logging
from pyrogram import filters, enums, StopPropagation
from pyrogram.types import Message, ChatAdministratorRights, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ChatMemberStatus, ButtonStyle
from AloneX import pbot, BOT_ID, font, prefix_cmds
from AloneX.helpers.decorator import protected_ids, is_sudo_user_db, only_groups, get_member_cached, UltraCache
from AloneX.db.banall_db import set_lockdown, is_lockdown, is_banall_enabled, set_banall_status

LOGGER = logging.getLogger(__name__)

# Deduplication cache to prevent double messages
DEDUP_CACHE = UltraCache(m=2000, t=10)

def is_processed(message: Message) -> bool:
    key = (message.chat.id, message.id)
    if DEDUP_CACHE.get(key):
        return True
    DEDUP_CACHE[key] = True
    return False

__module__ = "𝐀ɴᴛɪ-𝐁ᴀɴᴀʟʟ🚫"

__help__ = """
❂ *Available commands for Banall:*

The Banall module is a security "trap" and lockdown system.

*Commands:*
- `/antibanall`: Check and toggle the Banall security trap status.
- `/gcfree` or `/gc free`: Lift the group lockdown and restore messaging (Owner/Sudo/Creator only).
- `banall` or `ban all`: (Trigger) When triggered by a non-exempt user, the bot will demote ALL administrators in the chat (except the Owner, Sudo users, and itself) and lock the group.

*Note:*
- The banall trigger message is immediately deleted.
- During lockdown, only the Owner, Sudo users, and the Group Creator can speak. All other messages are deleted.
- Bot Owner, Sudo users, and the Chat Creator are exempt from demotion.
"""

async def is_user_exempt(chat_id: int, user_id: int) -> bool:
    if user_id == BOT_ID or user_id in protected_ids:
        return True
    if await is_sudo_user_db(user_id):
        return True

    try:
        member = await get_member_cached(pbot, chat_id, user_id)
        if member.status == ChatMemberStatus.OWNER:
            return True
    except Exception:
        pass
    return False

async def is_exempt(message: Message) -> bool:
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None

    if user_id:
        if await is_user_exempt(chat_id, user_id):
            return True

    if message.sender_chat and message.sender_chat.id == chat_id:
        return True

    return False

# Build regex for triggers
PREFIX_PATTERN = "[" + re.escape("".join(prefix_cmds)) + "]"
# TRIGGER_RE: Matches (prefix)?(banall|ban all)(@bot)? case-insensitive
TRIGGER_RE = rf"^\s*{PREFIX_PATTERN}?\s*(banall|ban\s+all)(?:@\w+)?\s*$"
# GCFREE_RE: Matches (prefix)?(gcfree|gc free)(@bot)? case-insensitive
GCFREE_RE = rf"^\s*{PREFIX_PATTERN}?\s*(gcfree|gc\s+free)(?:@\w+)?\s*$"

@pbot.on_message(filters.regex(TRIGGER_RE, re.IGNORECASE) & filters.group & ~filters.bot, group=-1101)
@only_groups
async def banall_trigger_handler(client, message: Message):
    if is_processed(message):
        raise StopPropagation

    chat_id = message.chat.id

    if not await is_banall_enabled(chat_id):
        return

    if await is_exempt(message):
        return

    user_id = message.from_user.id if message.from_user else None
    if user_id:
        try:
            member = await get_member_cached(client, chat_id, user_id)
            if member.status != ChatMemberStatus.ADMINISTRATOR:
                return
        except Exception:
            return
    else:
        return

    # Trap triggered!
    try:
        await message.delete()
    except Exception as e:
        LOGGER.warning(f"Failed to delete banall trigger in {chat_id}: {e}")

    await set_lockdown(chat_id, True)

    await message.reply_text(
        font("🚨 <b>Security Trap Triggered!</b>\n\n"
             "An unauthorized user attempted to use a restricted command.\n"
             "The group is now in <b>LOCKDOWN</b> mode.\n"
             "All administrators are being demoted."),
        parse_mode=enums.ParseMode.HTML
    )

    try:
        await client.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
    except Exception as e:
        LOGGER.warning(f"Failed to set lockdown permissions in {chat_id}: {e}")

    LOGGER.info(f"Banall trap triggered in {chat_id} by {user_id}. Demoting admins...")

    async for member in client.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
        if await is_user_exempt(chat_id, member.user.id):
            continue

        try:
            await client.promote_chat_member(
                chat_id,
                member.user.id,
                privileges=ChatAdministratorRights(
                    can_manage_chat=False,
                    can_post_messages=False,
                    can_edit_messages=False,
                    can_delete_messages=False,
                    can_post_stories=False,
                    can_edit_stories=False,
                    can_delete_stories=False,
                    can_restrict_members=False,
                    can_promote_members=False,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False,
                    can_manage_video_chats=False,
                    is_anonymous=False
                )
            )
        except Exception as e:
            LOGGER.debug(f"Failed to demote {member.user.id} in {chat_id}: {e}")

    try:
        await client.promote_chat_member(
            chat_id,
            BOT_ID,
            privileges=ChatAdministratorRights(
                can_manage_chat=False,
                can_post_messages=False,
                can_edit_messages=False,
                can_delete_messages=False,
                can_post_stories=False,
                can_edit_stories=False,
                can_delete_stories=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
                can_manage_video_chats=False,
                is_anonymous=False
            )
        )
        LOGGER.info(f"Bot successfully demoted itself in {chat_id}")
    except Exception as e:
        LOGGER.warning(f"Failed to demote bot in {chat_id}: {e}")

    raise StopPropagation

@pbot.on_message(filters.regex(GCFREE_RE, re.IGNORECASE) & filters.group & ~filters.bot, group=-1101)
@only_groups
async def gcfree_handler(client, message: Message):
    chat_id = message.chat.id
    if not await is_banall_enabled(chat_id):
        return
    if is_processed(message):
        raise StopPropagation

    if not await is_exempt(message):
        return

    await set_lockdown(chat_id, False)

    try:
        await client.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=True))
    except Exception as e:
        LOGGER.warning(f"Failed to lift lockdown permissions in {chat_id}: {e}")

    await message.reply_text(
        font("✅ <b>Lockdown Lifted!</b>\n\n"
             "The group lockdown has been deactivated.\n"
             "Regular members can now send messages again."),
        parse_mode=enums.ParseMode.HTML
    )
    u_id = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else "Anonymous")
    LOGGER.info(f"Lockdown lifted in {chat_id} by {u_id}")
    raise StopPropagation

@pbot.on_message(filters.group & ~filters.bot, group=-1102)
async def lockdown_enforcement_handler(client, message: Message):
    chat_id = message.chat.id

    if not await is_banall_enabled(chat_id):
        return

    if not await is_lockdown(chat_id):
        return

    # Check exemption
    if await is_exempt(message):
        return

    # Not exempt, delete!
    try:
        await message.delete()
    except:
        pass
    raise StopPropagation

async def get_antibanall_keyboard(chat_id: int):
    enabled = await is_banall_enabled(chat_id)
    if enabled:
        text = "🟢 Anti-Banall: ON"
        style = ButtonStyle.SUCCESS
    else:
        text = "🔴 Anti-Banall: OFF"
        style = ButtonStyle.DANGER

    return InlineKeyboardMarkup([[InlineKeyboardButton(font(text), callback_data="banall_toggle", style=style)]])

@pbot.on_message(filters.command("antibanall", prefixes=prefix_cmds) & filters.group)
async def antibanall_cmd(_, message: Message):
    if not message.from_user:
        return

    # Using is_user_exempt for admin check as only authorized users should toggle security features
    if not await is_user_exempt(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ You must be an authorized admin to use this command."))

    enabled = await is_banall_enabled(message.chat.id)
    status = "Enabled" if enabled else "Disabled"

    await message.reply_text(
        font(f"🛡️ <b>Banall Security Status:</b> {status}\n\n"
             "When enabled, the security trap will trigger on unauthorized use of 'banall'."),
        reply_markup=await get_antibanall_keyboard(message.chat.id),
        parse_mode=enums.ParseMode.HTML
    )

@pbot.on_callback_query(filters.regex(r"^banall_toggle$"))
async def banall_toggle_callback(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_exempt(chat_id, user_id):
        return await query.answer(font("❌ This button is for authorized admins only!"), show_alert=True)

    enabled = await is_banall_enabled(chat_id)
    new_state = not enabled
    await set_banall_status(chat_id, new_state)

    status_text = "Enabled" if new_state else "Disabled"
    await query.message.edit_text(
        font(f"🛡️ <b>Banall Security Status:</b> {status_text}\n\n"
             "When enabled, the security trap will trigger on unauthorized use of 'banall'."),
        reply_markup=await get_antibanall_keyboard(chat_id),
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer(font(f"Banall Security {'Enabled' if new_state else 'Disabled'}"))
