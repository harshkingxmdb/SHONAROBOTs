from AloneX import font
from AloneX.helpers.decorator import Command, only_groups, admin_check, DISABLEABLE_CMDS
from AloneX.db.disable import disable_cmd, enable_cmd, get_disabled
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

__module__ = "𝐃ɪsᴀʙʟᴇ🕳️"

__help__ = """
*Description*:  
This module allows group admins to control which bot commands are active in their group.  
You can temporarily disable commands that may not be appropriate or needed, and re-enable them anytime.


*Commands*:
❂ `/disable` <command> — Disable a specific command in the current group.  
❂ `/enable` <command> — Enable a previously disabled command.  
❂ `/listcmds` — Show all commands that can be toggled.  
❂ `/cmds` — Show currently disabled commands in this group.  

"""
@Command("disable")
@only_groups
@admin_check("can_change_info", protect_target=False)
async def disable_command(update, context):
    msg = update.effective_message

    if len(context.args) < 1:
        return await msg.reply_text(font("⚠️ Usage: /disable <command>"))

    cmd = context.args[0].lower()
    if cmd not in DISABLEABLE_CMDS:
        return await msg.reply_text(font("❌ Not in command disableable list! ।"))

    await disable_cmd(update.effective_chat.id, cmd)
    await msg.reply_text(
        f"🚫 Command <code>{cmd}</code> disabled!",
        parse_mode="HTML"
    )

@Command("enable")
@only_groups
@admin_check("can_change_info", protect_target=False)
async def enable_command(update, context):
    msg = update.effective_message

    if len(context.args) < 1:
        return await msg.reply_text(font("⚠️ Usage: /enable <command>"))

    cmd = context.args[0].lower()
    if cmd not in DISABLEABLE_CMDS:
        return await msg.reply_text(font("❌ This command not in disableable list!"))

    await enable_cmd(update.effective_chat.id, cmd)
    await msg.reply_text(
        f"✅ Command <code>{cmd}</code> enabled!",
        parse_mode="HTML"
    )


@Command("listcmds")
@only_groups
@admin_check("can_change_info", protect_target=False)
async def list_cmds(update, context):
    msg = update.effective_message
    text = "❂ <b>Toggleable Commands:</b>\n\n"
    text += "\n".join(f"- <code>{cmd}</code>" for cmd in DISABLEABLE_CMDS)

    await msg.reply_text(text, parse_mode="HTML")


@Command("cmds")
@only_groups
@admin_check("can_change_info", protect_target=False)
async def cmds_status(update, context):
    """Show only currently disabled commands in this group"""
    msg = update.effective_message
    chat_id = update.effective_chat.id

    disabled = await get_disabled(chat_id)

    if not disabled:
        return await msg.reply_text(font("✅ No command disabled!"))

    text = "🚫 <b>Disabled Commands</b>:\n\n"
    for cmd in disabled:
        text += f"• <code>{cmd}</code>\n"

    await msg.reply_text(text, parse_mode="HTML")
