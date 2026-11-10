from telegram import Update, ChatPermissions, MessageEntity, constants, InlineKeyboardButton, InlineKeyboardMarkup, helpers
from telegram.ext import ContextTypes, filters
import time
import re
import html
from AloneX import DEV_LIST, pbot, font
from AloneX.helpers.data.fonts import Fonts
from AloneX.db.approval_db import is_user_approved
from AloneX.helpers.decorator import Command, Messages, admin_check, only_groups, Callbacks, prefix_cmds, is_sudo_user_db
from pyrogram import filters as pfilters, enums, Client
from pyrogram.types import InlineKeyboardButton as PyroButton, InlineKeyboardMarkup as PyroMarkup, CallbackQuery as PyroCallbackQuery, Message
from pyrogram.enums import ButtonStyle
from AloneX.db.locks_db import (
    get_locks, update_lock, remove_lock, is_locked,
    remove_all_locks, set_lockwarn, get_lockwarn, set_adminlock, get_adminlock
)
from AloneX.db.warn_db import add_warn, get_warns, get_warn_limit, reset_warns, get_warn_action
from AloneX.helpers.log_helper import log_action
import asyncio

LOCK_TYPES = {
    'all': None, 'album': None, 'anonchannel': None, 'audio': 'can_send_audios',
    'bot': None, 'botlink': None, 'button': None, 'cashtag': None,
    'checklist': None, 'cjk': None, 'command': None, 'comment': None,
    'contact': None, 'cyrillic': None, 'document': 'can_send_documents',
    'email': None, 'emoji': None, 'emojicustom': None, 'emojigame': None,
    'emojionly': None, 'externalreply': None, 'forward': None,
    'forwardbot': None, 'forwardchannel': None, 'forwardstory': None,
    'forwarduser': None, 'game': None, 'gif': None, 'inline': None,
    'invitelink': None, 'location': None, 'phone': None, 'photo': 'can_send_photos',
    'poll': 'can_send_polls', 'rtl': None, 'spoiler': None, 'sticker': None,
    'stickeranimated': None, 'stickerpremium': None, 'text': 'can_send_messages',
    'url': None, 'video': 'can_send_videos', 'videonote': 'can_send_video_notes',
    'voice': 'can_send_voice_notes', 'zalgo': None, 'media': 'can_send_other_messages',
    'preview': 'can_add_web_page_previews', 'username': None, 'bots': None,
    'cmd': None, 'other': None
}

LOCK_DESCRIPTIONS = {
    'all': 'lock everything', 'album': 'media albums', 'anonchannel': 'anonymous channels',
    'audio': 'audio files', 'bot': 'messages from bots', 'botlink': 'bot username links (@examplebot or t.me/examplebot)',
    'button': 'inline buttons', 'cashtag': 'cash tags ($)', 'checklist': 'checklists',
    'cjk': 'chinese/japanese/korean text', 'command': 'all commands', 'comment': 'comments',
    'contact': 'contact cards', 'cyrillic': 'cyrillic/russian text', 'document': 'documents/files',
    'email': 'email addresses', 'emoji': 'all emojis', 'emojicustom': 'custom emojis',
    'emojigame': 'emoji dice games', 'emojionly': 'emoji-only messages', 'externalreply': 'external replies',
    'forward': 'all forwarded messages', 'forwardbot': 'forwards from bots', 'forwardchannel': 'forwards from channels',
    'forwardstory': 'forward stories', 'forwarduser': 'forwards from users', 'game': 'games',
    'gif': 'gifs/animations', 'inline': 'inline queries', 'invitelink': 'telegram group/channel invite links',
    'location': 'location sharing', 'phone': 'phone numbers', 'photo': 'photos/images',
    'poll': 'polls and quizzes', 'rtl': 'right-to-left text', 'spoiler': 'spoiler text',
    'sticker': 'all stickers', 'stickeranimated': 'animated stickers', 'stickerpremium': 'premium stickers',
    'text': 'text messages', 'url': 'url links', 'video': 'videos',
    'videonote': 'video notes/circles', 'voice': 'voice messages', 'zalgo': 'zalgo/corrupted text',
    'media': 'all media types', 'preview': 'link previews', 'username': 'username mentions (@)',
    'bots': 'messages sent by bots', 'cmd': 'command messages', 'other': 'other message types'
}

