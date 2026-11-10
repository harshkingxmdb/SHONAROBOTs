import html
import asyncio
from time import time
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, constants, ChatPermissions
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest, Forbidden, TelegramError
from AloneX.helpers.decorator import Command, Callbacks, only_groups, admin_check, mod_permission, get_effective_chat_id
from AloneX.helpers.utils import extract_user, async_cache
from AloneX import prefix_cmds as PREFIX_CMDS
from datetime import datetime, timedelta
import logging
from telegram import helpers
from AloneX import DEV_LIST, font
from AloneX.helpers.log_helper import log_action

logger = logging.getLogger(__name__)

PREFIX_SET = set(PREFIX_CMDS)
BANNED_STATUSES = {ChatMemberStatus.BANNED}
ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}

TIME_MULTIPLIERS = {"m": 60, "h": 3600, "d": 86400, "w": 604800}

BAN_TYPES = {
    "ban": (False, False, False),
    "dban": (True, False, False),
    "sban": (False, False, True),
    "pban": (False, True, False),
    "tban": (False, False, False),
    "dtban": (True, False, False),
    "stban": (False, False, True),
}

BAN_TEXT = {
    "ban": "banned",
    "dban": "banned",
    "sban": "banned",
    "pban": "banned",
    "tban": "temporarily banned",
    "dtban": "temporarily banned",
    "stban": "temporarily banned",
}

def extract_command(text):
    cmd = text.lower().split()[0]
    for p in PREFIX_SET:
        if cmd[0] == p:
            return cmd[1:]
    return cmd

