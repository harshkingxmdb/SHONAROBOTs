import asyncio
import html
from pyrogram import filters, enums
from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.errors import RPCError
from pyrogram.types import (
    Message, ChatJoinRequest, InlineKeyboardMarkup,
    InlineKeyboardButton, CallbackQuery, ChatMemberUpdated
)
from pyrogram.enums import ButtonStyle
from AloneX import pbot, prefix_cmds, font
from AloneX.db.join_request import toggle_request, is_request_enabled
from AloneX.helpers.decorator import protected_ids

JOIN_REQUEST_MESSAGES = {}  

__module__ = "𝐉ᴏɪɴ-𝐑ᴇǫᴜᴇsᴛ📝"
__help__ = """
*Join Request Management* — Manage group join requests with an approval system

• `/request` — Toggle join request notifications or check status.

*Note:* Only admins with 'Add Users' permission can approve/decline requests.
"""

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
        # Check for invite users permission as well for join requests
        res = member.status == ChatMemberStatus.OWNER or (
            member.status == ChatMemberStatus.ADMINISTRATOR and
            member.privileges and member.privileges.can_invite_users
        )
        user_admin_cache[k] = res
        return res
    except:
        return False

async def get_join_request_keyboard(chat_id: int):
    enabled = await is_request_enabled(chat_id)
    if enabled:
        text = "🟢 Join Request: ON"
        style = ButtonStyle.SUCCESS
    else:
        text = "🔴 Join Request: OFF"
        style = ButtonStyle.DANGER

    return InlineKeyboardMarkup([[InlineKeyboardButton(font(text), callback_data="jr_toggle", style=style)]])

@pbot.on_message(filters.command("request", prefixes=prefix_cmds) & filters.group & ~filters.forwarded, group=-321)
async def request_toggle_cmd(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply(font("❌ You must be an admin with 'Add Users' permission to use this command."))

    if len(message.command) > 1:
        arg = message.command[1].lower()
        if arg in ["enable", "on"]:
            await toggle_request(message.chat.id, True)
            return await message.reply(font("✅ Join Request Notifications <b>Enabled</b>."), reply_markup=await get_join_request_keyboard(message.chat.id), parse_mode=ParseMode.HTML)
        elif arg in ["disable", "off"]:
            await toggle_request(message.chat.id, False)
            return await message.reply(font("❌ Join Request Notifications <b>Disabled</b>."), reply_markup=await get_join_request_keyboard(message.chat.id), parse_mode=ParseMode.HTML)

    enabled = await is_request_enabled(message.chat.id)
    status = "Enabled" if enabled else "Disabled"
    await message.reply(
        font(f"📝 <b>Join Request Status:</b> {status}\n\nClick the button below to toggle."),
        reply_markup=await get_join_request_keyboard(message.chat.id),
        parse_mode=ParseMode.HTML
    )

@pbot.on_callback_query(filters.regex(r"^jr_toggle$"))
async def jr_toggle_cb(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(font("❌ Admin privilege required!"), show_alert=True)

    enabled = await is_request_enabled(chat_id)
    new_state = not enabled
    await toggle_request(chat_id, new_state)

    status = "Enabled" if new_state else "Disabled"
    await query.message.edit_text(
        font(f"📝 <b>Join Request Status:</b> {status}\n\nClick the button below to toggle."),
        reply_markup=await get_join_request_keyboard(chat_id),
        parse_mode=ParseMode.HTML
    )
    await query.answer(font(f"Join Request Notifications {'Enabled' if new_state else 'Disabled'}"))

@pbot.on_chat_join_request()
async def join_request_handler(_, req: ChatJoinRequest):
    chat_id = req.chat.id
    user = req.from_user

    if not await is_request_enabled(chat_id):
        return

    full_name = user.first_name or "Unknown"
    username = f"@{user.username}" if user.username else "N/A"

    text = (
        f"📥 <b>New Join Request</b>\n\n"
        f"👤 <b>Name:</b> <a href='tg://user?id={user.id}'>{html.escape(full_name)}</a>\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"🔗 <b>Username:</b> {html.escape(username)}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(font("✅ Approve"), callback_data=f"approve|{chat_id}|{user.id}", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(font("❌ Decline"), callback_data=f"decline|{chat_id}|{user.id}", style=ButtonStyle.DANGER)
        ]
    ])

    msg = await pbot.send_message(
        chat_id,
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

    JOIN_REQUEST_MESSAGES[(chat_id, user.id)] = msg.id

@pbot.on_callback_query(filters.regex(r"^(approve|decline)\|(-?\d+)\|(\d+)$"))
async def callback_join_action(_, cb: CallbackQuery):
    action, chat_id, user_id = cb.matches[0].groups()
    chat_id = int(chat_id)
    user_id = int(user_id)
    clicker_id = cb.from_user.id

    if not await is_user_admin(chat_id, clicker_id):
        return await cb.answer(font("❌ Only admins with 'Add Users' permission can process requests."), show_alert=True)

    try:
        if action == "approve":
            await pbot.approve_chat_join_request(chat_id, user_id)
            await cb.message.edit_text(
                f"✅ <b>Approved</b> by <a href='tg://user?id={clicker_id}'>{html.escape(cb.from_user.first_name)}</a>\n"
                f"👤 <b>User ID:</b> <code>{user_id}</code>",
                parse_mode=ParseMode.HTML
            )
        else:
            await pbot.decline_chat_join_request(chat_id, user_id)
            await cb.message.edit_text(
                f"❌ <b>Declined</b> by <a href='tg://user?id={clicker_id}'>{html.escape(cb.from_user.first_name)}</a>\n"
                f"👤 <b>User ID:</b> <code>{user_id}</code>",
                parse_mode=ParseMode.HTML
            )

    except RPCError as e:
        if "USER_ALREADY_PARTICIPANT" in str(e):
            msg_id = JOIN_REQUEST_MESSAGES.pop((chat_id, user_id), None)
            if msg_id:
                try:
                    await pbot.delete_messages(chat_id, msg_id)
                except Exception:
                    pass
            return await cb.answer(font("ℹ️ User already in group. Message deleted."), show_alert=True)
        else:
            return await cb.answer(font("❌ Failed to process the request."), show_alert=True)

    JOIN_REQUEST_MESSAGES.pop((chat_id, user_id), None)
    await cb.answer(font("✅ Done"))

@pbot.on_chat_member_updated()
async def on_member_added(_, update: ChatMemberUpdated):
    chat_id = update.chat.id
    user_id = update.new_chat_member.user.id

    key = (chat_id, user_id)
    if key in JOIN_REQUEST_MESSAGES:
        msg_id = JOIN_REQUEST_MESSAGES.pop(key, None)
        if msg_id:
            try:
                await pbot.delete_messages(chat_id, msg_id)
            except Exception:
                pass
