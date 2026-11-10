from datetime import datetime
import random
import asyncio
import html
from typing import Optional, Tuple
from telegram import *
from telegram.ext import ChatMemberHandler
from telegram.error import BadRequest
from AloneX.helpers.message_helper import MessageHelper
from AloneX.helpers.utils import get_method_by_type, auto_delete 
from AloneX import OWNER_ID, font
from AloneX.helpers.decorator import ChatMembers
from AloneX.db.chats import add_chat, remove_chat, get_chat
from AloneX.db.users import add_user, update_users_status
from AloneX.db.greetings import (
    get_welcome, get_goodbye,
    get_welcome_status, get_goodbye_status,
    get_clean_welcome, get_clean_goodbye,
    set_last_welcome, get_last_welcome,
    set_last_goodbye, get_last_goodbye
)
from AloneX.db.federation_db import is_user_fban, get_chat_fed, is_quiet_fed, get_fed_info
from AloneX.helpers.log_helper import log_action

FLOOD_CONTROL_DELAY = 0.05
BULK_JOIN_THRESHOLD = 5
BULK_TIME_WINDOW = 10

last_welcome_messages = {}
last_goodbye_messages = {}
auto_delete_tasks = {}
bulk_join_tracker = {}

WEL_STRING = [
    "𝗛𝗲𝘆 𝗧𝗵𝗲𝗿𝗲 <b>{mention}</b> 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝗧𝗼 <b>{chatname}</b>! 𝗛𝗼𝘄 𝗔𝗿𝗲 𝗬𝗼𝘂?",
    "𝗛𝗲𝘆 𝗧𝗵𝗲𝗿𝗲 <b>{mention}</b> 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝗧𝗼 <b>{chatname}</b>! 𝗛𝗼𝘄 𝗔𝗿𝗲 𝗬𝗼𝘂?"
]

OWNER_WEL_STRING = [
    "👑 <b>ᴍʏ ᴏᴡɴᴇʀ ʜᴀs ᴀʀʀɪᴠᴇᴅ!</b> {mention} ᴊᴏɪɴᴇᴅ <b>{chatname}</b>. ᴛʜᴇ ʙᴏss ɪs ʜᴇʀᴇ!",
    "⭐ <b>ᴛʜᴇ ᴏᴡɴᴇʀ ɪs ʜᴇʀᴇ!</b> ᴡᴇʟᴄᴏᴍᴇ ʙᴀᴄᴋ {mention}! <b>{chatname}</b> ɪs ʜᴏɴᴏʀᴇᴅ ʙʏ ʏᴏᴜʀ ᴘʀᴇsᴇɴᴄᴇ!",
    "🎯 <b>ᴏᴡɴᴇʀ ᴅᴇᴛᴇᴄᴛᴇᴅ!</b> {mention} ʜᴀs ᴇɴᴛᴇʀᴇᴅ <b>{chatname}</b>. ᴀʟʟ ʜᴀɪʟ ᴛʜᴇ ᴍᴀsᴛᴇʀ!",
    "💎 <b>ᴛʜᴇ ʙᴏss ʜᴀs ᴀʀʀɪᴠᴇᴅ!</b> {mention} ᴊᴏɪɴᴇᴅ <b>{chatname}</b>. ᴍʏ ᴏᴡɴᴇʀ ɪs ʜᴇʀᴇ!"
]

LEFT_STRING = [
    "👋 {mention} ᴅᴇᴘᴀʀᴛᴇᴅ ғʀᴏᴍ <b>{chatname}</b>. ᴜɴᴛɪʟ ᴡᴇ ᴍᴇᴇᴛ ᴀɢᴀɪɴ!",
    "💫 <b>ғᴀʀᴇᴡᴇʟʟ</b> {mention}! <b>{chatname}</b> ᴡɪʟʟ ᴍɪss ʏᴏᴜ!",
    "🚪 {mention} ʜᴀs ʟᴇғᴛ! sᴀғᴇ ᴛʀᴀᴠᴇʟs!",
    "📖 ᴀɴᴏᴛʜᴇʀ ᴄʜᴀᴘᴛᴇʀ ᴇɴᴅs... {mention} ʟᴇғᴛ <b>{chatname}</b>",
    "✨ {mention} ᴠᴀɴɪsʜᴇᴅ! ɢᴏᴏᴅʙʏᴇ ғʀᴏᴍ <b>{chatname}</b>!"
]