@async_cache(max_size=50000, max_idle_time=3600)
async def get_user_mention(bot, chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        fn = html.escape(member.user.first_name or "User")
        return f"<a href='tg://user?id={user_id}'>{fn}</a>"
    except:
        return f"<a href='tg://user?id={user_id}'>User</a>"

@async_cache(max_size=10000, max_idle_time=3600)
async def get_chat_name(bot, chat_id):
    try:
        tc = await bot.get_chat(chat_id)
        name = getattr(tc, "title", None) or (f"@{tc.username}" if getattr(tc, "username", None) else str(chat_id))
        return html.escape(name)
    except:
        return str(chat_id)

@async_cache(max_size=50000, max_idle_time=300)
async def check_banned(chat_id, user_id, chat_obj):
    try:
        member = await chat_obj.get_member(user_id)
        return member.status in BANNED_STATUSES
    except:
        return False

@async_cache(max_size=50000, max_idle_time=300)
async def check_admin(chat_id, user_id, chat_obj):
    try:
        member = await chat_obj.get_member(user_id)
        return member.status in ADMIN_STATUSES
    except:
        return False

def parse_time(ts):
    if not ts:
        return None
    ts = ts.lower().strip()
    try:
        if ts[-1] in TIME_MULTIPLIERS:
            amt = int(ts[:-1])
            if amt <= 0:
                return None
            secs = amt * TIME_MULTIPLIERS[ts[-1]]
            return datetime.now() + timedelta(seconds=secs)
    except:
        pass
    return None

async def auto_delete(msg, delay):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except:
        pass

@Command(["ban", "dban", "sban", "pban", "tban", "dtban", "stban"])
@mod_permission("ban")
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    args = context.args
    cmd = extract_command(m.text)
    
    # Handle channel bans
    if m.reply_to_message and m.reply_to_message.sender_chat:
        sc = m.reply_to_message.sender_chat
        delete_msg, revoke, is_silent = BAN_TYPES[cmd]
        reason = " ".join(args) if args else "No reason provided"
        
        if cmd in ["tban", "dtban", "stban"]:
            return await m.reply_text(font("Channels cannot be temporarily banned. Use /ban instead to permanently ban this channel."))
        
        rn = await get_chat_name(context.bot, sc.id)
        try:
            await context.bot.ban_chat_sender_chat(chat_id=chat_id, sender_chat_id=sc.id)
            if delete_msg and m.reply_to_message:
                asyncio.create_task(m.reply_to_message.delete())
            
            reason_safe = html.escape(reason)
            resp = f"The channel <b>{rn}</b> has been banned from this chat.\n\n<b>Reason:</b> {reason_safe}"
            
            if is_silent:
                sent = await m.reply_html(resp)
                asyncio.create_task(auto_delete(sent, 5))
                asyncio.create_task(auto_delete(m, 5))
            else:
                await m.reply_html(resp, reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(font("✅ Unban (Admin Only)"), callback_data=f"unban_{sc.id}")
                ]]))
            return
        except BadRequest as e:
            return await m.reply_html(f"Failed to ban channel: <code>{html.escape(str(e))}</code>")
        except Exception as e:
            return await m.reply_html(f"An error occurred: <code>{html.escape(str(e))}</code>")
    
    # Handle user bans
    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text(font("Please specify which user you would like to ban. You can reply to their message, mention them, or provide their user ID."))
    
    delete_msg, revoke, is_silent = BAN_TYPES[cmd]
    until_date = None
    reason = "No reason provided"
    is_temp = cmd in ["tban", "dtban", "stban"]
    
    # Parse time and reason for temporary bans
    if is_temp:
        if m.reply_to_message:
            if args:
                until_date = parse_time(args[0])
                reason = " ".join(args[1:]) if len(args) > 1 else reason
        else:
            if len(args) > 1:
                until_date = parse_time(args[1])
                reason = " ".join(args[2:]) if len(args) > 2 else reason
        
        if not until_date:
            return await m.reply_text(
                f"Please specify the ban duration.\n\n"
                f"<b>Examples:</b>\n"
                f"<code>/{cmd} 30m</code> - ban for 30 minutes\n"
                f"<code>/{cmd} 2h spam</code> - ban for 2 hours with reason\n\n"
                f"<b>Valid formats:</b> m (minutes), h (hours), d (days), w (weeks)",
                parse_mode=constants.ParseMode.HTML
            )
    else:
        if m.reply_to_message and args:
            reason = " ".join(args)
        elif not m.reply_to_message and len(args) > 1:
            reason = " ".join(args[1:])
    
    try:
        # Check if user is already banned
        member_target = await context.bot.get_chat_member(chat_id, user_id)
        if member_target.status == ChatMemberStatus.BANNED:
            mention = await get_user_mention(context.bot, chat_id, user_id)
            return await m.reply_html(f"{mention} is already banned from this chat.")
        
        # Check if user is admin
        if member_target.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await m.reply_text(font("Cannot ban administrators."))
        
        mention = await get_user_mention(context.bot, chat_id, user_id)
        
        # Ban the user
        if until_date:
            await context.bot.ban_chat_member(chat_id, user_id, until_date=until_date, revoke_messages=revoke)
        else:
            await context.bot.ban_chat_member(chat_id, user_id, revoke_messages=revoke)
        
        check_banned.clear_cache()
        
        # Delete replied message if needed
        if delete_msg and m.reply_to_message:
            asyncio.create_task(m.reply_to_message.delete())
        
        # Build response with proper HTML escaping
        reason_safe = html.escape(reason)
        resp = f"🚫{mention} has been {BAN_TEXT[cmd]}.\n\n<b>📝Reason:</b> {reason_safe}"
        
        if until_date:
            resp += f"\n<b>Ban expires:</b> {until_date.strftime('%Y-%m-%d at %H:%M:%S UTC')}"
        
        # Log action
        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        log_text = f"🚫 <b>{BAN_TEXT[cmd].capitalize()}</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>User:</b> {mention} (<code>{user_id}</code>)\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}\n" \
                   f"<b>Reason:</b> {reason_safe}"
        if until_date:
            log_text += f"\n<b>Expires:</b> {until_date.strftime('%Y-%m-%d %H:%M:%S')}"
        asyncio.create_task(log_action(context.bot, chat_id, "bans", log_text))

        # Debug log
        logger.debug(f"Ban response HTML: {resp}")
        logger.debug(f"Response length: {len(resp)} chars, {len(resp.encode('utf-8'))} bytes")
        
        if is_silent:
            sent = await m.reply_text(resp, parse_mode=constants.ParseMode.HTML)
            asyncio.create_task(auto_delete(sent, 5))
            asyncio.create_task(auto_delete(m, 5))
        else:
            await m.reply_text(resp, parse_mode=constants.ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(font("✅ Unban (Admin Only)"), callback_data=f"unban_{user_id}")
            ]]))
    except Forbidden:
        await m.reply_text(font("I do not have permission to ban users in this chat. Please ensure I have the necessary admin rights."))
    except BadRequest as e:
        await m.reply_text(f"Unable to ban this user: {html.escape(str(e))}")
    except Exception as e:
        logger.error(f"Error in ban command: {e}")
        await m.reply_text(f"An error occurred while trying to ban this user: {html.escape(str(e))}")

