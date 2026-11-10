from AloneX import font
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from AloneX.helpers.decorator import Command, only_groups, admin_check, get_effective_chat_id
from AloneX.helpers.markdown_parser import (
    parse_buttons_from_text, 
    dict_to_keyboard,
    format_buttons_help,
    extract_button_count
)
from AloneX.db.rules import *
from cachetools import TTLCache

rules_data_cache = TTLCache(maxsize=10000, ttl=3600)
chat_name_cache = TTLCache(maxsize=10000, ttl=7200)

DEFAULT_BUTTON = "Rules"
DEFAULT_MESSAGE = "The group admin has not set any rules for this chat yet.\n\nIt doesn't mean you can do anything!"

__module__ = "𝐑ᴜʟᴇs🚦"
__help__ = """
*Rules🚦*
*Description:*  
Every chat works with different rules; this module will help make those rules clearer!

*Commands:*  
❂ `/rules` - Show the rules button (rules will be displayed in private).  
❂ `/setrules` <text> - Set rules for this chat (supports buttons).  
❂ `/resetrules` - Reset rules to default.  
❂ /privaterules <yes/no> - Toggle between sending rules in private or group.  
❂ `/setrulesbutton` <name> - Set custom name for rules button.  
❂ `/resetrulesbutton` - Reset the rules button to default.  

*Button Format:*
❂ `[Button Text](buttonurl://your-link)`  
❂ `[Button 1](buttonurl://link1:same)[Button 2](buttonurl://link2)`

*Example:*  
`/setrules Be respectful! [Read More](buttonurl://example.com)`
"""

AFFIRMATIVE = {"yes", "on", "true", "1"}
NEGATIVE = {"no", "off", "false", "0"}

async def get_all_rules_data(chat_id):
    cache_key = f"rules_all_{chat_id}"
    cached = rules_data_cache.get(cache_key)
    if cached is not None:
        return cached
    
    rules_text = await get_rules(chat_id)
    rules_keyboard = await get_rules_keyboard(chat_id)
    button_text = await get_rules_button(chat_id)
    is_private = await get_private_rules(chat_id)
    
    result = {
        'rules': rules_text,
        'keyboard': rules_keyboard,
        'button': button_text or DEFAULT_BUTTON,
        'private': is_private if is_private is not None else True
    }
    rules_data_cache[cache_key] = result
    return result

def invalidate_rules_cache(chat_id):
    cache_key = f"rules_all_{chat_id}"
    rules_data_cache.pop(cache_key, None)

async def get_chat_name_cached(bot, chat_id):
    cached = chat_name_cache.get(chat_id)
    if cached:
        return cached
    try:
        chat = await bot.get_chat(chat_id)
        name = chat.title or "This Chat"
        chat_name_cache[chat_id] = name
        return name
    except:
        return "This Chat"

@Command("rules")
@only_groups
async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    data = await get_all_rules_data(chat.id)
    btn_text = data['button']
    
    from pyrogram.enums import ButtonStyle
    button = InlineKeyboardMarkup([[
        InlineKeyboardButton(btn_text, url=f"https://t.me/{context.bot.username}?start=rules_{chat.id}", style=ButtonStyle.PRIMARY)
    ]])
    
    await update.effective_message.reply_text(
        "Please click the button below to see the rules.", 
        reply_markup=button
    )

@Command("setrules")
@admin_check("can_change_info", protect_target=False)
async def setrules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    reply_msg = update.effective_message.reply_to_message
    
    if reply_msg and (reply_msg.text or reply_msg.caption):
        text = reply_msg.text or reply_msg.caption or ""
    else:
        msg_text = update.effective_message.text or update.effective_message.caption or ""
        if msg_text.startswith('/'):
            try:
                text = msg_text.split(' ', 1)[1]
            except IndexError:
                text = ""
        else:
            text = " ".join(context.args)
    
    if not text.strip():
        help_text = format_buttons_help()
        return await update.effective_message.reply_text(
            f"*Usage:* `/setrules <text>`\n"
            f"Or reply to a message with `/setrules`\n\n"
            f"{help_text}",
            parse_mode="Markdown"
        )
    
    clean_text, keyboard_data = parse_buttons_from_text(text)
    
    print(f"[SETRULES] Chat: {chat.id}")
    print(f"[SETRULES] Clean text: {clean_text}")
    print(f"[SETRULES] Keyboard data: {keyboard_data}")
    
    await set_rules(chat_id, clean_text, keyboard_data)
    invalidate_rules_cache(chat_id)
    
    button_count = extract_button_count(text)
    button_info = f"\n✨ With {button_count} button(s)" if button_count > 0 else ""
    
    await update.effective_message.reply_text(
        f"✅ *Rules have been set for this chat.*{button_info}",
        parse_mode="Markdown"
    )

@Command("resetrules")
@admin_check("can_change_info", protect_target=False)
async def resetrules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    await reset_rules(chat_id)
    invalidate_rules_cache(chat_id)
    await update.effective_message.reply_text(font("♻️ Rules have been reset to default."))

@Command("privaterules")
@admin_check("can_change_info", protect_target=False)
async def privaterules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    if not context.args:
        return await update.effective_message.reply_text(font("Usage: /privaterules <yes/no>"))
    
    arg = context.args[0].lower()
    if arg in AFFIRMATIVE:
        await set_private_rules(chat_id, True)
        invalidate_rules_cache(chat_id)
        await update.effective_message.reply_text(font("🔒 Rules will now be sent in private."))
    elif arg in NEGATIVE:
        await set_private_rules(chat_id, False)
        invalidate_rules_cache(chat_id)
        await update.effective_message.reply_text(font("📢 Rules will now be shown in group."))
    else:
        await update.effective_message.reply_text(font("Use yes/no or on/off."))

@Command("setrulesbutton")
@admin_check("can_change_info", protect_target=False)
async def setrulesbutton_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    btn_name = " ".join(context.args)
    if not btn_name:
        return await update.effective_message.reply_text(font("Usage: /setrulesbutton <name>"))
    
    await set_rules_button(chat_id, btn_name)
    invalidate_rules_cache(chat_id)
    await update.effective_message.reply_text(f"✅ Rules button set to: {btn_name}")

@Command("resetrulesbutton")
@admin_check("can_change_info", protect_target=False)
async def resetrulesbutton_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    await reset_rules_button(chat_id)
    invalidate_rules_cache(chat_id)
    await update.effective_message.reply_text(font("♻️ Rules button reset to default."))

async def send_rules_private_pyro(user_id: int, chat_id: int):
    from AloneX import pbot
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from pyrogram.enums import ButtonStyle
    import random
    
    data = await get_all_rules_data(chat_id)
    rules_text = data['rules'] or DEFAULT_MESSAGE
    keyboard_data = data.get('keyboard')
    
    buttons = None
    if keyboard_data and 'inline_keyboard' in keyboard_data:
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton(btn['text'], url=btn['url'], style=ButtonStyle.SUCCESS) for btn in row]
            for row in keyboard_data['inline_keyboard']
        ])
    
    chat_name = "This Chat"
    try:
        chat = await pbot.get_chat(chat_id)
        chat_name = chat.title or "This Chat"
    except:
        pass
    
    SE = (5107584321108051014, 5104858069142078462)
    
    await pbot.send_message(
        user_id,
        f"📜 **Rules for {chat_name}:**\n\n{rules_text}",
        reply_markup=buttons,
        effect_id=random.choice(SE)
    )