__module__ = "𝐋ᴏᴄᴋs🔒"

__help__ = """
❂ *locks module🔒*

❂ *commands*:
- `/locktypes` — display all lockable content types  
- `/lock <type>` — lock a type  
- `/unlock <type>` — unlock a type  
- `/locks` — show current lock status
- `/lockwarn <on/off>` — enable/disable warnings for locked content
- `/adminlock <on/off>` — apply locks to admins too
"""

BOT_START_TIME = int(time.time())

def should_process_message(message) -> bool:
    if not message or not message.date:
        return False
    message_time = int(message.date.timestamp())
    now = int(time.time())
    return message_time >= max(BOT_START_TIME, now - 10)

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        if not update.effective_user:
            return False
        member = await update.effective_chat.get_member(update.effective_user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

async def is_bot_admin(context, chat_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id, context.bot.id)
        return member.status in ("administrator", "creator") and member.can_delete_messages
    except Exception:
        return False

async def is_admin_pyro(user_id: int, chat_id: int):
    if user_id in DEV_LIST or await is_sudo_user_db(user_id):
        return True
    try:
        member = await pbot.get_chat_member(chat_id, user_id)
        return member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]
    except:
        return False

def get_valid_permissions(chat_info):
    permissions = chat_info.permissions.to_dict()
    return permissions

async def get_user_mention_fast(bot, chat_id, user_id):
    try:
        user_obj = await bot.get_chat_member(chat_id, user_id)
        return helpers.mention_html(user_id, user_obj.user.first_name)
    except:
        return f"<code>{user_id}</code>"

def has_cyrillic(text):
    return bool(re.search(r'[а-яА-ЯёЁ]', text))

