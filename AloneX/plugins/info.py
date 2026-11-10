import html
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from cachetools import TTLCache
import config
from telegram import constants, helpers, InlineKeyboardButton, InlineKeyboardMarkup, User, Chat
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from AloneX.helpers.decorator import Command, disableable
from AloneX.helpers.utils import get_media_id, find_registration_time, extract_user
from AloneX import pbot, font
from AloneX.db.sudo import (
    get_all_sudo_users, 
    get_all_whitelist_users, 
    get_all_support_users
)

logger = logging.getLogger(__name__)

__module__ = '𝐈ɴғᴏℹ️'

__help__ = '''
Commands:

❂ `/user/info <user_id or username>`: Get user information  
❂ `/chat <chat_id or chat name>`: Get chat information  
❂ `/id <user_id>`: Get all possible file, user, and chat IDs

Examples:
`/user @username`
`/chat -1001234567890`
Reply to a message with `/id`
'''

DC_LOCATIONS = {
    1: "MIA, Miami, FL, USA",
    2: "AMS, Amsterdam, NL",
    3: "MIA, Miami, FL, USA",
    4: "AMS, Amsterdam, NL",
    5: "SIN, Singapore, SG"
}

sudo_cache = TTLCache(maxsize=1, ttl=2)
support_cache = TTLCache(maxsize=1, ttl=2)
whitelist_cache = TTLCache(maxsize=1, ttl=2)

async def get_status_text(user_id: int) -> str:
    if user_id == config.OWNER_ID:
        return "👑 Owner"
    
    if hasattr(config, "DEV_LIST") and user_id in config.DEV_LIST:
        return "👨‍💻 Developer ⭐"
    
    if 'sudo' not in sudo_cache:
        db_sudo_users = await get_all_sudo_users()
        config_sudo_users = getattr(config, "SUDO_USERS", [])
        sudo_cache['sudo'] = set(db_sudo_users) | set(config_sudo_users)
    if user_id in sudo_cache['sudo']:
        return "⚡ Sudo User"
    
    if 'support' not in support_cache:
        db_support_users = await get_all_support_users()
        config_support_users = getattr(config, "SUPPORT_USERS", [])
        support_cache['support'] = set(db_support_users) | set(config_support_users)
    if user_id in support_cache['support']:
        return "🆘 Support User"
    
    if 'whitelist' not in whitelist_cache:
        db_whitelist_users = await get_all_whitelist_users()
        config_whitelist_users = getattr(config, "WHITELIST_USERS", [])
        whitelist_cache['whitelist'] = set(db_whitelist_users) | set(config_whitelist_users)
    if user_id in whitelist_cache['whitelist']:
        return "✅ Whitelisted"
    
    return ""

def safe_escape(text: Any) -> str:
    return "Null" if text is None else html.escape(str(text))

def format_chat_id(chat_id: str) -> str:
    if chat_id.startswith("https://t.me/"):
        return "@" + chat_id.split("/")[-1]
    return chat_id

def calculate_account_age(creation_date):
    today = datetime.now()
    total_days = (today - creation_date).days
    years = total_days // 365
    remaining_days = total_days % 365
    months = remaining_days // 30
    days = remaining_days % 30
    return f"{years} years, {months} months, {days} days"

def estimate_account_creation_date(user_id):
    reference_points = [
        (100000000, datetime(2013, 8, 1)),
        (1273841502, datetime(2020, 8, 13)),
        (1500000000, datetime(2021, 5, 1)),
        (2000000000, datetime(2022, 12, 1)),
    ]
    closest_point = min(reference_points, key=lambda x: abs(x[0] - user_id))
    closest_user_id, closest_date = closest_point
    id_difference = user_id - closest_user_id
    days_difference = id_difference / 20000000
    return closest_date + timedelta(days=days_difference)