@Command("unban")
@mod_permission("ban", protect_target=False)
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    args = context.args
    
    # Handle channel unbans
    if m.reply_to_message and m.reply_to_message.sender_chat:
        sc = m.reply_to_message.sender_chat
        rn = await get_chat_name(context.bot, sc.id)
        try:
            await context.bot.unban_chat_sender_chat(chat_id=chat_id, sender_chat_id=sc.id)
            return await m.reply_html(f"The channel <b>{rn}</b> has been unbanned and can now send messages in this chat.")
        except BadRequest as e:
            return await m.reply_html(f"Failed to unban channel: <code>{html.escape(str(e))}</code>")
        except Exception as e:
            return await m.reply_html(f"An error occurred: <code>{html.escape(str(e))}</code>")
    
    # Handle user unbans
    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text(font("Please specify which user you would like to unban. You can reply to their message, mention them, or provide their user ID."))
    
    try:
        member_target = await context.bot.get_chat_member(chat_id, user_id)
        if member_target.status != ChatMemberStatus.BANNED:
            mention = await get_user_mention(context.bot, chat_id, user_id)
            return await m.reply_html(f"{mention} is already unbanned.")
        
        await context.bot.unban_chat_member(chat_id, user_id)
        mention = await get_user_mention(context.bot, chat_id, user_id)
        await m.reply_html(f"{mention} has been unbanned and can now rejoin this chat.")

        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        log_text = f"🔓 <b>Unbanned</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>User:</b> {mention} (<code>{user_id}</code>)\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}"
        asyncio.create_task(log_action(context.bot, chat_id, "bans", log_text))
    except Forbidden:
        await m.reply_text(font("I do not have permission to unban users in this chat. Please ensure I have the necessary admin rights."))
    except BadRequest as e:
        await m.reply_text(f"Unable to unban this user: {html.escape(str(e))}")
    except Exception as e:
        logger.error(f"Error in unban command: {e}")
        await m.reply_text(f"An error occurred while trying to unban this user: {html.escape(str(e))}")

@Callbacks("^unban_")
@mod_permission("ban", protect_target=False)
async def unban_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = await get_effective_chat_id(update)
    user_id = int(query.data.split("_")[1])
    
    try:
        if user_id < 0:
            # Channel unban
            rn = await get_chat_name(context.bot, user_id)
            await context.bot.unban_chat_sender_chat(chat_id=chat_id, sender_chat_id=user_id)
            await query.message.edit_text(f"The channel {rn} has been unbanned.", parse_mode=constants.ParseMode.HTML)
        else:
            # User unban
            # Need to get chat object for check_banned
            chat_obj = await context.bot.get_chat(chat_id)
            is_banned = await check_banned(chat_id, user_id, chat_obj)
            
            if not is_banned:
                mention = await get_user_mention(context.bot, chat_id, user_id)
                await query.message.edit_text(f"{mention} is already unbanned.", parse_mode=constants.ParseMode.HTML)
                await query.answer(font("User is already unbanned"))
                return
            
            await context.bot.unban_chat_member(chat_id, user_id)
            check_banned.clear_cache()
            mention = await get_user_mention(context.bot, chat_id, user_id)
            await query.message.edit_text(f"{mention} has been unbanned.", parse_mode=constants.ParseMode.HTML)

            log_text = f"🔓 <b>Unbanned (via button)</b>\n" \
                       f"<b>Group:</b> {html.escape(chat_obj.title)}\n" \
                       f"<b>User:</b> {mention} (<code>{user_id}</code>)\n" \
                       f"<b>By:</b> {query.from_user.mention_html()}"
            asyncio.create_task(log_action(context.bot, chat_id, "bans", log_text))
        await query.answer(font("Successfully unbanned"))
    except Exception as e:
        logger.error(f"Error in unban button: {e}")
        await query.answer(f"Error: {html.escape(str(e))}", show_alert=True)

