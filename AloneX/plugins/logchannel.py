from AloneX import font, pbot, prefix_cmds, app
from telegram import Update, constants
from telegram.ext import ContextTypes, filters, CommandHandler
from AloneX.helpers.decorator import Command, admin_check, only_groups, Messages, get_effective_chat_id, user_admin
from AloneX.db.logchannel_db import (
    set_log_channel, unset_log_channel, get_log_channel,
    enable_log_category, disable_log_category, is_category_enabled,
    num_logchannels, stop_chat_logging
)
import config
import html
from telegram.helpers import escape_markdown

__module__ = "𝐋ᴏɢ-𝐂ʜᴀɴɴᴇʟ📜"
__help__ = """
*Log Channels📜*

*Admins only:*
❂ /logchannel*:* get log channel info
❂ /setlog*:* set the log channel.
❂ /unsetlog*:* unset the log channel.
❂ /log <category>*:* enable a log category.
❂ /nolog <category>*:* disable a log category.
❂ /logcategories*:* list all supported log categories.

*Setting the log channel is done by:*
❂ adding the bot to the desired channel (as an admin!)
❂ sending `/setlog` in the channel
❂ forwarding the `/setlog` to the group
"""

LOG_CATEGORIES = {
    "bans": "Bans and Unbans",
    "mutes": "Mutes and Unmutes",
    "warns": "Warnings",
    "notes": "Note management",
    "filters": "Filter management",
    "locks": "Chat lock changes",
    "cleans": "Cleaning commands",
    "admin": "Admin management",
    "greetings": "Welcome/Goodbye setup",
    "joins": "User join logs",
    "leaves": "User leave logs",
    "blocklists": "Blocklist word logs",
    "rules": "Rules management",
    "antiflood": "Anti-flood logs",
    "reports": "User report logs"
}

@Command("setlog")
@user_admin
async def setlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    message = update.effective_message
    chat = update.effective_chat

    if chat.type == chat.CHANNEL:
        return await message.reply_text(
            "Now, forward the `/setlog` to the group you want to tie this channel to!",
            parse_mode=constants.ParseMode.MARKDOWN
        )

    # Support for different forward detection methods
    log_chat_id = None
    if message.forward_origin and message.forward_origin.type == constants.MessageOriginType.CHANNEL:
        log_chat_id = message.forward_origin.chat.id

    if log_chat_id:
        await set_log_channel(message.chat.id, log_chat_id)
        try:
            await message.delete()
        except Exception:
            pass

        try:
            await bot.send_message(
                log_chat_id,
                f"This channel has been set as the log channel for {message.chat.title or message.chat.first_name}.",
            )
        except Exception:
            pass

        await bot.send_message(message.chat.id, "Successfully set log channel!")
    else:
        await message.reply_text(
            "The steps to set a log channel are:\n"
            " - add bot to the desired channel (as admin)\n"
            " - send `/setlog` in the channel\n"
            " - forward the `/setlog` to the group\n",
            parse_mode=constants.ParseMode.MARKDOWN
        )

@Command("logchannel")
@admin_check()
async def logging(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    message = update.effective_message
    chat_id = await get_effective_chat_id(update)

    log_channel = await get_log_channel(chat_id)
    if log_channel:
        try:
            log_channel_info = await bot.get_chat(log_channel)
            title = log_channel_info.title
        except:
            title = f"Unknown Channel ({log_channel})"

        res = f"This group has all it's logs sent to: {escape_markdown(title)} (`{log_channel}`)"

        res += f"\n\n📊 **Category Status:**\n"
        for cat, desc in LOG_CATEGORIES.items():
            status = "✅" if await is_category_enabled(chat_id, cat) else "❌"
            res += f"• {status} `{cat}`: {desc}\n"

        await message.reply_text(res, parse_mode=constants.ParseMode.MARKDOWN)
    else:
        await message.reply_text("No log channel has been set for this group!")

@Command("unsetlog")
@admin_check("can_change_info")
async def unsetlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    message = update.effective_message
    chat_id = await get_effective_chat_id(update)
    chat_title = update.effective_chat.title

    log_channel = await stop_chat_logging(chat_id)
    if log_channel:
        try:
            await bot.send_message(
                log_channel, f"Channel has been unlinked from {chat_title}"
            )
        except:
            pass
        await message.reply_text("Log channel has been un-set.")
    else:
        await message.reply_text("No log channel has been set yet!")

@Command("log")
@admin_check("can_change_info")
async def log_toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    if not context.args:
        return await update.effective_message.reply_text(font("🙋‍♂️ Specify a category to enable. Use `/logcategories` to see them."))

    cat = context.args[0].lower()
    if cat not in LOG_CATEGORIES:
        return await update.effective_message.reply_text(font("❌ Invalid category."))

    await enable_log_category(chat_id, cat)
    await update.effective_message.reply_text(f"✅ Category `{cat}` will now be logged.")

@Command("nolog")
@admin_check("can_change_info")
async def nolog_toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    if not context.args:
        return await update.effective_message.reply_text(font("🙋‍♂️ Specify a category to disable."))

    cat = context.args[0].lower()
    if cat not in LOG_CATEGORIES:
        return await update.effective_message.reply_text(font("❌ Invalid category."))

    await disable_log_category(chat_id, cat)
    await update.effective_message.reply_text(f"🚫 Category `{cat}` will no longer be logged.")

@Command("logcategories")
async def logcats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = "📋 **Available Log Categories:**\n"
    for cat, desc in LOG_CATEGORIES.items():
        res += f"• `{cat}`: {desc}\n"
    await update.effective_message.reply_text(res)

def __stats__():
    # This is a bit tricky as it is async, normally __stats__ is sync in some bots
    # but we can't easily do it here.
    return ""

async def __migrate__(old_chat_id, new_chat_id):
    from AloneX.db.logchannel_db import set_log_channel, get_log_channel, stop_chat_logging
    log_c = await get_log_channel(old_chat_id)
    if log_c:
        await set_log_channel(new_chat_id, log_c)
        await stop_chat_logging(old_chat_id)

__mod_name__ = "𝐋ᴏɢs"
