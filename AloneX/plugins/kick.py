import html
import logging
from telegram import Update, helpers
from telegram.ext import ContextTypes
from telegram.error import BadRequest, Forbidden, TelegramError
from AloneX.helpers.decorator import Command, only_groups, admin_check, mod_permission
from AloneX.helpers.utils import extract_user
from AloneX import DEV_LIST, font

logger = logging.getLogger(__name__)

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

async def get_chat_name(bot, chat_id):
    try:
        target_chat = await bot.get_chat(chat_id)
        if hasattr(target_chat, 'title') and target_chat.title:
            return html.escape(target_chat.title)
        elif hasattr(target_chat, 'username') and target_chat.username:
            return f"@{target_chat.username}"
        return str(chat_id)
    except:
        return str(chat_id)

@Command(["kick", "dkick"])
@mod_permission("kick", protect_target=False)
@only_groups
async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    args = context.args
    command = m.text.split()[0][1:].lower() if m.text else "kick"
    if m.reply_to_message and m.reply_to_message.sender_chat:
        sender_chat = m.reply_to_message.sender_chat
        reason = " ".join(args) if args else "No reason provided."
        if len(reason) > 200:
            reason = reason[:197] + "..."
        bot_member = await m.chat.get_member(context.bot.id)
        if not bot_member.can_restrict_members:
            return await m.reply_text("❌ I don't have permission to kick channels in this group.")
        channel_name = await get_chat_name(context.bot, sender_chat.id)
        try:
            await context.bot.ban_chat_sender_chat(chat_id=m.chat.id, sender_chat_id=sender_chat.id)
            await context.bot.unban_chat_sender_chat(chat_id=m.chat.id, sender_chat_id=sender_chat.id)
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
        bot_member = await m.chat.get_member(context.bot.id)
        if not bot_member.can_restrict_members:
            return await m.reply_text("❌ I don't have permission to kick users in this group.")
        try:
            member = await m.chat.get_member(user_id)
            target_user = member.user
            if member.status in ['creator', 'administrator']:
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
            await m.chat.ban_member(user_id)
            await m.chat.unban_member(user_id)
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
    except Forbidden:
        await m.reply_text("❌ I don't have permission to kick users.")
    except BadRequest as e:
        error_msg = getattr(e, 'message', str(e))
        await m.reply_text(f"❌ Cannot kick you: {html.escape(error_msg)}")
    except Exception as e:
        logger.error(f"Error in kickme command: {e}")
        await m.reply_text(font("❌ Failed to kick you due to an unexpected error."))