@Command(["mute", "smute", "dmute", "tmute", "stmute", "dtmute"])
@mod_permission("mute")
async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    args = context.args
    cmd = extract_command(m.text)
    
    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text(font("Please specify which user you would like to mute. You can reply to their message, mention them, or provide their user ID."))
    
    delete_msg = cmd.startswith("d")
    is_silent = cmd.startswith("s")
    is_temp = "tmute" in cmd
    until_date = None
    reason = "No reason provided"
    
    # Parse time and reason for temporary mutes
    if is_temp:
        if m.reply_to_message:
            if args:
                until_date = parse_time(args[0])
                reason = " ".join(args[1:]) if len(args) > 1 else reason
        else:
            if len(args) > 1:
                until_date = parse_time(args[1])
                reason = " ".join(args[2:]) if len(args) > 2 else reason
        
        if not until_date:
            return await m.reply_text(
                f"Please specify the mute duration.\n\n"
                f"<b>Examples:</b>\n"
                f"<code>/{cmd} 30m</code> - mute for 30 minutes\n"
                f"<code>/{cmd} 2h spam</code> - mute for 2 hours with reason\n\n"
                f"<b>Valid formats:</b> m (minutes), h (hours), d (days), w (weeks)",
                parse_mode=constants.ParseMode.HTML
            )
    else:
        if m.reply_to_message and args:
            reason = " ".join(args)
        elif not m.reply_to_message and len(args) > 1:
            reason = " ".join(args[1:])
    
    try:
        member_target = await context.bot.get_chat_member(chat_id, user_id)
        # Check if user is admin
        if member_target.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await m.reply_text(font("Cannot mute administrators."))
        
        mention = await get_user_mention(context.bot, chat_id, user_id)
        
        # Set restrictive permissions
        perms = ChatPermissions(
            can_send_messages=False,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        
        # Mute the user
        if until_date:
            await context.bot.restrict_chat_member(chat_id, user_id, permissions=perms, until_date=until_date)
        else:
            await context.bot.restrict_chat_member(chat_id, user_id, permissions=perms)
        
        # Delete replied message if needed
        if delete_msg and m.reply_to_message:
            asyncio.create_task(m.reply_to_message.delete())
        
        # Build response with proper HTML escaping
        mute_type = "temporarily muted" if is_temp else "muted"
        reason_safe = html.escape(reason)
        resp = f"🚷{mention} has been {mute_type}.\n\n<b>📝Reason:</b> {reason_safe}"
        
        if until_date:
            resp += f"\n<b>Mute expires:</b> {until_date.strftime('%Y-%m-%d at %H:%M:%S UTC')}"

        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        log_text = f"🔇 <b>{mute_type.capitalize()}</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>User:</b> {mention} (<code>{user_id}</code>)\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}\n" \
                   f"<b>Reason:</b> {reason_safe}"
        if until_date:
            log_text += f"\n<b>Expires:</b> {until_date.strftime('%Y-%m-%d %H:%M:%S')}"
        asyncio.create_task(log_action(context.bot, chat_id, "mutes", log_text))
        
        # Debug log
        logger.debug(f"Mute response HTML: {resp}")
        logger.debug(f"Response length: {len(resp)} chars, {len(resp.encode('utf-8'))} bytes")
        
        if is_silent:
            sent = await m.reply_text(resp, parse_mode=constants.ParseMode.HTML)
            asyncio.create_task(auto_delete(sent, 5))
            asyncio.create_task(auto_delete(m, 5))
        else:
            await m.reply_text(resp, parse_mode=constants.ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(font("✅ Unmute (Admin Only)"), callback_data=f"unmute_{user_id}")
            ]]))
    except Forbidden:
        await m.reply_text(font("I do not have permission to mute users in this chat. Please ensure I have the necessary admin rights."))
    except BadRequest as e:
        await m.reply_text(f"Unable to mute this user: {html.escape(str(e))}")
    except Exception as e:
        logger.error(f"Error in mute command: {e}")
        await m.reply_text(f"An error occurred while trying to mute this user: {html.escape(str(e))}")

