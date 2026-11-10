__module__ = "𝐀ᴘᴘʀᴏᴠᴀʟs✅"

__help__ = """
*Approvals✅*

*Description:*  
Approve trusted users/channels to bypass locks, blocklists, and anti-flood actions.

*User Commands:*  
❂ `/approval` – Check if a user/channel is approved

*Admin Commands:*  
❂ `/approve` – Approve a user/channel (reply to message)
❂ `/free` – Free a user/channel (reply to message)
❂ `/unapprove` – Remove approval from a user/channel (reply to message)
❂ `/unfree` – Remove Free from a user/channel (reply to message)
❂ `/approved` – Show all approved users/channels  
❂ `/unapproveall` – Remove approval from all users/channels (with confirmation)

*Note:* To approve/unapprove channels, you must reply to a message sent by that channel.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from AloneX import DEV_LIST, font
from AloneX.helpers.decorator import Command, admin_check, only_groups, Callbacks, group_owner_only
from AloneX.helpers.utils import extract_user, async_cache
from AloneX.db.approval_db import (
    approve_user,
    unapprove_user,
    is_user_approved,
    get_all_approved_users,
    remove_all_approved_users,
)
import html

@async_cache(max_size=5000, max_idle_time=600)
async def is_user_approved_cached(chat_id: int, user_id: int):
    return await is_user_approved(chat_id, user_id)

@async_cache(max_size=1000, max_idle_time=300)
async def get_all_approved_users_cached(chat_id: int):
    return await get_all_approved_users(chat_id)

async def get_user_mention(bot, chat_id, user_id):
    try:
        if user_id < 0:
            chat = await bot.get_chat(user_id)
            if hasattr(chat, 'title') and chat.title:
                title = html.escape(chat.title)
                return f"<b>{title}</b>"
            elif hasattr(chat, 'username') and chat.username:
                return f"<b>@{chat.username}</b>"
            return f"<code>{user_id}</code>"
        else:
            member = await bot.get_chat_member(chat_id, user_id)
            name = html.escape(member.user.first_name)
            return f"<a href='tg://user?id={user_id}'>{name}</a>"
    except Exception as e:
        return f"<code>{user_id}</code>"

@Command(['approve', 'free'])
@admin_check("can_change_info", protect_target=False)
@only_groups
async def approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    bot = context.bot
    if message.reply_to_message and message.reply_to_message.sender_chat:
        sender_chat = message.reply_to_message.sender_chat
        user_id = sender_chat.id
        try:
            user_link = await get_user_mention(bot, message.chat.id, user_id)
            if await is_user_approved_cached(message.chat.id, user_id):
                return await message.reply_text(
                    f"ℹ️ {user_link} is already approved!",
                    parse_mode=constants.ParseMode.HTML,
                    disable_web_page_preview=True
                )
            await approve_user(message.chat.id, user_id)
            is_user_approved_cached.clear_cache()
            await message.reply_text(
                f"✅ Channel {user_link} has been approved in <b>{html.escape(message.chat.title)}</b>!\n"
                f"🛡️ They will now be ignored by automated admin actions like locks, blocklists, and antiflood.",
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=True
            )
            return
        except Exception as e:
            return await message.reply_text(
                text=f"❌ Error approving channel: {html.escape(str(e))}",
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=True
            )
    user_id = await extract_user(message, False)
    if not user_id:
        return await message.reply_text(
            text="🙋 *Reply to a user/channel message or give their ID/username!*\n\n"
                 "💡 *To approve channels:* Reply to a message sent by the channel",
            parse_mode=constants.ParseMode.MARKDOWN
        )
    if user_id == message.from_user.id:
        return await message.reply_text("🙃 You can't approve yourself!")
    if user_id in DEV_LIST:
        return await message.reply_text("👑 Devs don't need approval!")
    try:
        is_channel = user_id < 0
        if is_channel:
            user_link = await get_user_mention(bot, message.chat.id, user_id)
            if await is_user_approved_cached(message.chat.id, user_id):
                return await message.reply_text(
                    f"ℹ️ {user_link} is already approved!",
                    parse_mode=constants.ParseMode.HTML,
                    disable_web_page_preview=True
                )
            await approve_user(message.chat.id, user_id)
            is_user_approved_cached.clear_cache()
            await message.reply_text(
                f"✅ Channel {user_link} has been approved in <b>{html.escape(message.chat.title)}</b>!\n"
                f"🛡️ They will now be ignored by automated admin actions like locks, blocklists, and antiflood.",
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=True
            )
        else:
            member = await message.chat.get_member(user_id)
            user_link = await get_user_mention(bot, message.chat.id, user_id)
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return await message.reply_text(font("👮 Already admin, no need to approve!"))
            if await is_user_approved_cached(message.chat.id, user_id):
                return await message.reply_text(
                    f"ℹ️ {user_link} is already approved!",
                    parse_mode=constants.ParseMode.HTML,
                    disable_web_page_preview=True
                )
            await approve_user(message.chat.id, user_id)
            is_user_approved_cached.clear_cache()
            await message.reply_text(
                f"✅ {user_link} has been approved in <b>{html.escape(message.chat.title)}</b>!\n"
                f"🛡️ They will now be ignored by automated admin actions like locks, blocklists, and antiflood.",
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=True
            )
    except Exception as e:
        error_msg = str(e)
        if "User_not_mutual_contact" in error_msg:
            error_msg = "Cannot approve user because they haven't interacted with the bot yet."
        return await message.reply_text(
            text=f"❌ Error: {html.escape(error_msg)}",
            parse_mode=constants.ParseMode.HTML,
            disable_web_page_preview=True
        )

@Command(['unapprove', 'unfree'])
@admin_check("can_change_info", protect_target=False)
@only_groups
async def unapprove_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    bot = context.bot
    if message.reply_to_message and message.reply_to_message.sender_chat:
        sender_chat = message.reply_to_message.sender_chat
        user_id = sender_chat.id
        try:
            user_link = await get_user_mention(bot, message.chat.id, user_id)
            if not await is_user_approved_cached(message.chat.id, user_id):
                return await message.reply_text(
                    f"ℹ️ {user_link} is not approved.",
                    parse_mode=constants.ParseMode.HTML,
                    disable_web_page_preview=True
                )
            await unapprove_user(message.chat.id, user_id)
            is_user_approved_cached.clear_cache()
            await message.reply_text(
                f"🚫 Approval removed from channel {user_link}",
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=True
            )
            return
        except Exception as e:
            return await message.reply_text(
                text=f"❌ Error unapproving channel: {html.escape(str(e))}",
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=True
            )
    user_id = await extract_user(message, False)
    if not user_id:
        return await message.reply_text(
            text="🙋 *Reply to a user/channel message or give their ID/username!*\n\n"
                 "💡 *To unapprove channels:* Reply to a message sent by the channel",
            parse_mode=constants.ParseMode.MARKDOWN
        )
    try:
        user_link = await get_user_mention(bot, message.chat.id, user_id)
        if not await is_user_approved_cached(message.chat.id, user_id):
            return await message.reply_text(
                f"ℹ️ {user_link} is not approved.",
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=True
            )
        await unapprove_user(message.chat.id, user_id)
        is_user_approved_cached.clear_cache()
        await message.reply_text(
            f"🚫 Approval removed from {user_link}",
            parse_mode=constants.ParseMode.HTML,
            disable_web_page_preview=True
        )
    except Exception as e:
        return await message.reply_text(
            text=f"❌ Error: {html.escape(str(e))}",
            parse_mode=constants.ParseMode.HTML,
            disable_web_page_preview=True
        )

@Command("approval")
@only_groups
async def approval_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    bot = context.bot
    if message.reply_to_message and message.reply_to_message.sender_chat:
        user_id = message.reply_to_message.sender_chat.id
    else:
        user_id = await extract_user(message, False)
        if not user_id:
            user_id = message.from_user.id
    try:
        user_link = await get_user_mention(bot, message.chat.id, user_id)
        is_approved = await is_user_approved_cached(message.chat.id, user_id)
        status = "✅ APPROVED" if is_approved else "🚫 NOT APPROVED"
        entity_type = "📢 Channel" if user_id < 0 else "👤 User"
        msg = f"{entity_type}: {user_link}\n📊 Status: {status}"
        if is_approved:
            msg += "\n✨ Bypasses locks, blocklists & antiflood"
        await message.reply_text(msg, parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        return await message.reply_text(
            text=f"❌ Error: {html.escape(str(e))}",
            parse_mode=constants.ParseMode.HTML,
            disable_web_page_preview=True
        )

@Command("approved")
@admin_check("can_change_info", protect_target=False)
@only_groups
async def list_approved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    bot = context.bot
    users = await get_all_approved_users_cached(message.chat.id)
    if not users:
        return await message.reply_text(
            "📝 No approved users/channels.",
            parse_mode=constants.ParseMode.HTML
        )
    text = f"✅ <b>Approved Users/Channels in {html.escape(message.chat.title)}</b>\n\n"
    for i, user_id in enumerate(users, start=1):
        try:
            user_link = await get_user_mention(bot, message.chat.id, user_id)
            entity_type = "📢" if user_id < 0 else "👤"
            text += f"{i}. {entity_type} {user_link}\n"
        except:
            entity_type = "📢" if user_id < 0 else "👤"
            text += f"{i}. {entity_type} <code>{user_id}</code> (Deleted/Inaccessible)\n"
    text += f"\n📊 Total: {len(users)}"
    await message.reply_text(text, parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True)

@Command("unapproveall")
@admin_check("can_change_info", protect_target=False)
@group_owner_only
async def unapprove_all_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    users = await get_all_approved_users_cached(message.chat.id)
    if not users:
        return await message.reply_text(
            "📝 No approved users/channels to remove.",
            parse_mode=constants.ParseMode.HTML
        )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(font("✅ Confirm"), callback_data=f"clr_app#{message.chat.id}"),
            InlineKeyboardButton(font("❌ Cancel"), callback_data="clr_app#cancel")
        ]
    ])
    await message.reply_text(
        f"⚠️ <b>Warning!</b>\n\n"
        f"Remove approval from <b>{len(users)}</b> users/channels?\n"
        f"This action cannot be undone.",
        reply_markup=keyboard,
        parse_mode=constants.ParseMode.HTML
    )

@Callbacks(r"^clr_app#")
async def handle_clear_approval_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    chat = query.message.chat
    bot = context.bot
    member = await bot.get_chat_member(chat.id, user.id)
    if member.status != ChatMemberStatus.OWNER:
        return await query.answer(font("🚫 Only the group owner can do this!"), show_alert=True)
    await query.answer()
    action = query.data.split("#")[1]
    if action == "cancel":
        return await query.edit_message_text(font("❌ Cancelled."), parse_mode=constants.ParseMode.HTML)
    chat_id = int(action)
    users = await get_all_approved_users_cached(chat_id)
    count = len(users)
    await remove_all_approved_users(chat_id)
    is_user_approved_cached.clear_cache()
    get_all_approved_users_cached.clear_cache()
    await query.edit_message_text(
        f"✅ Removed approval from <b>{count}</b> users/channels.",
        parse_mode=constants.ParseMode.HTML
            )