BOT_ADDED_TEXT = "🤖 <b>ᴛʜᴀɴᴋs ғᴏʀ ᴀᴅᴅɪɴɢ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ!</b>\n\nᴛᴀᴘ ʙᴇʟᴏᴡ ᴛᴏ sᴇᴇ ᴀʟʟ ᴀᴠᴀɪʟᴀʙʟᴇ ᴄᴏᴍᴍᴀɴᴅs ⚡"

DEFAULT_WELCOME_TIME = 3000
DEFAULT_GOODBYE_TIME = 20

def is_valid_greeting(data):
    if not data:
        return False
    if not isinstance(data, dict):
        return False
    text = data.get('text')
    file_id = data.get('file_id')
    has_text = text and isinstance(text, str) and len(text.strip()) > 0
    has_file = file_id and isinstance(file_id, str) and len(file_id.strip()) > 0
    return has_text or has_file

def dict_to_keyboard(data):
    if not data or 'inline_keyboard' not in data:
        return None
    try:
        keyboard = [[InlineKeyboardButton(**button) for button in row] for row in data['inline_keyboard']]
        return InlineKeyboardMarkup(keyboard)
    except Exception as e:
        print(f"Error converting dict to keyboard: {e}")
        return None

def safe_get_user_name(user):
    if not user:
        return "Unknown User"
    if hasattr(user, 'full_name') and user.full_name:
        return user.full_name
    if hasattr(user, 'first_name') and user.first_name:
        return user.first_name
    if hasattr(user, 'username') and user.username:
        return f"@{user.username}"
    return f"User{user.id}" if hasattr(user, 'id') else "Unknown User"

def safe_mention_html(user):
    if not user:
        return "Unknown User"
    try:
        display_name = safe_get_user_name(user)
        if hasattr(user, 'id') and user.id:
            from html import escape
            return f'<a href="tg://user?id={user.id}">{escape(display_name)}</a>\u200b'
        else:
            return display_name
    except Exception as e:
        print(f"Error in safe_mention_html: {e}")
        return safe_get_user_name(user)

async def safe_delete_message(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id, message_id)
        return True
    except BadRequest as e:
        error_msg = str(e).lower()
        if "message to delete not found" not in error_msg and "message can't be deleted" not in error_msg:
            pass
    except Exception:
        pass
    return False