def has_cjk(text):
    return bool(re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', text))

def has_rtl(text):
    return bool(re.search(r'[\u0590-\u05FF\u0600-\u06FF\u0700-\u074F]', text))

def has_zalgo(text):
    zalgo_chars = r'[\u0300-\u036F\u1AB0-\u1AFF\u1DC0-\u1DFF\u20D0-\u20FF\uFE20-\uFE2F]'
    return len(re.findall(zalgo_chars, text)) > 5

def is_emoji_only(text):
    emoji_pattern = r'[^\s\U0001F300-\U0001F9FF\u2600-\u27BF\u2B50\u2B55\u23E9-\u23F3\u23F8-\u23FA\u25AA-\u25FE\u2934-\u2935\u2B05-\u2B07\u3030\u303D\u3297\u3299]'
    return not bool(re.search(emoji_pattern, text.strip()))

def has_emoji(text):
    emoji_pattern = r'[\U0001F300-\U0001F9FF\u2600-\u27BF\u2B50\u2B55\u23E9-\u23F3\u23F8-\u23FA\u25AA-\u25FE\u2934-\u2935\u2B05-\u2B07\u3030\u303D\u3297\u3299]'
    return bool(re.search(emoji_pattern, text))

def extract_phone(text):
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    return bool(re.search(phone_pattern, text))

def extract_email(text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return bool(re.search(email_pattern, text))

def extract_cashtag(text):
    return bool(re.search(r'\$[A-Z]{1,6}\b', text))

def is_bot_link(text):
    bot_username_pattern = r'@\w+bot\b'
    bot_url_pattern = r't\.me/\w+bot\b'
    return bool(re.search(bot_username_pattern, text, re.IGNORECASE)) or bool(re.search(bot_url_pattern, text, re.IGNORECASE))

def is_invite_link(text):
    invite_patterns = [
        r't\.me/joinchat/',
        r't\.me/\+',
        r'telegram\.me/joinchat/',
        r'telegram\.dog/joinchat/'
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in invite_patterns)

def check_content_type(message, locked_set):
    if "all" in locked_set:
        return "all"
    
    if message.from_user and message.from_user.is_bot:
        if 'bot' in locked_set or 'bots' in locked_set:
            return 'bot'
    
    if message.forward_origin:
        if 'forward' in locked_set:
            return 'forward'
        origin_type = message.forward_origin.type
        if origin_type == "user" and 'forwarduser' in locked_set:
            return 'forwarduser'
        if origin_type == "channel" and 'forwardchannel' in locked_set:
            return 'forwardchannel'
        if origin_type == "hidden_user" and 'forwarduser' in locked_set:
            return 'forwarduser'
    
    if message.sender_chat:
        if message.sender_chat.type == "channel" and 'anonchannel' in locked_set:
            return 'anonchannel'
    
    if message.via_bot and 'forwardbot' in locked_set:
        return 'forwardbot'
    
    if message.sticker:
        if message.sticker.is_animated and 'stickeranimated' in locked_set:
            return 'stickeranimated'
        if hasattr(message.sticker, 'premium_animation') and message.sticker.premium_animation and 'stickerpremium' in locked_set:
            return 'stickerpremium'
        if 'sticker' in locked_set:
            return 'sticker'
    
    if message.photo and 'photo' in locked_set:
        return 'photo'
    if message.video and 'video' in locked_set:
        return 'video'
    if message.animation and 'gif' in locked_set:
        return 'gif'
    if message.audio and 'audio' in locked_set:
        return 'audio'
    if message.document and 'document' in locked_set:
        return 'document'
    if message.voice and 'voice' in locked_set:
        return 'voice'
    if message.video_note and 'videonote' in locked_set:
        return 'videonote'
    if message.poll and 'poll' in locked_set:
        return 'poll'
    if message.contact and 'contact' in locked_set:
        return 'contact'
    if message.location and 'location' in locked_set:
        return 'location'
    if message.game and 'game' in locked_set:
        return 'game'
    if message.dice and 'emojigame' in locked_set:
        return 'emojigame'
    
    if (message.photo or message.video or message.animation or message.audio or 
        message.document or message.voice or message.video_note) and 'media' in locked_set:
        return 'media'
    
    if message.reply_markup and ('button' in locked_set or 'inline' in locked_set):
        return 'button'
    
    if message.text or message.caption:
        text = message.text or message.caption
        
        if 'botlink' in locked_set and is_bot_link(text):
            return 'botlink'
        
        if 'invitelink' in locked_set and is_invite_link(text):
            return 'invitelink'
        
        if 'cyrillic' in locked_set and has_cyrillic(text):
            return 'cyrillic'
        if 'cjk' in locked_set and has_cjk(text):
            return 'cjk'
        if 'rtl' in locked_set and has_rtl(text):
            return 'rtl'
        if 'zalgo' in locked_set and has_zalgo(text):
            return 'zalgo'
        if 'emojionly' in locked_set and is_emoji_only(text):
            return 'emojionly'
        if 'emoji' in locked_set and has_emoji(text):
            return 'emoji'
        if 'phone' in locked_set and extract_phone(text):
            return 'phone'
        if 'email' in locked_set and extract_email(text):
            return 'email'
        if 'cashtag' in locked_set and extract_cashtag(text):
            return 'cashtag'
        
        entities = message.entities or message.caption_entities
        if entities:
            for e in entities:
                if e.type == MessageEntity.URL:
                    url_text = text[e.offset:e.offset + e.length]
                    if 'botlink' in locked_set and re.search(r'\w+bot\b', url_text, re.IGNORECASE):
                        return 'botlink'
                    if 'invitelink' in locked_set and is_invite_link(url_text):
                        return 'invitelink'
                    if 'url' in locked_set:
                        return 'url'
                    if 'preview' in locked_set:
                        return 'preview'
                
                if e.type == MessageEntity.TEXT_LINK:
                    if e.url:
                        if 'botlink' in locked_set and re.search(r'\w+bot\b', e.url, re.IGNORECASE):
                            return 'botlink'
                        if 'invitelink' in locked_set and is_invite_link(e.url):
                            return 'invitelink'
                    if 'url' in locked_set:
                        return 'url'
                
                if e.type in (MessageEntity.MENTION, MessageEntity.TEXT_MENTION):
                    mention_text = text[e.offset:e.offset + e.length]
                    if 'botlink' in locked_set and mention_text.lower().endswith('bot'):
                        return 'botlink'
                    if 'username' in locked_set:
                        return 'username'
                
                if e.type == MessageEntity.SPOILER and 'spoiler' in locked_set:
                    return 'spoiler'
                if e.type == MessageEntity.CUSTOM_EMOJI and 'emojicustom' in locked_set:
                    return 'emojicustom'
        
        if message.text and 'text' in locked_set:
            return 'text'
    
    return None

@pbot.on_message(pfilters.command("locktypes", prefix_cmds) & pfilters.group)
async def locktypes_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin_pyro(user_id, chat_id):
        return

    locked_items = await get_locks(chat_id)

    buttons = []
    row = []
    all_types = sorted(LOCK_TYPES.keys())
    
    for lock_type in all_types:
        is_locked_val = locked_items and (lock_type in locked_items or "all" in locked_items)
        status = "🔒 " if is_locked_val else ""
        style = ButtonStyle.SUCCESS if is_locked_val else ButtonStyle.DANGER
        row.append(PyroButton(f"{status}{font(lock_type.capitalize())}", callback_data=f"locktoggle#{lock_type}", style=style))
        if len(row) == 3:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)

    txt = "🔐 <b>available lock types</b>\n\n<i>tap any button to toggle</i>\n\n"
    if locked_items:
        txt += f"<b>currently locked ({len(locked_items)}):</b>\n<code>{', '.join(locked_items)}</code>"
    else:
        txt += "<i>no locks active</i>"

    await message.reply_text(
        txt, 
        parse_mode=enums.ParseMode.HTML,
        reply_markup=PyroMarkup(buttons)
    )

@pbot.on_callback_query(pfilters.regex("^locktoggle#"))
async def locktoggle_callback(client: Client, query: PyroCallbackQuery):
    from AloneX.helpers.decorator import get_effective_chat_id_pyro
    chat_id = await get_effective_chat_id_pyro(query)
    user_id = query.from_user.id

    if not await is_admin_pyro(user_id, chat_id):
        return await query.answer(font("This is for admins only!"), show_alert=True)

    lock_type = query.data.split("#")[1]
    locked_items = await get_locks(chat_id)
    
    if lock_type == 'all':
        if 'all' in locked_items:
            await remove_all_locks(chat_id)
            action = "unlocked"
        else:
            await update_lock(chat_id, 'all')
            action = "locked"
    else:
        if lock_type in locked_items:
            await remove_lock(chat_id, lock_type)
            action = "unlocked"
        else:
            await update_lock(chat_id, lock_type)
            action = "locked"

    # Update permissions
    if lock_type == 'all' or LOCK_TYPES.get(lock_type):
        try:
            new_locked_items = await get_locks(chat_id)
            from pyrogram.types import ChatPermissions as PyroChatPermissions

            is_all_locked = "all" in new_locked_items
            p_dict = {}

            # Map all lockable permissions based on current DB state
            for lt, p_attr in LOCK_TYPES.items():
                if p_attr:
                    # Permission is True (allowed) if 'all' is not locked AND specific type is not locked
                    p_dict[p_attr] = not (is_all_locked or lt in new_locked_items)

            if p_dict:
                await client.set_chat_permissions(chat_id, PyroChatPermissions(**p_dict))
        except Exception as e:
            print(f"Lock Toggle Perm Error: {e}")

    locked_items = await get_locks(chat_id)
    buttons = []
    row = []
    all_types = sorted(LOCK_TYPES.keys())

    for lt in all_types:
        is_locked_val = locked_items and (lt in locked_items or "all" in locked_items)
        status = "🔒 " if is_locked_val else ""
        style = ButtonStyle.SUCCESS if is_locked_val else ButtonStyle.DANGER
        row.append(PyroButton(f"{status}{font(lt.capitalize())}", callback_data=f"locktoggle#{lt}", style=style))
        if len(row) == 3:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    txt = "🔐 <b>available lock types</b>\n\n<i>tap any button to toggle</i>\n\n"
    if locked_items:
        txt += f"<b>currently locked ({len(locked_items)}):</b>\n<code>{', '.join(locked_items)}</code>"
    else:
        txt += "<i>no locks active</i>"

    try:
        await query.edit_message_text(
            txt,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=PyroMarkup(buttons)
        )
    except:
        pass
    
    await query.answer(f"{lock_type} {action}!")
    
    mention = f"<a href='tg://user?id={query.from_user.id}'>{html.escape(query.from_user.first_name)}</a>"
    log_text = f"{'🔒' if action == 'locked' else '🔓'} <b>{action.capitalize()} (via toggle)</b>\n" \
               f"<b>Group:</b> {html.escape(query.message.chat.title)}\n" \
               f"<b>Type:</b> {lock_type}\n" \
               f"<b>By:</b> {mention}"
    
    from AloneX import app as ptb_app
    asyncio.create_task(log_action(ptb_app.bot, chat_id, "locks", log_text))

async def apply_lock_action(update, context, action: str):
    chat = update.effective_chat
    bot = context.bot

    if not context.args:
        return await update.message.reply_text(
            f"❌ please specify what to {action}.\n\n"
            f"usage: `/{action} <type>` or `/{action} all`\n"
            f"example: `/{action} video`, `/{action} sticker`\n\n"
            f"use /locktypes to see all available types.",
            parse_mode=constants.ParseMode.MARKDOWN
        )

    permission = context.args[0].lower()
    if permission != 'all' and permission not in LOCK_TYPES:
        return await update.message.reply_text(
            f"❌ invalid {action} type: `{permission}`\n\n"
            f"use /locktypes to see all available types.",
            parse_mode=constants.ParseMode.MARKDOWN
        )

    try:
        chat_info = await bot.get_chat(chat.id)
        permissions = get_valid_permissions(chat_info)

        if action == "lock":
            if await is_locked(chat.id, permission):
                return await update.message.reply_text(
                    f"⚠️ `{permission}` is already locked!",
                    parse_mode=constants.ParseMode.MARKDOWN
                )

            if permission == 'all':
                for key in permissions:
                    permissions[key] = False
                await update_lock(chat.id, 'all')
                text = "🔒 <b>all content types</b>"
            else:
                telegram_perm = LOCK_TYPES[permission]
                if telegram_perm and telegram_perm in permissions:
                    permissions[telegram_perm] = False
                await update_lock(chat.id, permission)
                text = f"🔒 <code>{permission}</code>"

            await chat.set_permissions(ChatPermissions(**permissions))
            await update.message.reply_text(f"✅ <b>locked!</b> {text}", parse_mode=constants.ParseMode.HTML)

            log_text = f"🔒 <b>Lock</b>\n" \
                       f"<b>Group:</b> {helpers.escape(chat.title)}\n" \
                       f"<b>Type:</b> {permission}\n" \
                       f"<b>By:</b> {update.effective_user.mention_html()}"
            asyncio.create_task(log_action(context.bot, chat.id, "locks", log_text))

        else:
            if permission == 'all':
                locked_items = await get_locks(chat.id)
                if not locked_items:
                    return await update.message.reply_text(font("⚠️ nothing is locked!"))

                for key in permissions:
                    permissions[key] = True
                await remove_all_locks(chat.id)
                text = "🔓 <b>all content types</b>"
            else:
                if not await is_locked(chat.id, permission):
                    return await update.message.reply_text(
                        f"⚠️ `{permission}` is not locked!",
                        parse_mode=constants.ParseMode.MARKDOWN
                    )
                telegram_perm = LOCK_TYPES[permission]
                if telegram_perm and telegram_perm in permissions:
                    permissions[telegram_perm] = True
                await remove_lock(chat.id, permission)
                text = f"🔓 <code>{permission}</code>"

            await chat.set_permissions(ChatPermissions(**permissions))
            await update.message.reply_text(f"✅ <b>unlocked!</b> {text}", parse_mode=constants.ParseMode.HTML)

            log_text = f"🔓 <b>Unlock</b>\n" \
                       f"<b>Group:</b> {helpers.escape(chat.title)}\n" \
                       f"<b>Type:</b> {permission}\n" \
                       f"<b>By:</b> {update.effective_user.mention_html()}"
            asyncio.create_task(log_action(context.bot, chat.id, "locks", log_text))

    except Exception as e:
        error_msg = str(e)
        if "not enough rights" in error_msg.lower():
            await update.message.reply_text(font("❌ i need admin rights to change permissions!"))
        else:
            await update.message.reply_text(f"❌ error: <code>{error_msg}</code>", parse_mode=constants.ParseMode.HTML)

@Command("lock")
@only_groups
@admin_check("can_change_info", protect_target=False)
async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await apply_lock_action(update, context, "lock")

@Command("unlock")
@only_groups
@admin_check("can_restrict_members")
async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await apply_lock_action(update, context, "unlock")

@Command("locks")
@only_groups
@admin_check("can_change_info", protect_target=False)
async def locks_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    locked_items = await get_locks(chat_id)
    lockwarn_status = await get_lockwarn(chat_id)
    adminlock_status = await get_adminlock(chat_id)

    txt = "🔐 <b>lock status</b>\n\n"
    
    if locked_items:
        txt += f"<b>🔒 currently locked ({len(locked_items)}):</b>\n"
        for item in locked_items:
            desc = LOCK_DESCRIPTIONS.get(item, item)
            txt += f"• <code>{item}</code> - {desc}\n"
    else:
        txt += "<b>🔓 no locks active</b>\n"
    
    txt += f"\n<b>⚙️ settings:</b>\n"
    txt += f"• lockwarn: {'✅ enabled' if lockwarn_status else '❌ disabled'}\n"
    txt += f"• adminlock: {'✅ enabled (admins affected)' if adminlock_status else '❌ disabled (admins exempt)'}"

    await update.message.reply_text(txt, parse_mode=constants.ParseMode.HTML)

@Command("lockwarn")
@only_groups
@admin_check("can_restrict_members")
async def lockwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        current = await get_lockwarn(update.effective_chat.id)
        return await update.message.reply_text(
            f"<b>lockwarn status:</b> {'✅ enabled' if current else '❌ disabled'}\n\n"
            f"<b>usage:</b> <code>/lockwarn on|off</code>\n\n"
            f"<i>when enabled, users will receive warnings instead of silent deletion for locked content.</i>",
            parse_mode=constants.ParseMode.HTML
        )
    
    state = context.args[0].lower() in ['on', 'yes', 'true', 'enable']
    await set_lockwarn(update.effective_chat.id, state)
    
    await update.message.reply_text(
        f"✅ lockwarn {'enabled' if state else 'disabled'}.\n"
        f"users will now {'receive warnings' if state else 'have messages silently deleted'} for locked content.",
        parse_mode=constants.ParseMode.HTML
    )

@Command("adminlock")
@only_groups
@admin_check("can_restrict_members")
async def adminlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        current = await get_adminlock(update.effective_chat.id)
        return await update.message.reply_text(
            f"<b>adminlock status:</b> {'✅ enabled' if current else '❌ disabled'}\n\n"
            f"<b>usage:</b> <code>/adminlock on|off</code>\n\n"
            f"<i>when enabled, locks will apply to admins too (admins treated as normal users).</i>",
            parse_mode=constants.ParseMode.HTML
        )
    
    state = context.args[0].lower() in ['on', 'yes', 'true', 'enable']
    await set_adminlock(update.effective_chat.id, state)
    
    await update.message.reply_text(
        f"✅ adminlock {'enabled' if state else 'disabled'}.\n"
        f"locks will now {'apply to admins too' if state else 'exempt admins'}.",
        parse_mode=constants.ParseMode.HTML
    )
@Messages(filters=(filters.ALL) & ~filters.COMMAND, group=19)
async def delete_locked_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    
    if not user or not msg or not should_process_message(msg):
        return
    
    if user.id in DEV_LIST:
        return
    
    if await is_user_approved(chat.id, user.id):
        return
    
    adminlock_enabled = await get_adminlock(chat.id)
    if not adminlock_enabled:
        if await is_admin(update, context):
            return
    
    if not await is_bot_admin(context, chat.id):
        return
    
    try:
        locked_items = await get_locks(chat.id)
        if not locked_items:
            return
        
        locked_type = check_content_type(msg, set(locked_items))
        
        if not locked_type:
            return
        
        lockwarn_enabled = await get_lockwarn(chat.id)
        
        if lockwarn_enabled:
            lock_desc = LOCK_DESCRIPTIONS.get(locked_type, locked_type)
            reason = f"{locked_type} is locked in this chat"
            
            await add_warn(chat.id, user.id, reason)
            warns = await get_warns(chat.id, user.id)
            limit = await get_warn_limit(chat.id)
            
            if len(warns) >= limit:
                action = await get_warn_action(chat.id)
                user_mention = await get_user_mention_fast(context.bot, chat.id, user.id)
                await reset_warns(chat.id, user.id)
                
                try:
                    await msg.delete()
                except:
                    pass
                
                if action == "ban":
                    await chat.ban_member(user.id)
                    await context.bot.send_message(
                        chat.id,
                        f"🚫 {user_mention} banned after reaching {limit} warnings for locked content",
                        parse_mode=constants.ParseMode.HTML
                    )
                elif action == "kick":
                    await chat.ban_member(user.id)
                    await chat.unban_member(user.id)
                    await context.bot.send_message(
                        chat.id,
                        f"👋 {user_mention} removed after reaching {limit} warnings for locked content",
                        parse_mode=constants.ParseMode.HTML
                    )
                elif action == "mute":
                    await chat.restrict_member(user.id, ChatPermissions(can_send_messages=False))
                    await context.bot.send_message(
                        chat.id,
                        f"🔇 {user_mention} muted after reaching {limit} warnings for locked content",
                        parse_mode=constants.ParseMode.HTML
                    )
            else:
                try:
                    await msg.delete()
                except:
                    pass
                
                user_mention = await get_user_mention_fast(context.bot, chat.id, user.id)
                await context.bot.send_message(
                    chat.id,
                    f"⚠️ {user_mention} warned for sending locked content!\n"
                    f"🔒 <b>Reason:</b> {lock_desc}\n"
                    f"📊 <b>Warnings:</b> {len(warns)}/{limit}",
                    parse_mode=constants.ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(font("❌ Remove Warning"), callback_data=f"unwarn#{chat.id}#{user.id}")
                    ]])
                )
        else:
            try:
                await msg.delete()
            except Exception as e:
                print(f"Failed to delete message: {e}")
                
    except Exception as e:
        print(f"Error in delete_locked_content: {e}")

