import re
from html import escape
import time
import asyncio
import html
import os
from cachetools import TTLCache
from telegram.ext import ContextTypes, CallbackContext, filters, CallbackQueryHandler, filters
from telegram import Update, error, ChatPermissions, constants, ChatMemberOwner, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import mention_html
from AloneX.helpers.utils import extract_user, async_cache
from AloneX.helpers.decorator import Command, admin_check, only_groups, disableable, protect_sudos, Callbacks, Messages, mod_permission, get_effective_chat_id
from AloneX import BOT_ID, app, pbot, font
from pyrogram import enums
from pyrogram.enums import ChatMembersFilter, ParseMode, ChatMemberStatus
from AloneX.db.mod import *
from AloneX.helpers.log_helper import log_action
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup as IKM, InlineKeyboardButton as IKB
from pyrogram.errors import RPCError
from AloneX import pbot, prefix_cmds
import io
from AloneX.db.admincache import get_last_admins, save_admins
from AloneX.db.connection_db import get_connected_chat

MAX_MESSAGE_LENGTH = 4096

_cache_cleanup_task = None

async def _periodic_cache_cleanup():
    while True:
        await asyncio.sleep(300)
        try:
            admin_cache.clear()
            member_cache.clear()
            chat_cache.clear()
            report_cache.clear()
        except:
            pass

def start_admin_cache_cleanup():
    global _cache_cleanup_task
    if _cache_cleanup_task is None:
        _cache_cleanup_task = asyncio.create_task(_periodic_cache_cleanup())

__module__ = "𝐀ᴅᴍɪɴ🛠️"
__help__ = """
*Admin 🛠️ — Group management made simple*

*Member & moderation*
• `/kick <reply|user>` — Remove a member.  
• `/dkick <reply|user>` — Kick + delete recent messages.  
• `/ban <reply|user>` — Ban a user from the group.  
• `/dban <reply|user>` — Ban + remove recent messages.  
• `/unban <user_id|username>` — Lift a ban.  
• `/warn <reply|user>` — Add a warning (dummy).  
• `/dwarn <reply|user>` — Dummy warn with custom note.  
• `/purge` — Delete messages from replied message onward (use reply to start).  
• `/del` — Delete the replied message.

*Admins & roles*
• `/promote <reply|user>` — Promote with standard rights.  
• `/lowpromote <reply|user>` — Promote with restricted rights.  
• `/fullpromote <reply|user>` — Give full admin powers.  
• `/demote <reply|user>` — Remove admin rights.  
• `/adminlist` — Show current admins and their rights.  
• `/settitle <reply|user> <title>` — Set admin custom title.
• `/invite` — Generate group invite link.
• `/reloadadmin` — Refresh cached admin list (use when permissions changed).

*Short examples:*  
`/kick @username` — kick by username  
Reply to a message + `/ban` — ban that user  
`/settitle @user Moderator` — set admin title
"""

report_cache = TTLCache(maxsize=5000, ttl=60)
admin_cache = TTLCache(maxsize=1000, ttl=300)
member_cache = TTLCache(maxsize=10000, ttl=300)
chat_cache = TTLCache(maxsize=1000, ttl=600)

def clear_all_caches():
    admin_cache.clear()
    member_cache.clear()
    chat_cache.clear()
    report_cache.clear()

def clear_chat_cache(chat_id=None):
    if chat_id:
        chat_cache.pop(chat_id, None)
        for key in list(member_cache.keys()):
            if key[0] == chat_id:
                member_cache.pop(key, None)
        for key in list(admin_cache.keys()):
            if key[0] == chat_id:
                admin_cache.pop(key, None)
    else:
        clear_all_caches()

def invalidate_member_cache(chat_id, user_id):
    key = (chat_id, user_id)
    member_cache.pop(key, None)
    admin_cache.pop(key, None)