def extract_status_change(chat_member_update: ChatMemberUpdated) -> Optional[Tuple[bool, bool]]:
    if not chat_member_update:
        return None
    try:
        old_member = chat_member_update.old_chat_member
        new_member = chat_member_update.new_chat_member
        if not old_member or not new_member:
            return None
        old_status = old_member.status
        new_status = new_member.status
        old_is_member = getattr(old_member, 'is_member', None)
        new_is_member = getattr(new_member, 'is_member', None)
        was_member = old_status in [
            ChatMember.MEMBER, 
            ChatMember.OWNER, 
            ChatMember.ADMINISTRATOR
        ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
        is_member = new_status in [
            ChatMember.MEMBER, 
            ChatMember.OWNER, 
            ChatMember.ADMINISTRATOR
        ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)
        if was_member == is_member:
            return None
        return was_member, is_member
    except Exception as e:
        print(f"Error in extract_status_change: {e}")
        return None

def is_bulk_join(chat_id):
    current_time = datetime.now().timestamp()
    if chat_id not in bulk_join_tracker:
        bulk_join_tracker[chat_id] = []
    bulk_join_tracker[chat_id] = [timestamp for timestamp in bulk_join_tracker[chat_id] if current_time - timestamp <= BULK_TIME_WINDOW]
    bulk_join_tracker[chat_id].append(current_time)
    return len(bulk_join_tracker[chat_id]) > BULK_JOIN_THRESHOLD

def fix_username_display(username):
    if not username:
        return "None"
    clean_username = username.strip('@')
    if not clean_username:
        return "None"
    return f"@{clean_username}"

async def safe_send_message(bot, chat_id, text, max_retries=2, timeout=8, **kwargs):
    if 'parse_mode' not in kwargs:
        kwargs['parse_mode'] = "HTML"
    
    for attempt in range(max_retries):
        try:
            msg = await asyncio.wait_for(
                bot.send_message(chat_id, text, **kwargs),
                timeout=timeout
            )
            return msg
        except asyncio.TimeoutError:
            if attempt == max_retries - 1:
                print(f"Error safe_send_message: Timeout after {max_retries} attempts")
                return None
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Error safe_send_message: {e}")
            error_str = str(e).lower()
            if "flood" in error_str or "too many requests" in error_str:
                await asyncio.sleep(1)
                continue
            elif "chat not found" in error_str or "forbidden" in error_str:
                return None
            else:
                if attempt == max_retries - 1:
                    return None
                await asyncio.sleep(0.5)
    return None

async def smart_auto_delete(bot, chat_id, message_id, delay=20, message_type="welcome"):
    try:
        await asyncio.sleep(delay)
        await safe_delete_message(bot, chat_id, message_id)
        if message_type == "welcome" and chat_id in last_welcome_messages:
            if last_welcome_messages[chat_id] == message_id:
                del last_welcome_messages[chat_id]
        elif message_type == "goodbye" and chat_id in last_goodbye_messages:
            if last_goodbye_messages[chat_id] == message_id:
                del last_goodbye_messages[chat_id]
        if chat_id in auto_delete_tasks:
            del auto_delete_tasks[chat_id]
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Error smart_auto_delete: {e}")
        if chat_id in auto_delete_tasks:
            del auto_delete_tasks[chat_id]

async def instant_cleanup_messages(bot, chat_id, message_type=None):
    if chat_id in auto_delete_tasks:
        try:
            auto_delete_tasks[chat_id].cancel()
            del auto_delete_tasks[chat_id]
        except Exception as e:
            print(f"Error instant_cleanup_messages cancel: {e}")

    deleted_count = 0
    cleanup_targets = []

    if message_type == "welcome":
        cleanup_targets.append((last_welcome_messages, "welcome"))
    elif message_type == "goodbye":
        cleanup_targets.append((last_goodbye_messages, "goodbye"))
    else:
        cleanup_targets = [(last_welcome_messages, "welcome"), (last_goodbye_messages, "goodbye")]

    for msg_dict, m_type in cleanup_targets:
        message_id = msg_dict.get(chat_id)

        # Fallback to DB if not in memory
        if not message_id:
            if m_type == "welcome":
                message_id = await get_last_welcome(chat_id)
            else:
                message_id = await get_last_goodbye(chat_id)

        if message_id:
            try:
                asyncio.create_task(safe_delete_message(bot, chat_id, message_id))
                if chat_id in msg_dict:
                    del msg_dict[chat_id]
                deleted_count += 1
            except Exception as e:
                print(f"Error instant_cleanup_messages delete: {e}")

    return deleted_count

async def send_default_welcome(bot, chat_id, member_name, chat_title, is_owner=False):
    if is_owner:
        welcome_str = random.choice(OWNER_WEL_STRING)
    else:
        welcome_str = random.choice(WEL_STRING)

    chat_title_esc = html.escape(chat_title)
    formatted_text = welcome_str.replace('{mention}', member_name).replace('{chatname}', chat_title_esc)
    await asyncio.sleep(FLOOD_CONTROL_DELAY)
    msg = await safe_send_message(
        bot, chat_id, 
        formatted_text,
        parse_mode="HTML"
    )
    if msg:
        last_welcome_messages[chat_id] = msg.message_id
        await set_last_welcome(chat_id, msg.message_id)
        auto_delete_tasks[chat_id] = asyncio.create_task(
            smart_auto_delete(bot, chat_id, msg.message_id, DEFAULT_WELCOME_TIME, "welcome")
        )
    return msg

async def send_default_goodbye(bot, chat_id, member_name, chat_title):
    left_str = random.choice(LEFT_STRING)
    chat_title_esc = html.escape(chat_title)
    formatted_text = left_str.replace('{mention}', member_name).replace('{chatname}', chat_title_esc)
    await asyncio.sleep(FLOOD_CONTROL_DELAY)
    msg = await safe_send_message(
        bot, chat_id,
        formatted_text,
        parse_mode="HTML"
    )
    if msg:
        last_goodbye_messages[chat_id] = msg.message_id
        await set_last_goodbye(chat_id, msg.message_id)
        auto_delete_tasks[chat_id] = asyncio.create_task(
            smart_auto_delete(bot, chat_id, msg.message_id, DEFAULT_GOODBYE_TIME, "goodbye")
        )
    return msg

async def send_custom_greeting(bot, chat_id, data, member, chat, greeting_type="welcome"):
    original_text = data.get('text')
    text = None
    send_options = {}
    try:
        if original_text:
            text = MessageHelper.parse_random_content(original_text)
            text, send_options = await MessageHelper.convert_fillings(text, member, chat, None)
    except Exception as e:
        print(f"Error send_custom_greeting convert_fillings: {e}")
        text = original_text if original_text else None
    file_id = data.get('file_id')
    file_type = data.get('file_type')
    try:
        method = get_method_by_type(bot, file_type)
    except Exception as e:
        print(f"Error send_custom_greeting get_method_by_type: {e}")
        method = bot.send_message
    keyboard_data = data.get('keyboard')
    if data.get('has_rules_button'):
        try:
            from AloneX.db.rules import get_rules_button
            rules_button_text = await get_rules_button(chat_id) or "Rules"
            rules_button = {
                'text': rules_button_text,
                'url': f"https://t.me/{bot.username}?start=rules_{chat_id}"
            }
            if keyboard_data and 'inline_keyboard' in keyboard_data:
                if data.get('has_rules_same') and keyboard_data['inline_keyboard']:
                    keyboard_data['inline_keyboard'][-1].append(rules_button)
                else:
                    keyboard_data['inline_keyboard'].append([rules_button])
            else:
                keyboard_data = {'inline_keyboard': [[rules_button]]}
        except Exception as e:
            print(f"Error send_custom_greeting add rules button: {e}")
    keyboard = None
    try:
        if keyboard_data:
            keyboard = dict_to_keyboard(keyboard_data)
    except Exception as e:
        print(f"Error send_custom_greeting dict_to_keyboard: {e}")
        keyboard = None
    if not text or len(text.strip()) < 2:
        user_name = safe_get_user_name(member)
        text = f"Welcome {user_name}!" if greeting_type == "welcome" else f"Goodbye {user_name}!"
    await asyncio.sleep(FLOOD_CONTROL_DELAY)
    try:
        if file_type == "text" or not file_type:
            msg = await method(
                chat_id, 
                text=text, 
                reply_markup=keyboard, 
                parse_mode="HTML",
                **{k: v for k, v in send_options.items() if k in ['disable_web_page_preview', 'disable_notification', 'protect_content']}
            )
        else:
            media_kwargs = {'reply_markup': keyboard, 'parse_mode': 'HTML'}
            media_allowed_options = ['disable_notification', 'protect_content', 'has_spoiler']
            for key in media_allowed_options:
                if key in send_options:
                    media_kwargs[key] = send_options[key]
            if text and text.strip():
                msg = await method(chat_id, file_id, caption=text, **media_kwargs)
            else:
                msg = await method(chat_id, file_id, **media_kwargs)
        return msg
    except Exception as e:
        print(f"Error send_custom_greeting send message: {e}")
        try:
            if file_type == "text" or not file_type:
                msg = await method(chat_id, text=text, reply_markup=keyboard, parse_mode="HTML")
            else:
                if text and text.strip():
                    msg = await method(chat_id, file_id, caption=text, reply_markup=keyboard, parse_mode="HTML")
                else:
                    msg = await method(chat_id, file_id, reply_markup=keyboard)
            return msg
        except Exception as e2:
            print(f"Error send_custom_greeting retry: {e2}")
            try:
                user_name = safe_get_user_name(member)
                clean_text = f"Welcome {user_name}!" if greeting_type == "welcome" else f"Goodbye {user_name}!"
                msg = await safe_send_message(bot, chat_id, clean_text)
                return msg
            except Exception as e3:
                print(f"Error send_custom_greeting final fallback: {e3}")
        return None

async def send_custom_welcome(bot, chat_id, welcome, member, chat):
    msg = await send_custom_greeting(bot, chat_id, welcome, member, chat, "welcome")
    if msg:
        last_welcome_messages[chat_id] = msg.message_id
        await set_last_welcome(chat_id, msg.message_id)
        custom_time = int(welcome.get('time', DEFAULT_WELCOME_TIME)) if welcome.get('time') else DEFAULT_WELCOME_TIME
        auto_delete_tasks[chat_id] = asyncio.create_task(
            smart_auto_delete(bot, chat_id, msg.message_id, custom_time, "welcome")
        )
    return msg

async def send_custom_goodbye(bot, chat_id, goodbye, member, chat):
    msg = await send_custom_greeting(bot, chat_id, goodbye, member, chat, "goodbye")
    if msg:
        last_goodbye_messages[chat_id] = msg.message_id
        await set_last_goodbye(chat_id, msg.message_id)
        custom_time = int(goodbye.get('time', DEFAULT_GOODBYE_TIME)) if goodbye.get('time') else DEFAULT_GOODBYE_TIME
        auto_delete_tasks[chat_id] = asyncio.create_task(
            smart_auto_delete(bot, chat_id, msg.message_id, custom_time, "goodbye")
        )
    return msg

async def send_bot_added_message(bot, chat_id):
    await asyncio.sleep(FLOOD_CONTROL_DELAY)
    try:
        bot_username = bot.username if hasattr(bot, 'username') and bot.username else "bot"
        msg = await safe_send_message(
            bot, chat_id, BOT_ADDED_TEXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(font("Commands"), url=f"t.me/{bot_username}?start=help")]
            ]),
            parse_mode="HTML"
        )
        if msg:
            last_welcome_messages[chat_id] = msg.message_id
            await set_last_welcome(chat_id, msg.message_id)
            auto_delete_tasks[chat_id] = asyncio.create_task(
                smart_auto_delete(bot, chat_id, msg.message_id, 30, "welcome")
            )
        return msg
    except Exception as e:
        print(f"Error send_bot_added_message: {e}")
        return None

