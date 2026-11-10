import re
import asyncio
import html
from AloneX import pbot, font
from AloneX.helpers.pyro_utils import is_admin
from AloneX.helpers.decorator import only_groups, get_effective_chat_id
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatPermissions, LinkPreviewOptions
from pyrogram.enums import ChatMembersFilter, ParseMode, ButtonStyle
from pyrogram.errors import RPCError, MessageDeleteForbidden, UserAdminInvalid, FloodWait
from cachetools import TTLCache

member_cache = TTLCache(maxsize=5000, ttl=300)
admin_cache = TTLCache(maxsize=1000, ttl=300)

async def get_member_cached(chat, user_id):
    cache_key = f"{chat.id}:{user_id}"
    if cache_key in member_cache:
        return member_cache[cache_key]
    try:
        member = await chat.get_member(user_id)
        member_cache[cache_key] = member
        return member
    except Exception as e:
        raise e

async def get_admin_cached(chat_id, user_id):
    cache_key = f"{chat_id}:{user_id}"
    if cache_key in admin_cache:
        return admin_cache[cache_key]
    try:
        is_user_admin = await is_admin(chat_id, user_id)
        admin_cache[cache_key] = is_user_admin
        return is_user_admin
    except Exception:
        return False

def invalidate_member_cache(chat_id, user_id):
    cache_key = f"{chat_id}:{user_id}"
    member_cache.pop(cache_key, None)
    admin_cache.pop(cache_key, None)

@pbot.on_message((filters.command(["report", "reportar"]) | filters.regex(r"^@admin(s)?", flags=re.IGNORECASE)) & ~filters.forwarded, group=-78)
async def report_admin_mention(client, message: Message):
    if not message.reply_to_message:
        return
    reported_user = message.reply_to_message.from_user
    if not reported_user or reported_user.is_bot or reported_user.id == message.from_user.id:
        return
    try:
        target_member = await get_member_cached(message.chat, reported_user.id)
        if target_member.status in ["administrator", "creator"]:
            return
    except Exception:
        pass
    admin_mentions = []
    async for admin in message.chat.get_members(filter=ChatMembersFilter.ADMINISTRATORS):
        user = admin.user
        if (user and not user.is_bot and not user.is_deleted and not getattr(admin.privileges, "is_anonymous", False)):
            admin_mentions.append(f"<a href='tg://user?id={user.id}'>\u200b</a>")
    if not admin_mentions:
        return
    admin_tags = "".join(admin_mentions)
    reporter_link = f"<a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name or 'User'}</a>"
    reported_link = f"<a href='tg://user?id={reported_user.id}'>{reported_user.first_name or 'User'}</a>"
    
    # Fix: Construct the message link properly
    chat_username = message.chat.username
    msg_id = message.reply_to_message.id
    
    if chat_username:
        # For public groups/channels
        message_link = f"https://t.me/{chat_username}/{msg_id}"
    else:
        # For private groups (use c/ format)
        chat_id_str = str(message.chat.id)[4:]  # Remove -100 prefix
        message_link = f"https://t.me/c/{chat_id_str}/{msg_id}"
    
    report_text = (
        f"🚨 <b>Report Alert</b>\n\n"
        f"👤 <b>Reported:</b> {reported_link}\n"
        f"📢 <b>By:</b> {reporter_link}\n\n"
        f"Reported{admin_tags} to admins."
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(font("💬 View Message"), url=message_link, style=ButtonStyle.PRIMARY)
        ],
        [
            InlineKeyboardButton(font("⚠️ Kick"), callback_data=f"rp_kick_{reported_user.id}", style=ButtonStyle.DANGER),
            InlineKeyboardButton(font("🚫 Ban"), callback_data=f"rp_ban_{reported_user.id}", style=ButtonStyle.DANGER)
        ],
        [
            InlineKeyboardButton(font("❌ Delete"), callback_data=f"rp_del_{message.reply_to_message.id}", style=ButtonStyle.DANGER),
            InlineKeyboardButton(font("🔇 Mute"), callback_data=f"rp_mute_{reported_user.id}", style=ButtonStyle.PRIMARY)
        ],
        [
            InlineKeyboardButton(font("✅ Ignore"), callback_data=f"rp_ignore_{message.from_user.id}", style=ButtonStyle.PRIMARY)
        ]
    ])
    
    try:
        sent = await message.reply_to_message.reply_text(
            text=report_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )

        # Log to log channel
        from AloneX.helpers.log_helper import log_action
        from AloneX import app as ptb_app
        log_text = f"📢 <b>Report</b>\n" \
                   f"<b>Group:</b> {html.escape(message.chat.title)}\n" \
                   f"<b>Reported User:</b> {reported_link} (<code>{reported_user.id}</code>)\n" \
                   f"<b>By:</b> {reporter_link} (<code>{message.from_user.id}</code>)\n" \
                   f"<b>Message:</b> <a href='{message_link}'>Link</a>"
        asyncio.create_task(log_action(ptb_app.bot, message.chat.id, "reports", log_text))

        asyncio.create_task(auto_delete_report(sent, message, 300))
    except Exception as e:
        print(f"[Report Error] {e}")