async def get_photo_bytes(bot, photo_id: str) -> Optional[bytes]:
    try:
        try:
            photo_path = await pbot.download_media(photo_id, in_memory=True)
            if photo_path:
                if hasattr(photo_path, 'getvalue'):
                    return photo_path.getvalue()
                elif isinstance(photo_path, bytes):
                    return photo_path
        except Exception as e:
            logger.debug(f"Pyrogram download failed: {e}")
        
        file_info = await bot.get_file(photo_id)
        
        if hasattr(file_info, 'file_path'):
            if file_info.file_path.startswith('/'):
                try:
                    with open(file_info.file_path, 'rb') as f:
                        return f.read()
                except Exception as e:
                    logger.warning(f"Local file read failed: {e}")
            
            elif file_info.file_path.startswith('http'):
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                        async with session.get(file_info.file_path) as resp:
                            if resp.status == 200:
                                return await resp.read()
                except Exception as e:
                    logger.warning(f"HTTP download failed: {e}")
        
        try:
            return await file_info.download_as_bytearray()
        except Exception as e:
            logger.warning(f"PTB download failed: {e}")
            
    except Exception as e:
        logger.exception(f"Failed to get photo bytes: {e}")
    
    return None

def build_chat_info_text(chat: Chat) -> str:
    chat_type = "Chat"
    if chat.type == constants.ChatType.CHANNEL:
        chat_type = "Channel"
    elif chat.type == constants.ChatType.GROUP:
        chat_type = "Group"
    elif chat.type == constants.ChatType.SUPERGROUP:
        chat_type = "Supergroup"
    
    title = getattr(chat, 'title', 'Unknown')
    username = getattr(chat, 'username', None)
    member_count = getattr(chat, 'member_count', None)
    description = getattr(chat, 'description', None)
    
    text = (
        f"<b>🔍 Showing {chat_type}'s Profile Info 📋</b>\n"
        "<b>━━━━━━━━━━━━━━━━</b>\n"
        f"<b>Chat Title:</b> <b>{safe_escape(title)}</b>\n"
    )
    
    if username:
        text += f"<b>Username:</b> @{username}\n"
    
    text += f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
    
    if chat.type == constants.ChatType.SUPERGROUP:
        text += f"<b>Chat Type:</b> <b>Supergroup</b>\n"
    elif chat.type == constants.ChatType.GROUP:
        text += f"<b>Chat Type:</b> <b>Group</b>\n"
    elif chat.type == constants.ChatType.CHANNEL:
        text += f"<b>Chat Type:</b> <b>Channel</b>\n"
    
    if member_count:
        text += f"<b>Total Members:</b> <b>{member_count}</b>\n"
    
    if description:
        text += f"<b>Description:</b> <code>{safe_escape(description)}</code>\n"
    
    if username:
        text += f"<b>Permanent Link:</b> <a href='https://t.me/{username}'>Click Here</a>\n"
    
    text += (
        "<b>━━━━━━━━━━━━━━━━</b>\n"
        "<b>👁 Thank You for Using Our Tool ✅</b>"
    )
    return text

@Command(['chat', 'ginfo'])
@disableable("chat")
async def ChatInfo(update, context):
    bot = context.bot
    m = update.effective_message
    chat = update.effective_chat

    if chat.type == constants.ChatType.PRIVATE and len(m.text.split()) < 2:
        await m.reply_text(
            "🌚 <b>To check user info, kindly use /user command instead. "
            "This command needs a chatId argument.</b>\n"
            "<b>Example:</b> /chat chat_id",
            parse_mode=constants.ParseMode.HTML
        )
        return

    msg_task = asyncio.create_task(
        m.reply_text(font("<code>Processing Chat Info...</code>"), parse_mode=constants.ParseMode.HTML)
    )
    
    chat_id = chat.id
    if len(m.text.split()) > 1:
        chat_id = format_chat_id(m.text.split()[1].strip())
        
        if not (str(chat_id).startswith("@") or str(chat_id).startswith("-100")):
            msg = await msg_task
            await msg.edit_text(font("🙋 <b>Give only a valid chat username or chat_id.</b>"),
                               parse_mode=constants.ParseMode.HTML)
            return

    msg = await msg_task

    try:
        chat = await bot.get_chat(chat_id)
        text = build_chat_info_text(chat)
        title = getattr(chat, 'title', 'Unknown')
        
        if chat.photo:
            photo_bytes = await get_photo_bytes(bot, chat.photo.big_file_id)
            if photo_bytes:
                await m.reply_photo(
                    photo=photo_bytes,
                    caption=text,
                    parse_mode=constants.ParseMode.HTML
                )
                await msg.delete()
                return
        
        await msg.edit_text(text=text, parse_mode=constants.ParseMode.HTML)
        
    except Exception as e:
        await msg.edit_text(f"❌ <b>ERROR:</b> {html.escape(str(e))}", 
                           parse_mode=constants.ParseMode.HTML)