@ChatMembers(chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER, group=17)
async def track_chats(update: ChatMemberUpdated, context):
    bot = context.bot
    chat = update.effective_chat
    if chat.type == constants.ChatType.CHANNEL:
        return

    result = extract_status_change(update.my_chat_member)
    if result is None:
        return

    was_member, is_member = result
    user = update.effective_user
    mention = user.mention_html() if user else "Unknown"

    try:
        if chat.type == Chat.PRIVATE:
            if not was_member and is_member:
                await update_users_status([chat.id], True)
                text = (
                    "<b>Bot unblocked</b>\n"
                    f"User: {mention}\n"
                    f"ID: <code>{chat.id}</code>\n"
                    f"Time: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
                )
                # Global bot events stay in LOGS_CHANNEL or use log_action with chat.id
                asyncio.create_task(log_action(bot, chat.id, "admin", text))

            elif was_member and not is_member:
                await update_users_status([chat.id], False)
                text = (
                    "<b>Bot blocked</b>\n"
                    f"User: {mention}\n"
                    f"ID: <code>{chat.id}</code>\n"
                    f"Time: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
                )
                asyncio.create_task(log_action(bot, chat.id, "admin", text))

        elif chat.type in [Chat.GROUP, Chat.SUPERGROUP]:

            if chat.type == Chat.GROUP:
                try:
                    await bot.leave_chat(chat.id)
                    text = (
                        "<b>Left normal group</b>\n"
                        f"Name: {chat.title}\n"
                        f"ID: <code>{chat.id}</code>"
                    )
                    if LOGS_CHANNEL:
                        await bot.send_message(LOGS_CHANNEL, text, parse_mode="HTML")
                except Exception as e:
                    print(f"Error track_chats leave_chat: {e}")
                return

            if not was_member and is_member:
                try:
                    await add_chat(chat.id, chat.username)
                    username_display = fix_username_display(chat.username)
                    text = (
                        "<b>New chat joined</b>\n"
                        f"ID: <code>{chat.id}</code>\n"
                        f"Name: {chat.title}\n"
                        f"Username: {username_display}\n"
                        f"Type: {chat.type.title()}\n"
                        f"Date: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
                    )
                    if LOGS_CHANNEL:
                        asyncio.create_task(log_action(bot, chat.id, "admin", text))
                except Exception as e:
                    print(f"Error track_chats add_chat: {e}")

                await instant_cleanup_messages(bot, chat.id)
                await send_bot_added_message(bot, chat.id)

            elif was_member and not is_member:
                try:
                    username_display = fix_username_display(chat.username)
                    await remove_chat(chat.id)

                    cleanup_list = [
                        bulk_join_tracker,
                        last_welcome_messages,
                        last_goodbye_messages,
                        auto_delete_tasks
                    ]
                    for tracker in cleanup_list:
                        if chat.id in tracker:
                            try:
                                if hasattr(tracker[chat.id], "cancel"):
                                    tracker[chat.id].cancel()
                                del tracker[chat.id]
                            except Exception as e:
                                print(f"Error track_chats cleanup: {e}")

                    text = (
                        "<b>Chat removed</b>\n"
                        f"ID: <code>{chat.id}</code>\n"
                        f"Name: {chat.title}\n"
                        f"Username: {username_display}\n"
                        f"Date: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
                    )
                    if LOGS_CHANNEL:
                        asyncio.create_task(log_action(bot, chat.id, "admin", text))

                except Exception as e:
                    print(f"Error track_chats remove_chat: {e}")

    except Exception as e:
        print(f"Error track_chats: {e}")
        
