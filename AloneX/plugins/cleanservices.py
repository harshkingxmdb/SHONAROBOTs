from AloneX import font
__module__ = "𝐂ʟᴇᴀɴ-𝐒ᴇʀᴠɪᴄᴇ🈂️"
__help__ = """
❂ *CleanService Module* — Auto-delete service messages in groups.

*Commands:*
❂ /cleanservice <type/yes/no/on/off> — Enable cleaning. Types: all, join, leave, 
photo, pin, title, videochat, other
❂ /keepservice <type> — Keep specific service messages while 'all' cleaning is enabled
❂ /nocleanservice <type> — Alias for /keepservice
❂ /cleanservicetypes — Show all available service message types

*Notes:*
- Bot must be admin with delete permission.
- Automatically deletes service messages based on your settings.
- 'all' mode deletes everything except explicitly kept types.
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes, filters
from AloneX.helpers.decorator import Command, only_groups, admin_check, Messages
from AloneX.db.cleanservice_db import get_clean_settings, save_clean_settings

LOGGER = logging.getLogger(__name__)

SERVICE_TYPES = {
    "all": "All service messages",
    "join": "New users joining or being added",
    "leave": "Users leaving or being removed",
    "other": "Miscellaneous (payments, boosts, etc.)",
    "photo": "Chat photos/background changes",
    "pin": "Messages being pinned",
    "title": "Chat/topic title changes",
    "videochat": "Video chat actions (start/end/schedule/add)",
}

KEEP_PREFIX = "keep:"

settings_cache = {}
bot_perms_cache = {}

SERVICE_MAPPING = {
    "new_chat_members": "join",
    "left_chat_member": "leave",
    "pinned_message": "pin",
    "new_chat_title": "title",
    "new_chat_photo": "photo",
    "delete_chat_photo": "photo",
    "video_chat_started": "videochat",
    "video_chat_ended": "videochat",
    "video_chat_scheduled": "videochat",
    "video_chat_participants_invited": "videochat",
    "message_auto_delete_timer_changed": "other",
    "successful_payment": "other",
    "proximity_alert_triggered": "other",
    "boost_added": "other",
    "chat_background_set": "photo",
    "chat_theme_changed": "other",
}

def cache_settings(chat_id, settings):
    settings_cache[chat_id] = settings

def get_cached_settings(chat_id):
    return settings_cache.get(chat_id)

def invalidate_settings_cache(chat_id):
    settings_cache.pop(chat_id, None)

def cache_bot_perms(chat_id, can_delete):
    bot_perms_cache[chat_id] = can_delete

def get_cached_bot_perms(chat_id):
    return bot_perms_cache.get(chat_id)

@Command("cleanservice")
@only_groups
@admin_check("can_change_info", protect_target=False)
async def cleanservice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = update.effective_message
    args = context.args
    if not args:
        asyncio.create_task(msg.reply_text(
            "Usage:\n`/cleanservice <type/yes/no/on/off>`\nExamples:\n"
            "`/cleanservice all` – delete all service messages.\n"
            "`/cleanservice join` – delete join messages.",
            parse_mode="Markdown"
        ))
        return
    arg = args[0].lower()
    clean_types = await get_clean_settings(chat_id) or set()
    if arg in ("yes", "on"):
        keeps = {x for x in clean_types if x.startswith(KEEP_PREFIX)}
        new_clean = {"all"} | keeps
        await save_clean_settings(chat_id, new_clean)
        cache_settings(chat_id, new_clean)
        asyncio.create_task(msg.reply_text(font("✅ Enabled cleaning **all service messages**.")))
        return
    if arg in ("no", "off"):
        await save_clean_settings(chat_id, set())
        invalidate_settings_cache(chat_id)
        asyncio.create_task(msg.reply_text(font("🚫 Disabled cleaning service messages.")))
        return
    if arg not in SERVICE_TYPES:
        asyncio.create_task(msg.reply_text(
            f"❌ Invalid type: `{arg}`\nUse /cleanservicetypes to see all available types.",
            parse_mode="Markdown"
        ))
        return
    if "all" in clean_types:
        clean_types.discard(f"{KEEP_PREFIX}{arg}")
    clean_types.add(arg)
    await save_clean_settings(chat_id, clean_types)
    cache_settings(chat_id, clean_types)
    asyncio.create_task(msg.reply_text(f"✅ Now cleaning **{arg}** messages."))

@Command(["keepservice", "nocleanservice"])
@only_groups
@admin_check("can_change_info", protect_target=False)
async def keepservice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = update.effective_message
    args = context.args
    if not args:
        asyncio.create_task(msg.reply_text(
            "Usage:\n`/keepservice <type>`\nExample:\n`/keepservice pin` – keep pinned messages.",
            parse_mode="Markdown"
        ))
        return
    arg = args[0].lower()
    clean_types = await get_clean_settings(chat_id) or set()
    if arg not in SERVICE_TYPES:
        asyncio.create_task(msg.reply_text(
            f"❌ Invalid type: `{arg}`\nUse /cleanservicetypes to see all available types.",
            parse_mode="Markdown"
        ))
        return
    keep_key = f"{KEEP_PREFIX}{arg}"
    if "all" in clean_types:
        if keep_key in clean_types:
            clean_types.remove(keep_key)
            await save_clean_settings(chat_id, clean_types)
            cache_settings(chat_id, clean_types)
            asyncio.create_task(msg.reply_text(
                f"✅ No longer keeping **{arg}** messages (they will be deleted in 'all' mode)."
            ))
        else:
            clean_types.add(keep_key)
            await save_clean_settings(chat_id, clean_types)
            cache_settings(chat_id, clean_types)
            asyncio.create_task(msg.reply_text(
                f"✅ Keeping **{arg}** messages while 'all' cleaning is enabled."
            ))
        return
    if arg in clean_types:
        clean_types.remove(arg)
        await save_clean_settings(chat_id, clean_types)
        cache_settings(chat_id, clean_types)
        asyncio.create_task(msg.reply_text(f"✅ No longer cleaning **{arg}** messages."))
    else:
        asyncio.create_task(msg.reply_text(f"⚠️ `{arg}` was not being cleaned.", parse_mode="Markdown"))

@Command("cleanservicetypes")
@only_groups
@admin_check("can_change_info", protect_target=False)
async def cleanservicetypes(update: Update, _: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    text = "**Available service message types:**\n\n"
    for k, v in SERVICE_TYPES.items():
        text += f"- `{k}`: {v}\n"
    text += "\nNotes:\n- Use `/cleanservice all` to enable cleaning all.\n- `/keepservice <type>` keeps types when 'all' is on.\n"
    asyncio.create_task(msg.reply_text(text, parse_mode="Markdown"))

@Messages(filters=filters.StatusUpdate.ALL, group=-64)
async def delete_service_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return
    chat_id = msg.chat.id
    clean_types = get_cached_settings(chat_id)
    if clean_types is None:
        clean_types = await get_clean_settings(chat_id)
        if not clean_types:
            return
        cache_settings(chat_id, clean_types)
    if not clean_types:
        return
    bot_can_delete = get_cached_bot_perms(chat_id)
    if bot_can_delete is None:
        try:
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            bot_can_delete = getattr(bot_member, "status", "") in ("administrator", "creator") and getattr(bot_member, "can_delete_messages", False)
            cache_bot_perms(chat_id, bot_can_delete)
        except:
            bot_can_delete = False
            cache_bot_perms(chat_id, False)
    if not bot_can_delete:
        return
    service_type = None
    for attr, ctype in SERVICE_MAPPING.items():
        if getattr(msg, attr, None):
            service_type = ctype
            break
    if not service_type:
        return
    should_delete = False
    if "all" in clean_types:
        if f"{KEEP_PREFIX}{service_type}" not in clean_types:
            should_delete = True
    elif service_type in clean_types:
        should_delete = True
    if should_delete:
        asyncio.create_task(msg.delete())