@Command("unmute")
@mod_permission("restrict", protect_target=False)
async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    
    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text(font("Please specify which user you would like to unmute. You can reply to their message, mention them, or provide their user ID."))
    
    try:
        mention = await get_user_mention(context.bot, chat_id, user_id)
        
        # Restore permissions
        perms = ChatPermissions(
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
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False
        )
        
        await context.bot.restrict_chat_member(chat_id, user_id, permissions=perms)
        await m.reply_html(f"{mention} has been unmuted and can now send messages.")

        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        log_text = f"🔊 <b>Unmuted</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>User:</b> {mention} (<code>{user_id}</code>)\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}"
        asyncio.create_task(log_action(context.bot, chat_id, "mutes", log_text))
    except Forbidden:
        await m.reply_text(font("I do not have permission to unmute users in this chat. Please ensure I have the necessary admin rights."))
    except BadRequest as e:
        await m.reply_text(f"Unable to unmute this user: {html.escape(str(e))}")
    except Exception as e:
        logger.error(f"Error in unmute command: {e}")
        await m.reply_text(f"An error occurred while trying to unmute this user: {html.escape(str(e))}")

@Callbacks("^unmute_")
@mod_permission("restrict", protect_target=False)
async def unmute_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = await get_effective_chat_id(update)
    user_id = int(query.data.split("_")[1])
    
    try:
        mention = await get_user_mention(context.bot, chat_id, user_id)
        
        # Restore permissions
        perms = ChatPermissions(
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
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False
        )
        
        await context.bot.restrict_chat_member(chat_id, user_id, permissions=perms)
        await query.message.edit_text(f"{mention} has been unmuted.", parse_mode=constants.ParseMode.HTML)

        chat_obj = await context.bot.get_chat(chat_id)
        log_text = f"🔊 <b>Unmuted (via button)</b>\n" \
                   f"<b>Group:</b> {html.escape(chat_obj.title)}\n" \
                   f"<b>User:</b> {mention} (<code>{user_id}</code>)\n" \
                   f"<b>By:</b> {query.from_user.mention_html()}"
        asyncio.create_task(log_action(context.bot, chat_id, "mutes", log_text))
        await query.answer(font("Successfully unmuted"))
    except Exception as e:
        logger.error(f"Error in unmute button: {e}")
        await query.answer(f"Error: {html.escape(str(e))}", show_alert=True)

async def get_user_id_from_args_or_reply(m, args):
    try:
        if m.reply_to_message:
            return m.reply_to_message.from_user.id
        if not args:
            return None
        text = str(args[0]).strip()
        if not text:
            return None
        if text.startswith(("https://t.me/", "t.me/")):
            return None
        if text.isdigit():
            user_id = int(text)
            if 1 <= user_id <= 2**63 - 1:
                return user_id
            return None
        if text.startswith("@"):
            username = text[1:]
            if username and len(username) >= 5:
                return username
            return None
        return text
    except (ValueError, IndexError, AttributeError):
        return None