@Messages(filters=filters.COMMAND, group=20)
async def delete_locked_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    
    if not user or not msg or not should_process_message(msg):
        return
    
    if user.id in DEV_LIST:
        return
    
    if await is_user_approved(chat.id, user.id):
        return
    
    adminlock_enabled = await get_adminlock(chat.id)
    if not adminlock_enabled:
        if await is_admin(update, context):
            return
    
    if not await is_bot_admin(context, chat.id):
        return
    
    try:
        is_cmd_locked = (await is_locked(chat.id, 'cmd') or 
                        await is_locked(chat.id, 'command') or 
                        await is_locked(chat.id, 'all'))
        
        if not is_cmd_locked:
            return
        
        lockwarn_enabled = await get_lockwarn(chat.id)
        
        if lockwarn_enabled:
            reason = "command is locked in this chat"
            
            await add_warn(chat.id, user.id, reason)
            warns = await get_warns(chat.id, user.id)
            limit = await get_warn_limit(chat.id)
            
            if len(warns) >= limit:
                action = await get_warn_action(chat.id)
                user_mention = await get_user_mention_fast(context.bot, chat.id, user.id)
                await reset_warns(chat.id, user.id)
                
                try:
                    await msg.delete()
                except:
                    pass
                
                if action == "ban":
                    await chat.ban_member(user.id)
                    await context.bot.send_message(
                        chat.id,
                        f"🚫 {user_mention} banned after reaching {limit} warnings",
                        parse_mode=constants.ParseMode.HTML
                    )
                elif action == "kick":
                    await chat.ban_member(user.id)
                    await chat.unban_member(user.id)
                    await context.bot.send_message(
                        chat.id,
                        f"👋 {user_mention} removed after reaching {limit} warnings",
                        parse_mode=constants.ParseMode.HTML
                    )
                elif action == "mute":
                    await chat.restrict_member(user.id, ChatPermissions(can_send_messages=False))
                    await context.bot.send_message(
                        chat.id,
                        f"🔇 {user_mention} muted after reaching {limit} warnings",
                        parse_mode=constants.ParseMode.HTML
                    )
            else:
                try:
                    await msg.delete()
                except:
                    pass
                
                user_mention = await get_user_mention_fast(context.bot, chat.id, user.id)
                await context.bot.send_message(
                    chat.id,
                    f"⚠️ {user_mention} warned for using commands!\n"
                    f"🔒 <b>Reason:</b> Commands are locked\n"
                    f"📊 <b>Warnings:</b> {len(warns)}/{limit}",
                    parse_mode=constants.ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(font("❌ Remove Warning"), callback_data=f"unwarn#{chat.id}#{user.id}")
                    ]])
                )
        else:
            try:
                await msg.delete()
            except Exception as e:
                print(f"Failed to delete command: {e}")
                
    except Exception as e:
        print(f"Error in delete_locked_commands: {e}")