async def auto_delete_report(sent_msg, original_msg, delay):
    await asyncio.sleep(delay)
    try:
        await sent_msg.delete()
        await original_msg.delete()
    except Exception:
        pass

@pbot.on_callback_query(filters.regex(r"^rp_kick_"))
async def report_kick_handler(client, query: CallbackQuery):
    from AloneX.helpers.decorator import get_effective_chat_id_pyro
    chat_id = await get_effective_chat_id_pyro(query)
    if not await get_admin_cached(chat_id, query.from_user.id):
        return await query.answer(font("❌ Admins only"), show_alert=True)
    user_id = int(query.data.split("_")[2])
    try:
        bot_member = await client.get_chat_member(chat_id, "me")
        if not bot_member.privileges or not bot_member.privileges.can_restrict_members:
            return await query.answer(font("❌ Bot needs restrict permission"), show_alert=True)
        target_member = await client.get_chat_member(chat_id, user_id)
        if target_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await query.answer(font("❌ Cannot kick admins"), show_alert=True)
        await client.ban_chat_member(chat_id, user_id)
        await client.unban_chat_member(chat_id, user_id)
        invalidate_member_cache(chat_id, user_id)
        admin_name = query.from_user.first_name or "Admin"
        user_link = f"<a href='tg://user?id={user_id}'>{target_member.user.first_name or 'User'}</a>"
        await query.message.edit_text(
            f"👢 {user_link} kicked by {admin_name}.",
            reply_markup=None,
            parse_mode=ParseMode.HTML
        )
        await query.answer(font("✅ User kicked successfully"))
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await query.answer(font("⏳ Rate limited, try again"), show_alert=True)
    except UserAdminInvalid:
        await query.answer(font("❌ Cannot kick admins"), show_alert=True)
    except Exception as e:
        await query.answer(f"❌ Failed: {str(e)[:50]}", show_alert=True)

@pbot.on_callback_query(filters.regex(r"^rp_ban_"))
async def report_ban_handler(client, query: CallbackQuery):
    from AloneX.helpers.decorator import get_effective_chat_id_pyro
    chat_id = await get_effective_chat_id_pyro(query)
    if not await get_admin_cached(chat_id, query.from_user.id):
        return await query.answer(font("❌ Admins only"), show_alert=True)
    user_id = int(query.data.split("_")[2])
    try:
        bot_member = await client.get_chat_member(chat_id, "me")
        if not bot_member.privileges or not bot_member.privileges.can_restrict_members:
            return await query.answer(font("❌ Bot needs restrict permission"), show_alert=True)
        target_member = await client.get_chat_member(chat_id, user_id)
        if target_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await query.answer(font("❌ Cannot ban admins"), show_alert=True)
        await client.ban_chat_member(chat_id, user_id)
        invalidate_member_cache(chat_id, user_id)
        admin_name = query.from_user.first_name or "Admin"
        user_link = f"<a href='tg://user?id={user_id}'>{target_member.user.first_name or 'User'}</a>"
        await query.message.edit_text(
            f"🚫 {user_link} banned by {admin_name}.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(font("✅ Unban"), callback_data=f"rp_unban_{user_id}", style=ButtonStyle.SUCCESS)]]),
            parse_mode=ParseMode.HTML
        )
        await query.answer(font("✅ User banned successfully"))
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await query.answer(font("⏳ Rate limited, try again"), show_alert=True)
    except UserAdminInvalid:
        await query.answer(font("❌ Cannot ban admins"), show_alert=True)
    except Exception as e:
        await query.answer(f"❌ Failed: {str(e)[:50]}", show_alert=True)

@pbot.on_callback_query(filters.regex(r"^rp_unban_"))
async def report_unban_handler(client, query: CallbackQuery):
    from AloneX.helpers.decorator import get_effective_chat_id_pyro
    chat_id = await get_effective_chat_id_pyro(query)
    if not await get_admin_cached(chat_id, query.from_user.id):
        return await query.answer(font("❌ Admins only"), show_alert=True)
    user_id = int(query.data.split("_")[2])
    try:
        await client.unban_chat_member(chat_id, user_id)
        invalidate_member_cache(chat_id, user_id)
        admin_name = query.from_user.first_name or "Admin"
        await query.message.edit_text(
            f"✅ User unbanned by {admin_name}.",
            reply_markup=None
        )
        await query.answer(font("✅ User unbanned"))
    except Exception as e:
        await query.answer(f"❌ Failed: {str(e)[:50]}", show_alert=True)