@Command(['user', 'info'])
@disableable(['user', 'info'])
async def UserInfo(update, context):
    message = update.effective_message
    bot = context.bot
    chat = update.effective_chat
    
    user_id = await extract_user(message)
    if not user_id:
        await message.reply_text("Can't access by username, reply to the user or give their telegram id")
        return

    if (message.reply_to_message and message.reply_to_message.forward_origin 
        and getattr(message.reply_to_message.forward_origin, "sender_user", None)):
        user_id = message.reply_to_message.forward_origin.sender_user.id

    msg_task = asyncio.create_task(
        message.reply_text(font("<code>Processing User Info...</code>"), parse_mode=constants.ParseMode.HTML)
    )
    
    try:
        user_task = asyncio.create_task(bot.get_chat(user_id))
        msg, user = await asyncio.gather(msg_task, user_task)
        
        pyro_user = await pbot.get_users(user_id)
        dc_id = getattr(pyro_user, 'dc_id', None)
        is_premium = getattr(pyro_user, 'is_premium', False)
        is_bot = getattr(pyro_user, 'is_bot', False)
        is_restricted = getattr(pyro_user, 'is_restricted', False)
            
    except Exception as e:
        msg = await msg_task
        await msg.edit_text(f"❌ ERROR: {html.escape(str(e))}", 
                           parse_mode=constants.ParseMode.HTML)
        return

    dc_location = DC_LOCATIONS.get(dc_id, "Unknown")
    premium_status = "Yes" if is_premium else "No"
    account_created = estimate_account_creation_date(user.id)
    account_created_str = account_created.strftime("%B %d, %Y")
    account_age = calculate_account_age(account_created)
    
    first_name = getattr(user, 'first_name', 'Unknown')
    last_name = getattr(user, 'last_name', '')
    full_name = f"{first_name} {last_name}".strip() if last_name else first_name
    username = getattr(user, 'username', None)
    
    is_group_context = chat.type in [constants.ChatType.GROUP, constants.ChatType.SUPERGROUP]
    profile_type = "Bot's Profile Info" if is_bot else "User's Profile Info"
    
    text = (
        f"<b>🔍 Showing {profile_type} 📋</b>\n"
        "<b>━━━━━━━━━━━━━━━━</b>\n"
        f"<b>Full Name:</b> <b>{safe_escape(full_name)}</b>\n"
    )
    
    if username:
        text += f"<b>Username:</b> @{username}\n"
    
    text += f"<b>User ID:</b> <code>{user.id}</code>\n"
    
    if is_group_context:
        text += f"<b>Chat ID:</b> <code>{chat.id}</code>\n"
    
    if not is_bot:
        text += f"<b>Premium User:</b> <b>{premium_status}</b>\n"
    
    text += f"<b>Data Center:</b> <b>{dc_location}</b>\n"
    
    if not is_bot:
        text += (
            f"<b>Created On:</b> <b>{account_created_str}</b>\n"
            f"<b>Account Age:</b> <b>{account_age}</b>\n"
        )
    
    text += f"<b>Account Frozen:</b> <b>{'Yes' if is_restricted else 'No'}</b>\n"
    
    status = await get_status_text(user.id)
    
    if is_group_context:
        try:
            member = await bot.get_chat_member(chat.id, user.id)
            if member.status == constants.ChatMemberStatus.OWNER:
                status = f"{status} | 👑 Group Owner" if status else "👑 Group Owner"
            elif member.status == constants.ChatMemberStatus.ADMINISTRATOR:
                status = f"{status} | 🛡️ Admin" if status else "🛡️ Admin"
        except:
            pass

    if status:
        text += f"<b>Status:</b> {status}\n"
    
    try:
        pyro_user_full = await pbot.get_users(user_id)
        last_seen = "Unknown"
        if hasattr(pyro_user_full, 'status'):
            if str(pyro_user_full.status) == "UserStatus.ONLINE":
                last_seen = "Online"
            elif str(pyro_user_full.status) == "UserStatus.RECENTLY":
                last_seen = "Recently"
            elif str(pyro_user_full.status) == "UserStatus.LAST_WEEK":
                last_seen = "Last Week"
            elif str(pyro_user_full.status) == "UserStatus.LAST_MONTH":
                last_seen = "Last Month"
        text += f"<b>Users Last Seen:</b> <b>{last_seen}</b>\n"
    except:
        text += f"<b>Users Last Seen:</b> <b>Unknown</b>\n"

    bio = getattr(user, 'bio', None)
    if bio:
        text += f"<b>Bio:</b> <code>{safe_escape(bio)}</code>\n"
    
    text += (
        f"<b>Permanent Link:</b> <a href='tg://user?id={user.id}'>Click Here</a>\n"
        "<b>━━━━━━━━━━━━━━━━</b>\n"
        "<b>👁 Thank You for Using Our Tool ✅</b>"
    )

    keyboard = None
    try:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(f"📋 {full_name}", url=f"tg://user?id={user.id}")]])
    except:
        keyboard = None
   
    try:
        await msg.edit_text(text=text, parse_mode=constants.ParseMode.HTML, reply_markup=keyboard)
    except BadRequest as e:
        if "Button_user_privacy_restricted" in str(e):
            await msg.edit_text(text=text, parse_mode=constants.ParseMode.HTML)