def mention_html(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{html.escape(name)}</a>'
    
async def get_admin_cached(bot, chat_id, user_id, *, force_refresh=False):
    key = (chat_id, user_id)
    if not force_refresh:
        cached = admin_cache.get(key)
        if cached is not None:
            return cached
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        result = member.status in [constants.ChatMemberStatus.ADMINISTRATOR, constants.ChatMemberStatus.OWNER]
        admin_cache[key] = result
        return result
    except Exception:
        admin_cache.pop(key, None)
        return False

async def reload_admins_cache(bot, chat_id):
    keys_to_remove = [k for k in admin_cache.keys() if k[0] == chat_id]
    for key in keys_to_remove:
        admin_cache.pop(key, None)
    
    keys_to_remove = [k for k in member_cache.keys() if k[0] == chat_id]
    for key in keys_to_remove:
        member_cache.pop(key, None)

async def get_member_cached(bot, chat_id, user_id, *, force_refresh=False):
    key = (chat_id, user_id)
    if not force_refresh:
        cached = member_cache.get(key)
        if cached is not None:
            return cached
    try:
        result = await bot.get_chat_member(chat_id, user_id)
        member_cache[key] = result
        return result
    except Exception:
        member_cache.pop(key, None)
        raise

async def get_chat_cached(bot, chat_id, *, force_refresh=False):
    if not force_refresh:
        cached = chat_cache.get(chat_id)
        if cached is not None:
            return cached
    try:
        result = await bot.get_chat(chat_id)
        chat_cache[chat_id] = result
        return result
    except Exception:
        chat_cache.pop(chat_id, None)
        raise

@Command('purge')
@only_groups
@disableable("purge")
@mod_permission("delete", protect_target=False)
async def PurgeMsg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    reply = message.reply_to_message
    bot = context.bot
    
    if not reply:
        return await message.reply_text(font("*Reply to a message for start purge!*"), parse_mode=constants.ParseMode.MARKDOWN)
    
    message_ids = list(range(reply.message_id, message.message_id + 1))
    
    if len(message_ids) > 300:
        return await message.reply_text(font("*You cannot delete more than 300 messages at once! but try 299 🧏*"), parse_mode=constants.ParseMode.MARKDOWN)
    
    start = time.perf_counter()
    
    try:
        await pbot.delete_messages(chat_id=message.chat.id, message_ids=message_ids)
        deleted_count = len(message_ids)
    except Exception:
        deleted_count = 0
        for msg_id in message_ids:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
                deleted_count += 1
                if deleted_count % 20 == 0:
                    await asyncio.sleep(0.2)
            except Exception:
                pass
    
    ping = round(time.perf_counter() - start, 3)
    msg = await bot.send_message(chat_id=message.chat.id, text=f"`Successfully deleted {deleted_count} messages within {ping}(s)`.", parse_mode=constants.ParseMode.MARKDOWN)
    
    chat_id = await get_effective_chat_id(update)
    title = update.effective_chat.title
    if chat_id != update.effective_chat.id:
        try:
            target_chat = await context.bot.get_chat(chat_id)
            title = target_chat.title
        except:
            title = str(chat_id)

    log_text = f"🧹 <b>Purge</b>\n" \
               f"<b>Group:</b> {html.escape(title)}\n" \
               f"<b>Messages Deleted:</b> {deleted_count}\n" \
               f"<b>By:</b> {update.effective_user.mention_html()}\n" \
               f"<b>Time Taken:</b> {ping}s"
    asyncio.create_task(log_action(context.bot, chat_id, "cleans", log_text))

    await asyncio.sleep(5)
    try:
        await msg.delete()
    except:
        pass

@Command(['setcdes', 'setchatdes'])
@disableable(['setcdes', 'setchatdes'])
@admin_check("can_change_info", protect_target=False)
async def setChatDescription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    bot = context.bot
    chat_id = await get_effective_chat_id(update)
    
    description = ' '.join(context.args) if context.args else ''
    if not description:
        return await m.reply_text(font('✋ *Provide some text to set it as chat description*. e.g: `/setcdes Support Chat`'), parse_mode=constants.ParseMode.MARKDOWN)
    
    try:
        await bot.set_chat_description(chat_id, description[:254])
        clear_chat_cache(chat_id)
        await get_chat_cached(bot, chat_id, force_refresh=True)
        await m.reply_text(font('✨ *Chat Description Updated!*'), parse_mode=constants.ParseMode.MARKDOWN)

        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        log_text = f"🛠️ <b>Chat Description Updated</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}\n" \
                   f"<b>New Description:</b> {html.escape(description[:100])}..."
        asyncio.create_task(log_action(context.bot, chat_id, "admin", log_text))
    except Exception as e:
        return await m.reply_text(f'❌ Error: {html.escape(str(e))}', parse_mode=constants.ParseMode.HTML)

@Command(['setct', 'setchattitle'])
@admin_check("can_change_info", protect_target=False)
async def setChatTitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    bot = context.bot
    chat_id = await get_effective_chat_id(update)
    
    title_text = ' '.join(context.args) if context.args else ''
    if not title_text:
        return await m.reply_text(font('✋ *Provide some text to set it as chat title*. e.g: `/setct Support Chat`'), parse_mode=constants.ParseMode.MARKDOWN)
    
    try:
        await bot.set_chat_title(chat_id, title_text[:127])
        clear_chat_cache(chat_id)
        await get_chat_cached(bot, chat_id, force_refresh=True)
        await m.reply_text(font('✨ *Chat title Updated!*'), parse_mode=constants.ParseMode.MARKDOWN)

        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        log_text = f"🛠️ <b>Chat Title Updated</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}\n" \
                   f"<b>New Title:</b> {html.escape(title_text)}"
        asyncio.create_task(log_action(context.bot, chat_id, "admin", log_text))
    except Exception as e:
        return await m.reply_text(f'❌ Error: {html.escape(str(e))}', parse_mode=constants.ParseMode.HTML)

@Command(['rmcp', 'rmchatphoto'])
@admin_check("can_change_info", protect_target=False)
async def removeChatPhoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    bot = context.bot
    chat_id = await get_effective_chat_id(update)
    
    try:
        await bot.delete_chat_photo(chat_id)
        clear_chat_cache(chat_id)
        await get_chat_cached(bot, chat_id, force_refresh=True)
        await m.reply_text(font('*✨ Chat Photo Removed!*'), parse_mode=constants.ParseMode.MARKDOWN)

        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        log_text = f"🖼️ <b>Chat Photo Removed</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}"
        asyncio.create_task(log_action(context.bot, chat_id, "admin", log_text))
    except Exception as e:
        return await m.reply_text(f'❌ Error: {html.escape(str(e))}', parse_mode=constants.ParseMode.HTML)

@Command(['setcp', 'setchatphoto'])
@admin_check("can_change_info", protect_target=False)
async def setChatPhoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    bot = context.bot
    chat_id = await get_effective_chat_id(update)
    
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply_text(font('✋ Reply to photo!'))
    
    if m.reply_to_message and m.reply_to_message.photo:
        file = await bot.get_file(m.reply_to_message.photo[-1])
        photo_path = await file.download_to_drive()
        try:
            await bot.set_chat_photo(chat_id, photo=photo_path)
            clear_chat_cache(chat_id)
            await get_chat_cached(bot, chat_id, force_refresh=True)
            await m.reply_text(font('*✨ New photo has been updated!*'), parse_mode=constants.ParseMode.MARKDOWN)

            title = update.effective_chat.title
            if chat_id != update.effective_chat.id:
                try:
                    target_chat = await context.bot.get_chat(chat_id)
                    title = target_chat.title
                except:
                    title = str(chat_id)

            log_text = f"🖼️ <b>Chat Photo Updated</b>\n" \
                       f"<b>Group:</b> {html.escape(title)}\n" \
                       f"<b>By:</b> {update.effective_user.mention_html()}"
            asyncio.create_task(log_action(context.bot, chat_id, "admin", log_text))
        except Exception as e:
            return await m.reply_text(f'❌ Error: {html.escape(str(e))}', parse_mode=constants.ParseMode.HTML)
        finally:
            if os.path.exists(photo_path):
                os.remove(photo_path)

@Command('demote')
@disableable("demote")
@admin_check("can_promote_members", protect_target=False)
async def demoteChatMember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    bot = context.bot
    chat_id = await get_effective_chat_id(update)
    
    user_id = await extract_user(message, self=False)
    if not user_id:
        return await message.reply_text(text="🙋 *Reply to a user or give their telegram ID!*", parse_mode=constants.ParseMode.MARKDOWN)
    
    try:
        member = await get_member_cached(bot, chat_id, user_id, force_refresh=True)
        if member.status not in [constants.ChatMemberStatus.ADMINISTRATOR]:
            return await message.reply_text(text="❌ *User is not an admin!*", parse_mode=constants.ParseMode.MARKDOWN)
        if member.status == constants.ChatMemberStatus.OWNER:
            return await message.reply_text(text="❌ *Cannot demote the group owner!*", parse_mode=constants.ParseMode.MARKDOWN)
    except Exception:
        return await message.reply_text(text="❌ *User not found or error fetching member info!*", parse_mode=constants.ParseMode.MARKDOWN)
    
    try:
        await bot.promote_chat_member(
            chat_id, member.user.id,
            can_change_info=False, can_delete_messages=False, can_invite_users=False,
            can_restrict_members=False, can_pin_messages=False, can_promote_members=False,
            can_manage_chat=False, can_manage_video_chats=False, is_anonymous=False
        )
        invalidate_member_cache(chat_id, user_id)
        await reload_admins_cache(bot, chat_id)
        mention = mention_html(member.user.id, member.user.first_name)
        await message.reply_text(text=f"<b>Successfully demoted {'bot' if member.user.is_bot else 'user'} {mention}!</b>", parse_mode=constants.ParseMode.HTML)

        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        log_text = f"👮 <b>Demoted</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>User:</b> {mention} (<code>{user_id}</code>)\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}"
        asyncio.create_task(log_action(context.bot, chat_id, "admin", log_text))
    except Exception as e:
        error_msg = str(e)
        if "USER_CREATOR" in error_msg:
            error_msg = "Cannot demote the group creator."
        elif "CHAT_ADMIN_REQUIRED" in error_msg or "Chat_admin_required" in error_msg:
            error_msg = "Bot needs admin rights with 'Add Admins' permission."
        elif "USER_NOT_PARTICIPANT" in error_msg:
            error_msg = "User is not in the group."
        return await message.reply_text(text=f"❌ Error: {html.escape(error_msg)}", parse_mode=constants.ParseMode.HTML)

@Command(('pin', 'unpin'))
@only_groups
@disableable('pin')
@disableable('unpin')
@admin_check("can_pin_messages", protect_target=False)
async def PinChatMsg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    reply = message.reply_to_message
    
    if not reply:
        return await message.reply_text(font("🤷 Reply to a message to pin or unpin it."))
    
    command = message.text.split()[0][1:]
    
    try:
        if command == 'pin':
            await reply.pin()
        else:
            await reply.unpin()
        
        if reply.chat.username:
            link = f"https://t.me/{reply.chat.username}/{reply.message_id}"
        else:
            chat_id_short = str(reply.chat.id).replace("-100", "")
            link = f"https://t.me/c/{chat_id_short}/{reply.message_id}"
        
        text = f"<b>Successfully <a href='{link}'>Message</a> {command.capitalize()}ed!</b>"
        await message.reply_text(text=text, parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True)

        chat_id = await get_effective_chat_id(update)
        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        log_text = f"📌 <b>{command.capitalize()}</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>Message:</b> <a href='{link}'>Link</a>\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}"
        asyncio.create_task(log_action(context.bot, chat_id, "admin", log_text))
    except Exception as e:
        await message.reply_text(f"❌ Error: {html.escape(str(e))}", parse_mode=constants.ParseMode.HTML)

@Command('del')
@only_groups
@mod_permission("delete", protect_target=False)
@disableable('del')
async def delete_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    reply = message.reply_to_message
    
    if not reply:
        return await message.reply_text(font("What should I delete?"))
    
    try:
        await reply.delete()
        await message.delete()

        chat_id = await get_effective_chat_id(update)
        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        log_text = f"🗑️ <b>Message Deleted</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}"
        asyncio.create_task(log_action(context.bot, chat_id, "cleans", log_text))
    except error.TelegramError as e:
        return await message.reply_text(f"❌ Error: {html.escape(str(e))}", parse_mode=constants.ParseMode.HTML)

@Command(['reload', 'reloadadmin'])
@admin_check()
async def reload_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_id = await get_effective_chat_id(update)
    user_id = message.from_user.id
    bot = context.bot
    
    cooldown_key = f"reload_{chat_id}"
    current_time = time.time()
    
    if cooldown_key in context.bot_data:
        last_used = context.bot_data[cooldown_key]
        time_left = 180 - (current_time - last_used)
        
        if time_left > 0:
            mins = int(time_left // 60)
            secs = int(time_left % 60)
            return await message.reply_text(
                f"⏱️ ᴄᴏᴏʟᴅᴏᴡɴ ᴀᴄᴛɪᴠᴇ\n"
                f"ᴡᴀɪᴛ <code>{mins}ᴍ {secs}ꜱ</code>",
                parse_mode=constants.ParseMode.HTML
            )
    
    msg = await message.reply_text(
        "🔄 ʀᴇꜰʀᴇꜱʜɪɴɢ ᴄᴀᴄʜᴇ...", 
        parse_mode=constants.ParseMode.HTML
    )
    
    try:
        from AloneX.helpers.cache_manager import smart_cache_refresh
        from AloneX import pbot
        
        await smart_cache_refresh(bot, chat_id, user_id, client=pbot)
        
        await msg.edit_text(
            "✅ ᴀᴅᴍɪɴ ᴄᴀᴄʜᴇ ʀᴇꜰʀᴇꜱʜᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ",
            parse_mode=constants.ParseMode.HTML
        )
        context.bot_data[cooldown_key] = current_time
        
    except Exception as e:
        await msg.edit_text(
            f"❌ ᴇʀʀᴏʀ: <code>{html.escape(str(e)[:50])}</code>", 
            parse_mode=constants.ParseMode.HTML
        )

@Command('invitelink')
@disableable('invitelink')
@admin_check('can_invite_users', protect_target=False)
async def GetInvite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    bot = context.bot
    chat_id = await get_effective_chat_id(update)
    
    try:
        chat = await get_chat_cached(bot, chat_id)
        link = chat.invite_link
        if not link:
            link = await bot.export_chat_invite_link(chat_id)
        await message.reply_text(text=f"<b>✨ {html.escape(chat.title)} Invite Link</b>:\n{link}", parse_mode=constants.ParseMode.HTML)
    except Exception as e:
        await message.reply_text(f"❌ Error: {html.escape(str(e))}", parse_mode=constants.ParseMode.HTML)

async def get_bot_permissions(bot, chat_id):
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        if bot_member.status not in [constants.ChatMemberStatus.ADMINISTRATOR, constants.ChatMemberStatus.OWNER]:
            return {}
        
        return {
            'can_change_info': bot_member.can_change_info or False,
            'can_delete_messages': bot_member.can_delete_messages or False,
            'can_invite_users': bot_member.can_invite_users or False,
            'can_restrict_members': bot_member.can_restrict_members or False,
            'can_pin_messages': bot_member.can_pin_messages or False,
            'can_promote_members': bot_member.can_promote_members or False,
            'can_manage_chat': bot_member.can_manage_chat or False,
            'can_manage_video_chats': bot_member.can_manage_video_chats or False,
            'can_manage_topics': getattr(bot_member, 'can_manage_topics', False),
            'can_post_stories': getattr(bot_member, 'can_post_stories', False),
            'can_edit_stories': getattr(bot_member, 'can_edit_stories', False),
            'can_delete_stories': getattr(bot_member, 'can_delete_stories', False)
        }
    except Exception:
        return {}


@Command(('promote', 'fullpromote', 'lowpromote'))
@disableable('promote')
@admin_check("can_promote_members", protect_target=False)
async def promoteChatMember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    bot = context.bot
    chat_id = await get_effective_chat_id(update)
    
    command = message.text.split()[0][1:].lower()
    
    user_id = None
    admin_title = None
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        if context.args:
            admin_title = ' '.join(context.args).strip()[:16]
    else:
        if message.entities:
            for entity in message.entities:
                if entity.type == constants.MessageEntityType.TEXT_MENTION and entity.user:
                    user_id = entity.user.id
                    full_text = message.text
                    mention_start = entity.offset
                    mention_end = entity.offset + entity.length
                    after_mention = full_text[mention_end:].strip()
                    if after_mention:
                        admin_title = after_mention[:16]
                    break
        
        if not user_id and context.args:
            first_arg = context.args[0]
            if first_arg.startswith('@'):
                try:
                    from AloneX import pbot
                    user = await pbot.get_users(first_arg)
                    if user and hasattr(user, 'id'):
                        user_id = user.id
                except:
                    try:
                        from AloneX.db.users import get_user_id_by_username
                        user_id = await get_user_id_by_username(first_arg[1:])
                    except:
                        pass
                
                if len(context.args) > 1:
                    admin_title = ' '.join(context.args[1:]).strip()[:16]
            
            elif first_arg.isdigit():
                user_id = int(first_arg)
                if len(context.args) > 1:
                    admin_title = ' '.join(context.args[1:]).strip()[:16]
    
    if not user_id:
        return await message.reply_text(
            text="🙋 *Reply to a user or give their telegram ID/username!*",
            parse_mode=constants.ParseMode.MARKDOWN
        )
    
    is_already_admin = False
    try:
        member = await get_member_cached(bot, chat_id, user_id, force_refresh=True)
        if member.status == constants.ChatMemberStatus.OWNER:
            return await message.reply_text(
                text="❌ *Cannot modify the group owner!*",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        if member.status == constants.ChatMemberStatus.ADMINISTRATOR:
            is_already_admin = True
            if command == 'promote':
                return await message.reply_text(
                    text="❌ *User is already an admin! Use /fullpromote or /lowpromote to change permissions.*",
                    parse_mode=constants.ParseMode.MARKDOWN
                )
    except Exception:
        pass
    
    bot_perms = await get_bot_permissions(bot, chat_id)
    
    if not bot_perms:
        return await message.reply_text(
            text="❌ Bot is not an admin or cannot check permissions!",
            parse_mode=constants.ParseMode.HTML
        )
    
    try:
        member = await get_member_cached(bot, chat_id, user_id, force_refresh=True)
        user_name = member.user.first_name
        user_link = f'<a href="tg://user?id={member.user.id}">{html.escape(user_name)}</a>'
        
        promote_perms = {}
        granted_perms = []
        denied_perms = []
        
        if command == 'lowpromote':
            desired = {
                'can_delete_messages': True,
                'can_pin_messages': True,
                'can_manage_video_chats': True
            }
        elif command == 'promote':
            desired = {
                'can_invite_users': True,
                'can_pin_messages': True,
                'can_delete_messages': True,
                'can_manage_video_chats': True,
                'can_post_stories': True,
                'can_edit_stories': True,
                'can_delete_stories': True
            }
        else:
            desired = {
                'can_change_info': True,
                'can_delete_messages': True,
                'can_invite_users': True,
                'can_manage_chat': True,
                'can_restrict_members': True,
                'can_manage_video_chats': True,
                'can_pin_messages': True,
                'can_promote_members': True,
                'can_post_stories': True,
                'can_edit_stories': True,
                'can_delete_stories': True
            }
        
        for perm, value in desired.items():
            if bot_perms.get(perm, False):
                promote_perms[perm] = value
                granted_perms.append(perm.replace('can_', '').replace('_', ' '))
            else:
                denied_perms.append(perm.replace('can_', '').replace('_', ' '))
        
        if command == 'fullpromote':
            promote_perms['is_anonymous'] = False
        
        await bot.promote_chat_member(
            chat_id,
            member.user.id,
            **promote_perms
        )
        
        invalidate_member_cache(chat_id, user_id)
        await reload_admins_cache(bot, chat_id)
        
        title_info = ""
        if admin_title:
            try:
                await bot.set_chat_administrator_custom_title(
                    chat_id,
                    member.user.id,
                    admin_title
                )
                title_info = f" with title: <b>{html.escape(admin_title)}</b>"
            except Exception as title_error:
                title_err_msg = str(title_error)
                if "User_not_mutual_contact" in title_err_msg or "CHAT_ADMIN_REQUIRED" in title_err_msg:
                    title_info = "\n\n<i>⚠️ Title not set: User needs to send a message first.</i>"
                else:
                    title_info = f"\n\n<i>⚠️ Title error: {html.escape(title_err_msg[:60])}</i>"
        
        action_word = "upgraded" if is_already_admin else f"{command}d"
        success_text = f"<b>✅ Successfully {action_word} {user_link}{title_info}</b>"
        
        if granted_perms:
            success_text += f"\n\n<b>Granted permissions:</b>\n• " + "\n• ".join(granted_perms)
        
        if denied_perms:
            success_text += f"\n\n<b>⚠️ Bot lacks these permissions:</b>\n• " + "\n• ".join(denied_perms)
            success_text += "\n\n<i>Give bot more admin rights to grant full permissions.</i>"
        
        await message.reply_text(text=success_text, parse_mode=constants.ParseMode.HTML)
        
        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        log_text = f"👮 <b>{action_word.capitalize()}</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>User:</b> {user_link} (<code>{user_id}</code>)\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}"
        if admin_title:
             log_text += f"\n<b>Title:</b> {html.escape(admin_title)}"
        asyncio.create_task(log_action(context.bot, chat_id, "admin", log_text))

    except Exception as e:
        error_msg = str(e)
        if "User_not_mutual_contact" in error_msg:
            error_msg = "Cannot promote: User needs to start the bot or send a message."
        elif "CHAT_ADMIN_REQUIRED" in error_msg or "Chat_admin_required" in error_msg:
            error_msg = "Bot needs admin rights with 'Add Admins' permission."
        elif "USER_CREATOR" in error_msg:
            error_msg = "Cannot modify the group creator."
        elif "RIGHT_FORBIDDEN" in error_msg or "Not enough rights" in error_msg:
            error_msg = "Bot doesn't have sufficient admin rights."
        
        return await message.reply_text(
            text=f"❌ <b>Error:</b> {html.escape(error_msg)}",
            parse_mode=constants.ParseMode.HTML
        )        

@Command(['title', 'settitle', 'setadmintitle'])
@admin_check("can_promote_members", protect_target=False)
async def setAdminTitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    bot = context.bot
    chat_id = await get_effective_chat_id(update)
    
    user_id = None
    admin_title = None
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        if context.args:
            admin_title = ' '.join(context.args).strip()[:16]
    else:
        if message.entities:
            for entity in message.entities:
                if entity.type == constants.MessageEntityType.TEXT_MENTION and entity.user:
                    user_id = entity.user.id
                    full_text = message.text
                    mention_end = entity.offset + entity.length
                    after_mention = full_text[mention_end:].strip()
                    if after_mention:
                        admin_title = after_mention[:16]
                    break
        
        if not user_id and context.args:
            first_arg = context.args[0]
            if first_arg.startswith('@'):
                try:
                    from AloneX import pbot
                    user = await pbot.get_users(first_arg)
                    if user and hasattr(user, 'id'):
                        user_id = user.id
                except:
                    from AloneX.db.users import get_user_id_by_username
                    user_id = await get_user_id_by_username(first_arg[1:])
                
                if len(context.args) > 1:
                    admin_title = ' '.join(context.args[1:]).strip()[:16]
            
            elif first_arg.isdigit():
                user_id = int(first_arg)
                if len(context.args) > 1:
                    admin_title = ' '.join(context.args[1:]).strip()[:16]
    
    if not user_id:
        return await message.reply_text(text="🙋 *Reply to a user or give their telegram ID!*", parse_mode=constants.ParseMode.MARKDOWN)
    
    if not admin_title:
        return await message.reply_text(text="✋ *Provide a title to set!*\n\nUsage: `/settitle @username Custom Title`", parse_mode=constants.ParseMode.MARKDOWN)
    
    try:
        invalidate_member_cache(chat_id, user_id)
        member = await bot.get_chat_member(chat_id, user_id)
        
        if member.status not in [constants.ChatMemberStatus.ADMINISTRATOR, constants.ChatMemberStatus.OWNER]:
            return await message.reply_text(text="❌ *User must be an admin first!*", parse_mode=constants.ParseMode.MARKDOWN)
        
        user_link = f'<a href="tg://user?id={member.user.id}">{html.escape(member.user.first_name)}</a>'
        await bot.set_chat_administrator_custom_title(chat_id, member.user.id, admin_title)
        invalidate_member_cache(chat_id, user_id)
        
        await message.reply_text(text=f"✨ <b>Successfully set admin title for {user_link}:</b> {html.escape(admin_title)}", parse_mode=constants.ParseMode.HTML)

        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        log_text = f"🏷️ <b>Admin Title Set</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>User:</b> {user_link} (<code>{user_id}</code>)\n" \
                   f"<b>New Title:</b> {html.escape(admin_title)}\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}"
        asyncio.create_task(log_action(context.bot, chat_id, "admin", log_text))
    except Exception as e:
        error_msg = str(e)
        if "User_not_mutual_contact" in error_msg or "Bad Request: user not found" in error_msg:
            error_msg = "User needs to send a message in the group first or start the bot."
        elif "CHAT_ADMIN_REQUIRED" in error_msg or "Chat_admin_required" in error_msg:
            error_msg = "Bot needs 'Add Admins' permission."
        elif "USER_CREATOR" in error_msg:
            error_msg = "Cannot set title for group creator from API."
        return await message.reply_text(text=f"❌ Error: {html.escape(error_msg)}", parse_mode=constants.ParseMode.HTML)

@Command('zombies')
@disableable("zombies")
@admin_check('can_restrict_members')
async def zombiesFire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    chat = m.chat
    
    users = []
    msg = await m.reply_text(font("Checking for Zombies ..."))
    async for member in pbot.get_chat_members(chat_id):
        if member.user.is_deleted:
            users.append(member.user.id)
        else:
            continue
    
    if len(m.text.split()) < 2:
        return await msg.edit_text(
            f"<b>Currently {len(users)} Zombies in this chat, do you want kill them? usage:</b><code>/zombies clean</code>",
            parse_mode=constants.ParseMode.HTML
        )
    elif not users:
        return await msg.edit_text(font("😉 <b>No Zombies in the chat.</b>"), parse_mode=constants.ParseMode.HTML)
    else:
        pattern = m.text.split()[1].lower()
        if pattern != "clean":
            return await msg.edit_text("<b>Its 'clean' buddy isn't it?</b>", parse_mode=constants.ParseMode.HTML)
        else:
            done = 0
            fail = 0
            for user_id in users:
                try:
                    service = await m.chat.ban_member(user_id)
                    invalidate_member_cache(chat_id, user_id)
                    done += 1
                except Exception as e:
                    fail += 1
            title = update.effective_chat.title
            if chat_id != update.effective_chat.id:
                try:
                    target_chat = await context.bot.get_chat(chat_id)
                    title = target_chat.title
                except:
                    title = str(chat_id)
            text = f"⚔️ <b>Killed {done} Zombies in {html.escape(title)}</b> "
            if fail != 0:
                text += f"<b>and {fail} Zombies are escaped!</b>"
            return await msg.edit_text(text, parse_mode=constants.ParseMode.HTML)

@pbot.on_message(filters.command("adminlist", prefix_cmds), group=109)
async def adminlist_command(client: Client, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.chat.type == enums.ChatType.PRIVATE:
        from AloneX.db.connection_db import get_connected_chat
        chat_id = await get_connected_chat(user_id) or chat_id
        if chat_id == message.chat.id:
            return await message.reply_text(font("❌ This command only works in groups or via connections!"))

    chat = await client.get_chat(chat_id)
    msg = await message.reply_text(font("⚡ Fetching Staff List..."))
    current_admin_ids = []
    owner = None
    regular = []
    async for m in client.get_chat_members(chat.id, filter=ChatMembersFilter.ADMINISTRATORS):
        current_admin_ids.append(m.user.id)
        if m.status == ChatMemberStatus.OWNER:
            owner = m
        else:
            regular.append(m)
    old_admin_ids = await get_last_admins(chat.id)
    if set(current_admin_ids) == set(old_admin_ids):
        cached = True
    else:
        cached = False
        await save_admins(chat.id, current_admin_ids)
    text = f"🧑‍✈️ <b>Staff's in {html.escape(chat.title)}</b>:\n\n"
    if cached:
        text += "⚠️ <i>Note: These are cached values</i>\n\n"
    else:
        text += "✅ <i>Note: These are up-to-date values</i>\n\n"
    if owner:
        text += "👑 <b>Owner</b>:\n"
        name = html.escape(owner.user.first_name)
        if owner.custom_title:
            text += f"➣ <a href='tg://user?id={owner.user.id}'>{name}</a> - <i>{html.escape(owner.custom_title)}</i>\n\n"
        else:
            text += f"➣ <a href='tg://user?id={owner.user.id}'>{name}</a>\n\n"
    if regular:
        text += "👮 <b>Admins</b>:\n"
        for a in regular:
            name = html.escape(a.user.first_name)
            if a.custom_title:
                text += f"➣ <a href='tg://user?id={a.user.id}'>{name}</a> - <i>{html.escape(a.custom_title)}</i>\n"
            else:
                text += f"➣ <a href='tg://user?id={a.user.id}'>{name}</a>\n"
        text += "\n"
    mods = await get_all_mods(chat.id)
    mod_group = {}
    for m in mods:
        u = m['user_id']
        r = m['role']
        if r not in mod_group:
            mod_group[r] = []
        mod_group[r].append(u)
    names = {
        "mod": "🛡️ Moderators",
        "warner": "⚠️ Warners",
        "muter": "🔇 Muters",
        "cleaner": "🧹 Cleaners"
    }
    for r in ["mod", "muter", "warner", "cleaner"]:
        if r in mod_group:
            text += f"<b>{names[r]}</b>:\n"
            for uid in mod_group[r]:
                try:
                    cm = await client.get_chat_member(chat.id, uid)
                    if cm.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                        await remove_all_user_mods(chat.id, uid)
                        continue
                    name = html.escape(cm.user.first_name)
                    if cm.custom_title:
                        text += f"➣ <a href='tg://user?id={cm.user.id}'>{name}</a> - <i>{html.escape(cm.custom_title)}</i>\n"
                    else:
                        text += f"➣ <a href='tg://user?id={cm.user.id}'>{name}</a>\n"
                except:
                    await remove_all_user_mods(chat.id, uid)
                    continue
            text += "\n"
    if len(text) > 4096:
        clean = text.replace("<b>", "").replace("</b>", "")
        clean = clean.replace("<i>", "").replace("</i>", "")
        clean = clean.replace("<code>", "").replace("</code>", "")
        clean = clean.replace("<a href='tg://user?id=", "").replace("'>", " ").replace("</a>", "")
        buf = io.BytesIO(clean.encode())
        buf.name = f"adminlist_{chat.id}.txt"
        await msg.delete()
        return await message.reply_document(buf, caption="📋 Full Adminlist")
    await msg.edit_text(text, parse_mode=ParseMode.HTML)