@Command(["kick", "dkick"])
@mod_permission("kick", protect_target=False)
async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    args = context.args
    command = m.text.split()[0][1:].lower() if m.text else "kick"
    
    # Handle channel kicks
    if m.reply_to_message and m.reply_to_message.sender_chat:
        sender_chat = m.reply_to_message.sender_chat
        reason = " ".join(args) if args else "No reason provided."
        if len(reason) > 200:
            reason = reason[:197] + "..."
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if not bot_member.can_restrict_members:
            return await m.reply_text("❌ I don't have permission to kick channels in this group.")
        channel_name = await get_chat_name(context.bot, sender_chat.id)
        try:
            await context.bot.ban_chat_sender_chat(chat_id=chat_id, sender_chat_id=sender_chat.id)
            await context.bot.unban_chat_sender_chat(chat_id=chat_id, sender_chat_id=sender_chat.id)
            if command == "dkick":
                try:
                    await m.reply_to_message.delete()
                    await m.delete()
                except Exception:
                    pass
            reason_safe = html.escape(reason)
            success_msg = (
                f"👢 Channel <b>{channel_name}</b> has been kicked from the group!\n"
                f"📄 Reason: {reason_safe}"
            )
            return await m.reply_html(success_msg)
        except BadRequest as e:
            return await m.reply_text(f"❌ Cannot kick channel: {html.escape(str(e))}")
        except Exception as e:
            logger.error(f"Error kicking channel: {e}")
            return await m.reply_text(font("❌ Failed to kick the channel."))
    
    # Handle user kicks
    try:
        user_id = await extract_user(m, self=False)
        if not user_id and args:
            user_id = await get_user_id_from_args_or_reply(m, args)
        if not user_id:
            return await m.reply_text(
                "❌ Usage: Reply to a message or provide username/ID to kick.\n"
                "Example: /kick @username reason or /kick 123456789 reason"
            )
        reason = "No reason provided."
        if len(args) > 1:
            if m.reply_to_message:
                reason = " ".join(args)
            else:
                reason = " ".join(args[1:])
        if len(reason) > 200:
            reason = reason[:197] + "..."
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if not bot_member.can_restrict_members:
            return await m.reply_text("❌ I don't have permission to kick users in this group.")
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            target_user = member.user
            if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                return await m.reply_text(font("❌ Cannot kick administrators or group creator."))
            if target_user.id == context.bot.id:
                return await m.reply_text(font("❌ I cannot kick myself!"))
        except BadRequest:
            return await m.reply_text(font("❌ User not found in this group."))
        except Exception as e:
            logger.error(f"Error getting member info: {e}")
            return await m.reply_text(font("❌ Failed to get user information."))
        if command == "dkick" and m.reply_to_message:
            try:
                await m.reply_to_message.delete()
                await m.delete()
            except Exception:
                pass
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
        except Forbidden:
            return await m.reply_text("❌ I don't have permission to kick users here.")
        except BadRequest as e:
            error_msg = getattr(e, 'message', str(e))
            return await m.reply_text(f"❌ Cannot kick user: {html.escape(error_msg)}")
        first_name = html.escape(target_user.first_name or "User")
        mention = helpers.mention_html(target_user.id, first_name)
        reason_safe = html.escape(reason)
        success_msg = (
            f"👢 {mention} has been kicked from the group!\n"
            f"📄 Reason: {reason_safe}"
        )

        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        log_text = f"👢 <b>Kicked</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>User:</b> {mention} (<code>{user_id}</code>)\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}\n" \
                   f"<b>Reason:</b> {reason_safe}"
        asyncio.create_task(log_action(context.bot, chat_id, "bans", log_text))

        return await m.reply_html(success_msg)
    except TelegramError as e:
        logger.error(f"Telegram error in kick command: {e}")
        return await m.reply_text(f"❌ Telegram error: {html.escape(str(e))}")
    except Exception as e:
        logger.error(f"Unexpected error in kick command: {e}")
        return await m.reply_text(font("❌ An unexpected error occurred while kicking the user."))

@Command("skick")
@admin_check("can_restrict_members")
@only_groups
async def silent_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    chat = m.chat
    
    # Handle channel kicks
    if m.reply_to_message and m.reply_to_message.sender_chat:
        sender_chat = m.reply_to_message.sender_chat
        try:
            bot_member = await chat.get_member(context.bot.id)
            if not bot_member.can_restrict_members:
                return
            await context.bot.ban_chat_sender_chat(chat_id=chat.id, sender_chat_id=sender_chat.id)
            await context.bot.unban_chat_sender_chat(chat_id=chat.id, sender_chat_id=sender_chat.id)
            try:
                await m.reply_to_message.delete()
                await m.delete()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error in silent kick channel: {e}")
        return
    
    # Handle user kicks
    try:
        user_id = await extract_user(m, self=False)
        if not user_id:
            return
        bot_member = await chat.get_member(context.bot.id)
        if not bot_member.can_restrict_members:
            return await m.reply_text("❌ I don't have permission to kick users.")
        try:
            member = await chat.get_member(user_id)
            if member.status in ['creator', 'administrator']:
                return
        except BadRequest:
            return
        await chat.ban_member(user_id)
        await chat.unban_member(user_id)
        try:
            await m.delete()
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Error in silent kick: {e}")