@pbot.on_callback_query(filters.regex(r"^rp_mute_"))
async def report_mute_handler(client, query: CallbackQuery):
    from AloneX.helpers.decorator import get_effective_chat_id_pyro
    chat_id = await get_effective_chat_id_pyro(query)
    if not await get_admin_cached(chat_id, query.from_user.id):
        return await query.answer(font("❌ Admins only"), show_alert=True)
    user_id = int(query.data.split("_")[2])
    try:
        bot_member = await client.get_chat_member(chat_id, "me")
        if not bot_member.privileges or not bot_member.privileges.can_restrict_members:
            return await query.answer(font("❌ Bot needs restrict permission"), show_alert=True)
        target_member = await client.get_chat_member(chat_id, user_id)
        if target_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await query.answer(font("❌ Cannot mute admins"), show_alert=True)
        await client.restrict_chat_member(
            chat_id,
            user_id,
            ChatPermissions(can_send_messages=False)
        )
        invalidate_member_cache(chat_id, user_id)
        admin_name = query.from_user.first_name or "Admin"
        user_link = f"<a href='tg://user?id={user_id}'>{target_member.user.first_name or 'User'}</a>"
        await query.message.edit_text(
            f"🔇 {user_link} muted by {admin_name}.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(font("🔊 Unmute"), callback_data=f"rp_unmute_{user_id}", style=ButtonStyle.SUCCESS)]]),
            parse_mode=ParseMode.HTML
        )
        await query.answer(font("✅ User muted successfully"))
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await query.answer(font("⏳ Rate limited, try again"), show_alert=True)
    except UserAdminInvalid:
        await query.answer(font("❌ Cannot mute admins"), show_alert=True)
    except Exception as e:
        await query.answer(f"❌ Failed: {str(e)[:50]}", show_alert=True)

@pbot.on_callback_query(filters.regex(r"^rp_unmute_"))
async def report_unmute_handler(client, query: CallbackQuery):
    from AloneX.helpers.decorator import get_effective_chat_id_pyro
    chat_id = await get_effective_chat_id_pyro(query)
    if not await get_admin_cached(chat_id, query.from_user.id):
        return await query.answer(font("❌ Admins only"), show_alert=True)
    user_id = int(query.data.split("_")[2])
    try:
        await client.restrict_chat_member(
            chat_id,
            user_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_invite_users=True
            )
        )
        invalidate_member_cache(chat_id, user_id)
        admin_name = query.from_user.first_name or "Admin"
        await query.message.edit_text(
            f"🔊 User unmuted by {admin_name}.",
            reply_markup=None
        )
        await query.answer(font("✅ User unmuted"))
    except Exception as e:
        await query.answer(f"❌ Failed: {str(e)[:50]}", show_alert=True)

@pbot.on_callback_query(filters.regex(r"^rp_del_"))
async def report_delete_handler(_, query: CallbackQuery):
    if not await get_admin_cached(query.message.chat.id, query.from_user.id):
        return await query.answer(font("❌ Admins only"), show_alert=True)
    msg_id = int(query.data.split("_")[2])
    try:
        await pbot.delete_messages(query.message.chat.id, msg_id)
        admin_name = query.from_user.first_name or "Admin"
        await query.message.edit_text(
            f"✅ Reported message deleted by {admin_name}.",
            reply_markup=None
        )
        await query.answer(font("✅ Message deleted"))
    except MessageDeleteForbidden:
        await query.answer("❌ Can't delete this message", show_alert=True)
    except Exception as e:
        await query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)

@pbot.on_callback_query(filters.regex(r"^rp_ignore_"))
async def report_ignore_handler(client, query: CallbackQuery):
    from AloneX.helpers.decorator import get_effective_chat_id_pyro
    chat_id = await get_effective_chat_id_pyro(query)
    if not await get_admin_cached(chat_id, query.from_user.id):
        return await query.answer(font("❌ Admins only"), show_alert=True)
    admin_name = query.from_user.first_name or "Admin"
    try:
        await query.message.edit_text(
            f"✅ Report ignored by {admin_name}.",
            reply_markup=None
        )
        await query.answer(font("✅ Report dismissed"))
    except Exception:
        await query.answer(font("✅ Ignored"), show_alert=False)