@Command('id')
@disableable("id")
async def _getTelegramID(update, context):
    bot = context.bot
    message = update.effective_message
    reply = message.reply_to_message

    if len(message.text.split()) > 1:
        try:
            user_id = await extract_user(message)
            if not user_id:
                await message.reply_text("Couldn't find the user...")
                return

            user = await bot.get_chat(user_id)
            text = (f"👤 User: `{user.first_name}`\n"
                   f"🆔 User ID: `{user.id}`")

            try:
                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton(font("📢 Mention"), url=f"tg://user?id={user.id}")]]
                )
                await message.reply_text(text, parse_mode=constants.ParseMode.MARKDOWN, 
                                       reply_markup=keyboard)
            except BadRequest as e:
                if "Button_user_privacy_restricted" in str(e):
                    await message.reply_text(text, parse_mode=constants.ParseMode.MARKDOWN)
                else:
                    raise
        except Exception as e:
            await message.reply_text(f"❌ Error: `{str(e)}`", parse_mode=constants.ParseMode.MARKDOWN)
        return

    sender_id = message.sender_chat.id if message.sender_chat else message.from_user.id
    text = (f"👤 Your Tg ID: `{sender_id}`\n"
           f"💬 Chat ID: `{message.chat.id}`\n"
           f"📝 Msg ID: `{message.message_id}`")

    if reply:
        reply_sender_id = reply.sender_chat.id if reply.sender_chat else reply.from_user.id
        text += (f"\n👤 Replied Tg ID: `{reply_sender_id}`"
                f"\n📝 Replied Msg ID: `{reply.message_id}`")

        if reply.forward_origin:
            if getattr(reply.forward_origin, 'sender_user', None):
                text += f"\n👤 Forward Tg ID: `{reply.forward_origin.sender_user.id}`"
            elif getattr(reply.forward_origin, 'chat', None):
                text += f"\n📢 Forward Chat ID: `{reply.forward_origin.chat.id}`"

        media_type, media_id = get_media_id(reply)
        if media_type and media_id:
            text += f"\n📁 {media_type.capitalize()} ID: `{media_id}`"

    await message.reply_text(text=text, parse_mode=constants.ParseMode.MARKDOWN)