@ChatMembers(chat_member_types=ChatMemberHandler.CHAT_MEMBER, group=-130)
async def WelcomeMembers(update, context):
    bot = context.bot
    chat = update.effective_chat
    chat_id = chat.id
    if not chat or chat.type == constants.ChatType.CHANNEL:
        return
    result = extract_status_change(update.chat_member)
    if result is None:
        return
    was_member, is_member = result
    if not update.chat_member or not update.chat_member.new_chat_member:
        return
    member = update.chat_member.new_chat_member.user
    if not member:
        return
    member_name = safe_mention_html(member)
    member_data = {
        "id": member.id,
        "first_name": member.first_name if member.first_name else "Unknown",
        "username": member.username if member.username else None
    }
    is_owner = member.id == OWNER_ID if OWNER_ID else False
    try:
        if not was_member and is_member:
            # Log Join
            log_text = f"📥 <b>User Joined</b>\n" \
                       f"<b>Group:</b> {html.escape(chat.title)}\n" \
                       f"<b>User:</b> {member_name} (<code>{member.id}</code>)"
            asyncio.create_task(log_action(bot, chat_id, "joins", log_text))

            # Federation check
            fed_id = await get_chat_fed(chat_id)
            if fed_id:
                is_banned, reason = await is_user_fban(fed_id, member.id)
                if is_banned:
                    try:
                        await chat.ban_member(member.id)
                        if not await is_quiet_fed(chat_id):
                            await bot.send_message(chat_id, f"🚫 <b>Fed Ban Detected!</b>\n{member_name} has been banned from the chat because they are banned in the federation.\n<b>Reason:</b> {reason}", parse_mode='HTML')

                        # Log to log channel
                        log_text = f"🚫 <b>Fed Ban (on join)</b>\n" \
                                   f"<b>Group:</b> {html.escape(chat.title)}\n" \
                                   f"<b>User:</b> {member_name} (<code>{member.id}</code>)\n" \
                                   f"<b>Reason:</b> {reason}"
                        asyncio.create_task(log_action(bot, chat_id, "bans", log_text))

                        # Log to federation log if set
                        fed = await get_fed_info(fed_id)
                        if fed and fed.get('log_channel'):
                            try:
                                await bot.send_message(fed['log_channel'], f"🚫 <b>Fed Ban Action</b>\n<b>User:</b> {member_name} (<code>{member.id}</code>)\n<b>Chat:</b> {chat.title}\n<b>Reason:</b> {reason}", parse_mode='HTML')
                            except: pass
                        return # Stop processing welcome
                    except Exception as e:
                        print(f"Error banning fbaned user: {e}")

            try:
                await add_chat(chat_id)
            except Exception as e:
                print(f"Error WelcomeMembers add_chat: {e}")
            if not member.is_bot:
                try:
                    await add_user(member_data, active=False)
                except Exception as e:
                    print(f"Error WelcomeMembers add_user: {e}")
            if is_bulk_join(chat_id):
                return
            try:
                welcome_enabled = await get_welcome_status(chat_id)
            except Exception as e:
                print(f"Error WelcomeMembers get_welcome_status: {e}")
                welcome_enabled = True
            if not welcome_enabled:
                return

            if await get_clean_welcome(chat_id):
                await instant_cleanup_messages(bot, chat_id, "welcome")

            welcome_data = {}
            try:
                welcome_data = await get_welcome(chat_id)
            except Exception as e:
                print(f"Error WelcomeMembers get_welcome: {e}")
                welcome_data = {}
            if not is_valid_greeting(welcome_data):
                await send_default_welcome(bot, chat_id, member_name, chat.title, is_owner)
            else:
                await send_custom_welcome(bot, chat_id, welcome_data, member, chat)
        elif was_member and not is_member:
            # Log Leave
            log_text = f"📤 <b>User Left</b>\n" \
                       f"<b>Group:</b> {html.escape(chat.title)}\n" \
                       f"<b>User:</b> {member_name} (<code>{member.id}</code>)"
            asyncio.create_task(log_action(bot, chat_id, "leaves", log_text))

            if is_bulk_join(chat_id):
                return
            try:
                goodbye_enabled = await get_goodbye_status(chat_id)
            except Exception as e:
                print(f"Error WelcomeMembers get_goodbye_status: {e}")
                goodbye_enabled = False
            if not goodbye_enabled:
                return

            if await get_clean_goodbye(chat_id):
                await instant_cleanup_messages(bot, chat_id, "goodbye")

            goodbye_data = {}
            try:
                goodbye_data = await get_goodbye(chat_id)
            except Exception as e:
                print(f"Error WelcomeMembers get_goodbye: {e}")
                goodbye_data = {}
            if not is_valid_greeting(goodbye_data):
                await send_default_goodbye(bot, chat_id, member_name, chat.title)
            else:
                await send_custom_goodbye(bot, chat_id, goodbye_data, member, chat)
    except Exception as e:
        print(f"Error WelcomeMembers: {e}")

async def cleanup_on_shutdown():
    for task in auto_delete_tasks.values():
        try:
            task.cancel()
        except:
            pass
    cleanup_dicts = [bulk_join_tracker, last_welcome_messages, last_goodbye_messages, auto_delete_tasks]
    for d in cleanup_dicts:
        d.clear()
