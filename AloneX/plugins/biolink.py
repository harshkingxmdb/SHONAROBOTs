import re
import asyncio
import html
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM, Message, CallbackQuery
from pyrogram.enums import ButtonStyle, ChatMemberStatus
from AloneX import pbot, font, LOGS_CHANNEL, BOT_USERNAME, prefix_cmds, DEV_LIST
from AloneX.db.bio_filter import (
    is_bio_filter_enabled,
    set_bio_filter_status,
    get_auth_users,
    add_auth,
    remove_auth
)
from AloneX.helpers.decorator import protected_ids

__module__ = "𝐀ɴᴛɪ-𝐁ɪᴏʟɪɴᴋ🔗"
__help__ = """
*Bio Link Filter 🔗 — Protect your group from bio spammers*

• `/biolink` — Toggle bio link filter or check status.
• `/bauth <reply|user>` — Authorize a user to have links in bio.
• `/rmbauth <reply|user>` — Unauthorize a user.
• `/bauthlist` — Show list of authorized users.

*Main feature:*
Deletes messages from users who have a link or @username in their bio.
"""

# ----------------- Regex -----------------
URL_PATTERN = re.compile(r"(https?://|www\.)\S+", re.IGNORECASE)
USERNAME_PATTERN = re.compile(r"@[\w_]+", re.IGNORECASE)

def format_user(user):
    username = f"@{user.username}" if user.username else "No Username"
    mention = f"<a href='tg://user?id={user.id}'>{html.escape(user.first_name)}</a>"
    return f"<b>Name:</b> {mention}\n<b>User ID:</b> <code>{user.id}</code>\n<b>Username:</b> <code>{html.escape(username)}</code>"

async def get_target_user(message: Message):
    if message.reply_to_message:
        return message.reply_to_message.from_user
    elif len(message.command) > 1:
        username = message.command[1].strip()
        try:
            user = await pbot.get_users(username)
            return user
        except:
            return None
    return None

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

# ----------------- Keyboards -----------------
async def get_biolink_keyboard(chat_id: int):
    is_enabled = await is_bio_filter_enabled(chat_id)
    if is_enabled:
        text = "🟢 Bio Link Filter: ON"
    else:
        text = "🔴 Bio Link Filter: OFF"

    # We use style attribute because the project uses a custom Pyrogram (kurigram)
    # that supports ButtonStyle. SUCCESS and DANGER enums are imported from pyrogram.enums
    return IKM([[IKB(font(text), callback_data="bl_toggle", style=ButtonStyle.SUCCESS if is_enabled else ButtonStyle.DANGER)]])

