from AloneX import font

__module__ = "𝐂ʟᴇᴀɴ-𝐂ᴍᴅs🧹"

__help__ = """
❂ *CleanCommand Module* — Auto-delete commands in groups.

*Commands:*
• /cleancommand <type> — Enable auto-delete
• /cleancommandoff — Disable cleaning
• /cleancommandstatus — Check current settings

*Types:*
• all — Delete ALL commands
• admin — Delete admin commands only
• user — Delete user commands only

*Notes:*
- Bot must be admin with delete permission
- Only one type can be active at a time
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, filters
from AloneX.helpers.decorator import Command, only_groups, admin_check, Messages
from AloneX.db.cleancommand_db import set_clean_type, get_clean_type, disable_cleaning

LOGGER = logging.getLogger(__name__)

VALID_TYPES = ["all", "admin", "user"]

admin_cache = {}
bot_perms_cache = {}
settings_cache = {}


def cache_admin(chat_id: int, user_id: int, is_admin: bool):
    admin_cache[f"{chat_id}:{user_id}"] = is_admin


def get_admin_cache(chat_id: int, user_id: int):
    return admin_cache.get(f"{chat_id}:{user_id}")


def cache_bot_perms(chat_id: int, can_delete: bool):
    bot_perms_cache[chat_id] = can_delete


def get_bot_perms_cache(chat_id: int):
    return bot_perms_cache.get(chat_id)


def cache_settings(chat_id: int, clean_type: str):
    settings_cache[chat_id] = clean_type


def get_settings_cache(chat_id: int):
    return settings_cache.get(chat_id)


def clear_chat_cache(chat_id: int):
    settings_cache.pop(chat_id, None)
    bot_perms_cache.pop(chat_id, None)
    keys = [k for k in admin_cache if k.startswith(f"{chat_id}:")]
    for k in keys:
        admin_cache.pop(k, None)


async def safe_delete(message):
    try:
        await message.delete()
    except Exception as e:
        if "not found" not in str(e).lower() and "can't be deleted" not in str(e).lower():
            LOGGER.warning(f"Delete failed: {e}")


@Command("cleancommandstatus")
@only_groups
@admin_check("can_change_info", protect_target=False)
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    clean_type = await get_clean_type(chat_id)
    
    if clean_type:
        text = f"✅ **Cleaning enabled**\n**Type:** `{clean_type}`"
    else:
        text = "❌ **Cleaning disabled**"
    
    await update.effective_message.reply_text(text, parse_mode="Markdown")


@Command("cleancommand")
@only_groups
@admin_check("can_change_info", protect_target=False)
async def clean_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if not context.args:
        current = await get_clean_type(chat_id)
        status = f"**Current:** `{current if current else 'disabled'}`\n\n"
        usage = (
            "**Usage:** `/cleancommand <type>`\n\n"
            "**Types:**\n"
            "• `all` — Delete all commands\n"
            "• `admin` — Delete admin commands\n"
            "• `user` — Delete user commands\n\n"
            "**Disable:** `/cleancommandoff`"
        )
        await update.effective_message.reply_text(status + usage, parse_mode="Markdown")
        return
    
    clean_type = context.args[0].lower()
    
    if clean_type not in VALID_TYPES:
        await update.effective_message.reply_text(
            f"❌ Invalid type: `{clean_type}`\n\n"
            f"Valid types: {', '.join(VALID_TYPES)}",
            parse_mode="Markdown"
        )
        return
    
    await set_clean_type(chat_id, clean_type)
    clear_chat_cache(chat_id)
    cache_settings(chat_id, clean_type)
    
    await update.effective_message.reply_text(
        f"✅ Cleaning enabled: **{clean_type}**",
        parse_mode="Markdown"
    )


@Command("cleancommandoff")
@only_groups
@admin_check("can_change_info", protect_target=False)
async def clean_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await disable_cleaning(chat_id)
    clear_chat_cache(chat_id)
    await update.effective_message.reply_text(font("✅ Cleaning **disabled**"), parse_mode="Markdown")


@Messages(filters=filters.COMMAND, group=-76)
async def auto_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.from_user:
        return
    
    chat_id = msg.chat.id
    user_id = msg.from_user.id
    
    clean_type = get_settings_cache(chat_id)
    if clean_type is None:
        clean_type = await get_clean_type(chat_id)
        if clean_type:
            cache_settings(chat_id, clean_type)
    
    if not clean_type:
        return
    
    bot_can_delete = get_bot_perms_cache(chat_id)
    if bot_can_delete is None:
        try:
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            bot_can_delete = bot_member.status in ["administrator", "creator"] and bot_member.can_delete_messages
            cache_bot_perms(chat_id, bot_can_delete)
        except Exception:
            return
    
    if not bot_can_delete:
        return
    
    if clean_type == "all":
        await safe_delete(msg)
        return
    
    is_admin = get_admin_cache(chat_id, user_id)
    if is_admin is None:
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            is_admin = member.status in ["administrator", "creator"]
            cache_admin(chat_id, user_id, is_admin)
        except Exception:
            is_admin = False
            cache_admin(chat_id, user_id, False)
    
    if clean_type == "admin" and is_admin:
        await safe_delete(msg)
    elif clean_type == "user" and not is_admin:
        await safe_delete(msg)