@Command("kickme")
@only_groups
async def kick_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    user = m.from_user
    try:
        if user.id in DEV_LIST:
            return await m.reply_text("😎 You're too powerful to kick yourself!")
        bot_member = await m.chat.get_member(context.bot.id)
        if not bot_member.can_restrict_members:
            return await m.reply_text("❌ I don't have permission to kick users.")
        user_member = await m.chat.get_member(user.id)
        if user_member.status in ['creator', 'administrator']:
            return await m.reply_text(font("❌ Administrators cannot kick themselves using this command."))
        await m.chat.ban_member(user.id)
        await m.chat.unban_member(user.id)
        await m.reply_text(font("👋 You kicked yourself from the group. Goodbye!"))

        log_text = f"👢 <b>User Kicked Self</b>\n" \
                   f"<b>Group:</b> {html.escape(m.chat.title)}\n" \
                   f"<b>User:</b> {user.mention_html()} (<code>{user.id}</code>)"
        asyncio.create_task(log_action(context.bot, m.chat.id, "bans", log_text))
    except Forbidden:
        await m.reply_text("❌ I don't have permission to kick users.")
    except BadRequest as e:
        error_msg = getattr(e, 'message', str(e))
        await m.reply_text(f"❌ Cannot kick you: {html.escape(error_msg)}")
    except Exception as e:
        logger.error(f"Error in kickme command: {e}")
        await m.reply_text(font("❌ Failed to kick you due to an unexpected error."))

__module__ = "𝐁ᴀɴs🚫"

__help__ = """
*Ban Commands*
❂ `/ban <reply|user> [reason]` — Permanently ban a user from the group.  
❂ `/dban <reply|user> [reason]` — Ban + delete the replied message.  
❂ `/sban <reply|user> [reason]` — Silent ban (auto-deletes command & message).  
❂ `/pban <reply|user> [reason]` — Ban + purge all recent messages from user.  
❂ `/tban <reply|user> <time> [reason]` — Temporarily ban (e.g., 30m, 2h, 1d, 1w).  
❂ `/dtban <reply|user> <time> [reason]` — Temp ban + delete message.  
❂ `/stban <reply|user> <time> [reason]` — Silent temp ban (auto-deletes).  
❂ `/unban <reply|user>` — Lift a ban and allow user to rejoin.
❂ `/kick <reply|user> [reason]` — Remove a member (they can rejoin).  
❂ `/dkick <reply|user> [reason]` — Kick + delete the replied message.  
❂ `/skick <reply|user>` — Silent kick (no confirmation message).  
❂ `/kickme` — Kick yourself from the group.
❂ `/mute <reply|user> [reason]` — Permanently mute a user.  
❂ `/dmute <reply|user> [reason]` — Mute + delete the replied message.  
❂ `/smute <reply|user> [reason]` — Silent mute (auto-deletes messages).  
❂ `/tmute <reply|user> <time> [reason]` — Temporarily mute (e.g., 30m, 2h, 1d).  
❂ `/dtmute <reply|user> <time> [reason]` — Temp mute + delete message.  
❂ `/stmute <reply|user> <time> [reason]` — Silent temp mute.  
❂ `/unmute <reply|user>` — Unmute a user.


*Usage Examples:*
• `/ban @username spam` — ban by username with reason  
• Reply to a message + `/dban` — ban and delete that message  
• `/tban @user 1h flooding` — temp ban for 1 hour  
• `/kick 123456789 off-topic` — kick by user ID  
• `/skick` (reply) — silent kick with no notification  
• `/mute @user off-topic` — mute user permanently  
• `/tmute 30m` (reply) — temp mute for 30 minutes  
• `/kickme` — remove yourself from group  
"""