# ----------------- Enable / Disable Commands -----------------
@pbot.on_message(filters.command("biolink", prefixes=prefix_cmds) & filters.group)
async def bl_cmd(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    if len(message.command) > 1:
        state = message.command[1].lower()
        if state == "on":
            await set_bio_filter_status(message.chat.id, True)
            return await message.reply_text(font("✅ Bio Link Filter <b>Enabled</b>."), reply_markup=await get_biolink_keyboard(message.chat.id), parse_mode=enums.ParseMode.HTML)
        elif state == "off":
            await set_bio_filter_status(message.chat.id, False)
            return await message.reply_text(font("❌ Bio Link Filter <b>Disabled</b>."), reply_markup=await get_biolink_keyboard(message.chat.id), parse_mode=enums.ParseMode.HTML)

    is_enabled = await is_bio_filter_enabled(message.chat.id)
    status_text = "Enabled" if is_enabled else "Disabled"
    await message.reply_text(
        font(f"🔗 <b>Bio Link Filter Status:</b> {status_text}\n\nClick the button below to toggle."),
        reply_markup=await get_biolink_keyboard(message.chat.id),
        parse_mode=enums.ParseMode.HTML
    )

@pbot.on_callback_query(filters.regex(r"^bl_toggle$"))
async def bl_toggle_callback(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(font("❌ This button is for admins only!"), show_alert=True)

    is_enabled = await is_bio_filter_enabled(chat_id)
    new_state = not is_enabled
    await set_bio_filter_status(chat_id, new_state)

    status_text = "Enabled" if new_state else "Disabled"
    await query.message.edit_text(
        font(f"🔗 <b>Bio Link Filter Status:</b> {status_text}\n\nClick the button below to toggle."),
        reply_markup=await get_biolink_keyboard(chat_id),
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer(font(f"Bio Link Filter {'Enabled' if new_state else 'Disabled'}"))

# ----------------- Auth Commands -----------------
@pbot.on_message(filters.command("bauth", prefixes=prefix_cmds) & filters.group)
async def add_auth_command(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ Admin privilege required!"))

    user = await get_target_user(message)
    if not user:
        return await message.reply_text(font("Reply to a user or give a valid username/user ID!"))

    await add_auth(message.chat.id, user.id)
    await message.reply_text(f"{font('✅ User has been <b>authorized</b>.')}\n\n{format_user(user)}", parse_mode=enums.ParseMode.HTML)

@pbot.on_message(filters.command("rmbauth", prefixes=prefix_cmds) & filters.group)
async def remove_auth_command(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ Admin privilege required!"))

    user = await get_target_user(message)
    if not user:
        return await message.reply_text(font("Reply to a user or give a valid username/user ID!"))

    await remove_auth(message.chat.id, user.id)
    await message.reply_text(f"{font('❌ User has been <b>unauthorized</b>.')}\n\n{format_user(user)}", parse_mode=enums.ParseMode.HTML)

@pbot.on_message(filters.command("bauthlist", prefixes=prefix_cmds) & filters.group)
async def authlist_handler(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ Admin privilege required!"))

    chat_id = message.chat.id
    users = await get_auth_users(chat_id)

    if not users:
        return await message.reply_text(font("⚠️ No users have been authorized in this group."))

    text = font("<b>Authorized users in this group:</b>\n\n")
    for i, user_id in enumerate(users, start=1):
        try:
            user = await pbot.get_users(user_id)
            name = f"<a href='tg://user?id={user.id}'>{html.escape(user.first_name)}</a>"
        except:
            name = f"<code>{user_id}</code> (Unable to fetch)"
        text += f"{i}. {name}\n"

    await message.reply_text(text, parse_mode=enums.ParseMode.HTML)

# ----------------- Main Bio Filter -----------------
@pbot.on_message(filters.group & filters.text & ~filters.bot, group=110)
async def bio_filter_handler(client, message):
    chat_id = message.chat.id
    user = message.from_user

    if not user:
        return

    # Filter disabled
    if not await is_bio_filter_enabled(chat_id):
        return

    # Sudo/Dev ignore
    if user.id in protected_ids:
        return

    # Admin ignore
    if await is_user_admin(chat_id, user.id):
        return

    # Auth ignore
    auth_users = await get_auth_users(chat_id)
    if user.id in auth_users:
        return

    # Get bio
    try:
        user_info = await client.get_chat(user.id)
        bio = getattr(user_info, "bio", "") or ""
    except:
        bio = ""

    # No bio
    if not bio:
        return

    # Check if bio contains link OR username tag
    if not (re.search(URL_PATTERN, bio) or re.search(USERNAME_PATTERN, bio)):
        return

    # ----------------- Delete message -----------------
    try:
        await message.delete()
    except:
        pass

    mention = f"<a href='tg://user?id={user.id}'>{html.escape(user.first_name)}</a>"
    username = f"@{user.username}" if user.username else "None"

    # ----------------- Warn User -----------------
    try:
        warn = await message.reply_text(
            f"⚠️ {mention}, {font('<b>bio me link/username allowed nahi hai!</b>')}",
            parse_mode=enums.ParseMode.HTML
        )
        await asyncio.sleep(10)
        await warn.delete()
    except:
        pass

    # ----------------- Send Log -----------------
    log_text = f"""
<b>🚨 Bio Filter Alert</b>
<b>User:</b> {mention}
<b>Username:</b> {html.escape(username)}
<b>User ID:</b> <code>{user.id}</code>
<b>Group:</b> <code>{html.escape(message.chat.title)}</code>
<b>Chat ID:</b> <code>{chat_id}</code>
<b>Bio:</b> <code>{html.escape(bio)}</code>
"""

    if LOGS_CHANNEL:
        try:
            await client.send_message(
                LOGS_CHANNEL,
                log_text,
                parse_mode=enums.ParseMode.HTML,
            )
        except:
            pass
