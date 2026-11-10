from AloneX import font, pbot, prefix_cmds
import asyncio
from datetime import datetime
from telegram import constants, MessageEntity, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, TimedOut, NetworkError
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM, Message, CallbackQuery
from pyrogram.enums import ButtonStyle, ChatMemberStatus
from AloneX.helpers.decorator import protected_ids
from AloneX.db.greetings import (
    get_welcome, set_welcome, clear_welcome, set_welcome_time,
    get_goodbye, set_goodbye, clear_goodbye, set_goodbye_time,
    set_welcome_status, get_welcome_status,
    set_goodbye_status, get_goodbye_status,
    check_welcome, check_goodbye,
    set_clean_welcome, get_clean_welcome,
    set_clean_goodbye, get_clean_goodbye
)
from AloneX.db.rules import get_rules_button
from AloneX.helpers.decorator import Command, admin_check, Callbacks, only_groups, get_effective_chat_id
from AloneX.helpers.message_helper import MessageHelper
from AloneX.helpers.log_helper import log_action
import html

__module__ = "𝐆ʀᴇᴇᴛɪɴɢs📕"
__help__ = MessageHelper.get_help_text()

welcome_temp = {}
goodbye_temp = {}

@Command('cleanwelcome')
@admin_check()
async def CleanWelcomeOnOff(update, context):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)

    try:
        args = m.text.split()
        if len(args) < 2:
            status = await get_clean_welcome(chat_id)
            status_text = "✅ Enabled" if status else "❌ Disabled"
            return await m.reply_text(
                f'ℹ️ *Clean Welcome Status:* {status_text}\n\n'
                '*Usage:* `/cleanwelcome on` or `/cleanwelcome off` \n'
                '*(Deletes previous welcome message when a new one is sent)*',
                parse_mode=constants.ParseMode.MARKDOWN
            )

        action = args[1].lower()
        if action not in ['on', 'off']:
            return await m.reply_text(font("❌ Invalid argument! Usage: /cleanwelcome on/off"))

        new_status = (action == 'on')
        await set_clean_welcome(chat_id, new_status)

        status_text = "enabled" if new_status else "disabled"
        return await m.reply_text(font(f"✅ Clean welcome {status_text} for this chat."))

    except Exception as e:
        print(f"[CleanWelcomeOnOff] Error: {e}")
        await m.reply_text(font("❌ An error occurred."))

@Command('cleangoodbye')
@admin_check()
async def CleanGoodbyeOnOff(update, context):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)

    try:
        args = m.text.split()
        if len(args) < 2:
            status = await get_clean_goodbye(chat_id)
            status_text = "✅ Enabled" if status else "❌ Disabled"
            return await m.reply_text(
                f'ℹ️ *Clean Goodbye Status:* {status_text}\n\n'
                '*Usage:* `/cleangoodbye on` or `/cleangoodbye off` \n'
                '*(Deletes previous goodbye message when a new one is sent)*',
                parse_mode=constants.ParseMode.MARKDOWN
            )

        action = args[1].lower()
        if action not in ['on', 'off']:
            return await m.reply_text(font("❌ Invalid argument! Usage: /cleangoodbye on/off"))

        new_status = (action == 'on')
        await set_clean_goodbye(chat_id, new_status)

        status_text = "enabled" if new_status else "disabled"
        return await m.reply_text(font(f"✅ Clean goodbye {status_text} for this chat."))

    except Exception as e:
        print(f"[CleanGoodbyeOnOff] Error: {e}")
        await m.reply_text(font("❌ An error occurred."))

async def is_user_admin(chat_id: int, user_id: int):
    from AloneX.helpers.decorator import user_admin_cache
    if user_id in protected_ids:
        return True
    k = (chat_id, user_id, 'a')
    res = user_admin_cache.get(k)
    if res is not None:
        return res
    try:
        member = await pbot.get_chat_member(chat_id, user_id)
        res = member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
        user_admin_cache[k] = res
        return res
    except:
        return False

async def get_greetings_keyboard(chat_id: int, g_type: str):
    if g_type == "welcome":
        enabled = await get_welcome_status(chat_id)
        cb = "wel_toggle"
    else:
        enabled = await get_goodbye_status(chat_id)
        cb = "gb_toggle"

    if enabled:
        text = f"🟢 {g_type.title()}: ON"
        style = ButtonStyle.SUCCESS
    else:
        text = f"🔴 {g_type.title()}: OFF"
        style = ButtonStyle.DANGER

    return IKM([[IKB(font(text), callback_data=cb, style=style)]])

@pbot.on_message(filters.command("welcome", prefixes=prefix_cmds))
async def WelcomeOnOff(_, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.chat.type == enums.ChatType.PRIVATE:
        from AloneX.db.connection_db import get_connected_chat
        chat_id = await get_connected_chat(user_id) or chat_id

    if not await is_user_admin(chat_id, user_id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    if len(message.command) > 1:
        action = message.command[1].lower()
        if action == "on":
            await set_welcome_status(chat_id, True)
            await message.reply_text(font("✅ Welcome messages have been **enabled**."))
        elif action == "off":
            await set_welcome_status(chat_id, False)
            await message.reply_text(font("🚫 Welcome messages have been **disabled**."))
        else:
            await message.reply_text(font("❌ Invalid argument! Use `on` or `off`."))
        return

    status = await get_welcome_status(chat_id)
    has_custom = await check_welcome(chat_id)
    status_text = "Enabled" if status else "Disabled"
    message_type = "Custom" if has_custom else "Default"
    
    await message.reply_text(
        font(f"👋 **Welcome Status:** {status_text}\n📝 **Message Type:** {message_type}\n\nClick the button below to toggle."),
        reply_markup=await get_greetings_keyboard(chat_id, "welcome")
    )

@pbot.on_message(filters.command("goodbye", prefixes=prefix_cmds))
async def GoodbyeOnOff(_, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.chat.type == enums.ChatType.PRIVATE:
        from AloneX.db.connection_db import get_connected_chat
        chat_id = await get_connected_chat(user_id) or chat_id

    if not await is_user_admin(chat_id, user_id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    if len(message.command) > 1:
        action = message.command[1].lower()
        if action == "on":
            await set_goodbye_status(chat_id, True)
            await message.reply_text(font("✅ Goodbye messages have been **enabled**."))
        elif action == "off":
            await set_goodbye_status(chat_id, False)
            await message.reply_text(font("🚫 Goodbye messages have been **disabled**."))
        else:
            await message.reply_text(font("❌ Invalid argument! Use `on` or `off`."))
        return

    status = await get_goodbye_status(chat_id)
    has_custom = await check_goodbye(chat_id)
    status_text = "Enabled" if status else "Disabled"
    message_type = "Custom" if has_custom else "Default"
    
    await message.reply_text(
        font(f"👋 **Goodbye Status:** {status_text}\n📝 **Message Type:** {message_type}\n\nClick the button below to toggle."),
        reply_markup=await get_greetings_keyboard(chat_id, "goodbye")
    )

@pbot.on_callback_query(filters.regex(r"^(wel|gb)_toggle$"))
async def greetings_toggle_callback(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(font("❌ This button is for admins only!"), show_alert=True)

    g_type = "welcome" if query.data == "wel_toggle" else "goodbye"
    
    if g_type == "welcome":
        enabled = await get_welcome_status(chat_id)
        new_state = not enabled
        await set_welcome_status(chat_id, new_state)
        has_custom = await check_welcome(chat_id)
    else:
        enabled = await get_goodbye_status(chat_id)
        new_state = not enabled
        await set_goodbye_status(chat_id, new_state)
        has_custom = await check_goodbye(chat_id)

    status_text = "Enabled" if new_state else "Disabled"
    message_type = "Custom" if has_custom else "Default"

    await query.message.edit_text(
        font(f"👋 **{g_type.title()} Status:** {status_text}\n📝 **Message Type:** {message_type}\n\nClick the button below to toggle."),
        reply_markup=await get_greetings_keyboard(chat_id, g_type)
    )
    await query.answer(font(f"{g_type.title()} {'Enabled' if new_state else 'Disabled'}"))

@Command('setgoodbyetime')
@admin_check("can_change_info", protect_target=False)
async def SetGoodByeTime(update, context):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    
    try:
        args = m.text.split()
        if len(args) < 2:
            return await m.reply_text(
                '⚠️ *Usage:* `/setgoodbyetime <seconds>`\n'
                '*Example:* `/setgoodbyetime 30`\n'
                '*Range:* 5-86400 seconds (5 sec - 24 hours)',
                parse_mode=constants.ParseMode.MARKDOWN
            )
        
        time_val = MessageHelper.validate_time(args[1])
        if time_val is None:
            return await m.reply_text(
                '❌ *Invalid time value!*\n'
                'Please provide a number between 5 and 86400 seconds.',
                parse_mode=constants.ParseMode.MARKDOWN
            )
        
        if await set_goodbye_time(chat_id, time_val):
            return await m.reply_text(
                f"✅ *Goodbye auto-delete time set to {time_val} seconds.*",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        else:
            return await m.reply_text(
                'ℹ️ *Please set a goodbye message first using /setgoodbye*',
                parse_mode=constants.ParseMode.MARKDOWN
            )
    
    except Exception as e:
        print(f"[SetGoodByeTime] Error: {e}")
        await m.reply_text(font("❌ An error occurred while setting goodbye time."))

@Command('setwelcometime')
@admin_check("can_change_info", protect_target=False)
async def SetWelcomeTime(update, context):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    
    try:
        args = m.text.split()
        if len(args) < 2:
            return await m.reply_text(
                '⚠️ *Usage:* `/setwelcometime <seconds>`\n'
                '*Example:* `/setwelcometime 30`\n'
                '*Range:* 5-86400 seconds (5 sec - 24 hours)',
                parse_mode=constants.ParseMode.MARKDOWN
            )
        
        time_val = MessageHelper.validate_time(args[1])
        if time_val is None:
            return await m.reply_text(
                '❌ *Invalid time value!*\n'
                'Please provide a number between 5 and 86400 seconds.',
                parse_mode=constants.ParseMode.MARKDOWN
            )
        
        if await set_welcome_time(chat_id, time_val):
            return await m.reply_text(
                f"✅ *Welcome auto-delete time set to {time_val} seconds.*",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        else:
            return await m.reply_text(
                'ℹ️ *Please set a welcome message first using /setwelcome*',
                parse_mode=constants.ParseMode.MARKDOWN
            )
    
    except Exception as e:
        print(f"[SetWelcomeTime] Error: {e}")
        await m.reply_text(font("❌ An error occurred while setting welcome time."))

@Callbacks(r"(^gb_chk|^gb_verify|^gb_cancel)")
@admin_check("can_change_info", protect_target=False)
async def GoodbyeSettings(update, context):
    query = update.callback_query
    user = query.from_user
    m = update.effective_message
    
    try:
        cmd, chat_id = query.data.split('#')
        chat_id = int(chat_id)
        chat = m.chat

        MessageHelper.cleanup_temp_data(goodbye_temp, chat_id)
        
        if cmd == "gb_cancel":
            if chat_id in goodbye_temp:
                del goodbye_temp[chat_id]
            return await m.edit_text(font("❌ *Goodbye setup cancelled.*"), parse_mode=constants.ParseMode.MARKDOWN)

        elif cmd == "gb_verify":
            data = goodbye_temp.get(chat_id)
            if not data:
                return await query.answer(font("❌ Setup data expired. Please try again."), show_alert=True)
            
            await set_goodbye(
                chat_id,
                text=data.get('text'), 
                file_id=data.get('file_id'),
                file_type=data.get('file_type'),
                keyboard=data.get('keyboard'),
                has_rules_button=data.get('has_rules_button', False),
                has_rules_same=data.get('has_rules_same', False)
            )
            del goodbye_temp[chat_id]
            
            rules_info = " (with Rules button)" if data.get('has_rules_button') else ""
            return await m.edit_text(
                f"✅ *Goodbye message successfully set for {chat.title}!*{rules_info}", 
                parse_mode=constants.ParseMode.MARKDOWN
            )
            
        elif cmd == "gb_chk":
            data = goodbye_temp.get(chat_id)
            if not data:
                return await query.answer(font("❌ Setup data expired. Please try again."), show_alert=True)
            
            rules_button_text = None
            if data.get('has_rules_button'):
                rules_button_text = await get_rules_button(chat_id)
                if not rules_button_text:
                    rules_button_text = "Rules"
            
            await MessageHelper.send_message(
                context.bot, 
                chat_id, 
                data, 
                user, 
                chat, 
                context,
                rules_button_text
            )
            
            await query.answer(font("👀 Preview sent above!"), show_alert=False)
    
    except Exception as e:
        print(f"[GoodbyeSettings] Error: {e}")
        await query.answer(font("❌ An error occurred."), show_alert=True)

@Callbacks(r"(^wel_chk|^wel_verify|^wel_cancel)")
@admin_check("can_change_info", protect_target=False)
async def WelcomeSettings(update, context):
    query = update.callback_query
    user = query.from_user
    m = update.effective_message
    
    try:
        cmd, chat_id = query.data.split('#')
        chat_id = int(chat_id)
        chat = m.chat

        MessageHelper.cleanup_temp_data(welcome_temp, chat_id)
        
        if cmd == "wel_cancel":
            if chat_id in welcome_temp:
                del welcome_temp[chat_id]
            return await m.edit_text(font("❌ *Welcome setup cancelled.*"), parse_mode=constants.ParseMode.MARKDOWN)

        elif cmd == "wel_verify":
            data = welcome_temp.get(chat_id)
            if not data:
                return await query.answer(font("❌ Setup data expired. Please try again."), show_alert=True)
            
            await set_welcome(
                chat_id,
                text=data.get('text'), 
                file_id=data.get('file_id'),
                file_type=data.get('file_type'),
                keyboard=data.get('keyboard'),
                has_rules_button=data.get('has_rules_button', False),
                has_rules_same=data.get('has_rules_same', False)
            )
            del welcome_temp[chat_id]
            
            rules_info = " (with Rules button)" if data.get('has_rules_button') else ""
            return await m.edit_text(
                f"✅ *Welcome message successfully set for {chat.title}!*{rules_info}", 
                parse_mode=constants.ParseMode.MARKDOWN
            )
            
        elif cmd == "wel_chk":
            data = welcome_temp.get(chat_id)
            if not data:
                return await query.answer(font("❌ Setup data expired. Please try again."), show_alert=True)
            
            rules_button_text = None
            if data.get('has_rules_button'):
                rules_button_text = await get_rules_button(chat_id)
                if not rules_button_text:
                    rules_button_text = "Rules"
            
            await MessageHelper.send_message(
                context.bot, 
                chat_id, 
                data, 
                user, 
                chat, 
                context,
                rules_button_text
            )
            
            await query.answer(font("👀 Preview sent above!"), show_alert=False)
    
    except Exception as e:
        print(f"[WelcomeSettings] Error: {e}")
        await query.answer(font("❌ An error occurred."), show_alert=True)

@Command('cleargoodbye')
@admin_check("can_change_info", protect_target=False)
async def ClearGoodbye(update, context):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    
    try:
        if await clear_goodbye(chat_id):
            return await m.reply_text(font("✅ *Cleared custom goodbye message.*"), parse_mode=constants.ParseMode.MARKDOWN)
        else:
            return await m.reply_text(font("🤷 *No custom goodbye message set yet.*"), parse_mode=constants.ParseMode.MARKDOWN)
    except Exception as e:
        print(f"[ClearGoodbye] Error: {e}")
        await m.reply_text(font("❌ An error occurred while clearing goodbye message."))

@Command('clearwelcome')
@admin_check('can_change_info')
async def ClearWelcome(update, context):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    
    try:
        if await clear_welcome(chat_id):
            return await m.reply_text(font("✅ *Cleared custom welcome message.*"), parse_mode=constants.ParseMode.MARKDOWN)
        else:
            return await m.reply_text(font("🤷 *No custom welcome message set yet.*"), parse_mode=constants.ParseMode.MARKDOWN)
    except Exception as e:
        print(f"[ClearWelcome] Error: {e}")
        await m.reply_text(font("❌ An error occurred while clearing welcome message."))

@Command('getgoodbye')
@admin_check("can_change_info", protect_target=False)
async def GetGoodbye(update, context):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    user = m.from_user
    
    try:
        data = await get_goodbye(chat_id)
        if not data:
            return await m.reply_text(font("🤷 *No custom goodbye set yet.*"), parse_mode=constants.ParseMode.MARKDOWN)
        
        rules_button_text = None
        if data.get('has_rules_button'):
            rules_button_text = await get_rules_button(chat_id)
            if not rules_button_text:
                rules_button_text = "Rules"
        
        await MessageHelper.send_message(
            context.bot, 
            chat_id, 
            data, 
            user, 
            m.chat, 
            context,
            rules_button_text
        )
    
    except Exception as e:
        print(f"[GetGoodbye] Error: {e}")
        await m.reply_text(font("❌ An error occurred while retrieving goodbye message."))

@Command('getwelcome')
@admin_check("can_change_info", protect_target=False)
async def GetWelcome(update, context):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    user = m.from_user
    
    try:
        data = await get_welcome(chat_id)
        if not data:
            return await m.reply_text(font("🤷 *No custom welcome set yet.*"), parse_mode=constants.ParseMode.MARKDOWN)
        
        rules_button_text = None
        if data.get('has_rules_button'):
            rules_button_text = await get_rules_button(chat_id)
            if not rules_button_text:
                rules_button_text = "Rules"
        
        await MessageHelper.send_message(
            context.bot, 
            chat_id, 
            data, 
            user, 
            m.chat, 
            context,
            rules_button_text
        )
    
    except Exception as e:
        print(f"[GetWelcome] Error: {e}")
        await m.reply_text(font("❌ An error occurred while retrieving welcome message."))

@Command('getgoodbye')
@admin_check("can_change_info", protect_target=False)
@only_groups
async def GetGoodbye(update, context):
    m = update.effective_message
    chat_id = m.chat.id
    user = m.from_user
    
    try:
        data = await get_goodbye(chat_id)
        if not data:
            return await m.reply_text(font("🤷 *No custom goodbye set yet.*"), parse_mode=constants.ParseMode.MARKDOWN)
        
        rules_button_text = None
        if data.get('has_rules_button'):
            rules_button_text = await get_rules_button(chat_id)
            if not rules_button_text:
                rules_button_text = "Rules"
        
        await MessageHelper.send_message(
            context.bot, 
            chat_id, 
            data, 
            user, 
            m.chat, 
            context,
            rules_button_text
        )
    
    except Exception as e:
        print(f"[GetGoodbye] Error: {e}")
        await m.reply_text(font("❌ An error occurred while retrieving goodbye message."))

@Command('getwelcome')
@admin_check("can_change_info", protect_target=False)
@only_groups
async def GetWelcome(update, context):
    m = update.effective_message
    chat_id = m.chat.id
    user = m.from_user
    
    try:
        data = await get_welcome(chat_id)
        if not data:
            return await m.reply_text(font("🤷 *No custom welcome set yet.*"), parse_mode=constants.ParseMode.MARKDOWN)
        
        rules_button_text = None
        if data.get('has_rules_button'):
            rules_button_text = await get_rules_button(chat_id)
            if not rules_button_text:
                rules_button_text = "Rules"
        
        await MessageHelper.send_message(
            context.bot, 
            chat_id, 
            data, 
            user, 
            m.chat, 
            context,
            rules_button_text
        )
    
    except Exception as e:
        print(f"[GetWelcome] Error: {e}")
        await m.reply_text(font("❌ An error occurred while retrieving welcome message."))

@Command('setgoodbye')
@admin_check("can_change_info", protect_target=False)
async def SetGoodbye(update, context):
    m = update.effective_message
    r = m.reply_to_message
    chat_id = await get_effective_chat_id(update)
    bot = context.bot
    
    try:
        command_text = m.text or m.caption
        args = command_text.split(maxsplit=1) if command_text else []
        
        if len(args) > 1 and not r:
            original_text = args[1]
            file_type = "text"
            file_id = None
            method = bot.send_message
            
            if m.entities:
                full_text = m.text
                command_end_pos = full_text.find(original_text)
                
                if command_end_pos > 0:
                    text_entities = []
                    for entity in m.entities:
                        if entity.type != 'bot_command':
                            new_offset = entity.offset - command_end_pos
                            
                            if new_offset >= 0 and new_offset < len(original_text):
                                new_entity = MessageEntity(
                                    type=entity.type,
                                    offset=new_offset,
                                    length=entity.length,
                                    url=entity.url if hasattr(entity, 'url') else None,
                                    user=entity.user if hasattr(entity, 'user') else None,
                                    language=entity.language if hasattr(entity, 'language') else None
                                )
                                text_entities.append(new_entity)
                    
                    if text_entities:
                        original_text = MessageHelper.entities_to_markdown(original_text, text_entities)
        
        elif r:
            original_text = (r.caption or r.text) if (r.caption or r.text) else None
            
            if original_text and (r.entities or r.caption_entities):
                entities = r.entities or r.caption_entities
                original_text = MessageHelper.entities_to_markdown(original_text, entities)
            
            file_type, file_id, method = MessageHelper.get_media_info(bot, r)
        
        else:
            return await m.reply_text(
                "❌ *Please provide a goodbye message!*\n\n"
                "*Two ways to set:*\n"
                "1️⃣ `/setgoodbye Your message here`\n"
                "2️⃣ Reply to a message with `/setgoodbye`\n\n"
                "*Supported formats:*\n"
                "• Text messages with formatting\n"
                "• Photos, videos, animations\n" 
                "• Documents, stickers, audio\n"
                "• Messages with inline buttons\n\n"
                "*Use variables like:* `{first}`, `{mention}`, `{chatname}`\n"
                "*Button syntax:* `[Button Text](buttonurl://example.com)`\n"
                "*Same line buttons:* `[Button1](buttonurl://url1:same)[Button2](buttonurl://url2)`\n"
                "*Rules button:* Add `{rules}` anywhere in your message\n"
                "*Special:* `{preview}`, `{nonotif}`, `{protect}`, `{mediaspoiler}`",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        
        keyboard = None
        text = original_text
        has_rules_button = False
        has_rules_same = False
        rules_target_row = -1
        
        if original_text:
            text, keyboard_data, has_rules_button, has_rules_same, rules_target_row = MessageHelper.parse_buttons_from_text(original_text)
            if keyboard_data:
                keyboard = keyboard_data
        
        if r and r.reply_markup and not keyboard:
            keyboard = r.reply_markup.to_dict()
        
        if not file_type or not file_id:
            file_type = "text"
            method = bot.send_message
        
        buttons = MessageHelper.create_setup_buttons('goodbye', chat_id)
        
        goodbye_temp[chat_id] = {
            'text': text,
            'keyboard': keyboard,
            'file_type': file_type,
            'file_id': file_id,
            'method': method,
            'has_rules_button': has_rules_button,
            'has_rules_same': has_rules_same,
            'rules_target_row': rules_target_row,
            'timestamp': datetime.now().timestamp()
        }
        
        rules_info = "\n📋 *Rules button will be added automatically!*" if has_rules_button else ""
        
        await m.reply_text(
            f"⚠️ *Please verify your goodbye message before setting it.*{rules_info}\n\n"
            "• *Preview:* Shows how the message will look\n"
            "• *Confirm:* Sets the message as goodbye\n"
            "• *Cancel:* Cancels the setup process",
            parse_mode=constants.ParseMode.MARKDOWN,
            reply_markup=buttons
        )
    
    except Exception as e:
        print(f"[SetGoodbye] Error: {e}")
        await m.reply_text(font("❌ An error occurred while setting goodbye message."))

@Command('setwelcome')
@admin_check("can_change_info", protect_target=False)
async def SetWelcome(update, context):
    m = update.effective_message
    r = m.reply_to_message
    chat_id = await get_effective_chat_id(update)
    bot = context.bot
    
    try:
        command_text = m.text or m.caption
        args = command_text.split(maxsplit=1) if command_text else []
        
        if len(args) > 1 and not r:
            original_text = args[1]
            file_type = "text"
            file_id = None
            method = bot.send_message
            
            if m.entities:
                full_text = m.text
                command_end_pos = full_text.find(original_text)
                
                if command_end_pos > 0:
                    text_entities = []
                    for entity in m.entities:
                        if entity.type != 'bot_command':
                            new_offset = entity.offset - command_end_pos
                            
                            if new_offset >= 0 and new_offset < len(original_text):
                                new_entity = MessageEntity(
                                    type=entity.type,
                                    offset=new_offset,
                                    length=entity.length,
                                    url=entity.url if hasattr(entity, 'url') else None,
                                    user=entity.user if hasattr(entity, 'user') else None,
                                    language=entity.language if hasattr(entity, 'language') else None
                                )
                                text_entities.append(new_entity)
                    
                    if text_entities:
                        original_text = MessageHelper.entities_to_markdown(original_text, text_entities)
        
        elif r:
            original_text = (r.caption or r.text) if (r.caption or r.text) else None
            
            if original_text and (r.entities or r.caption_entities):
                entities = r.entities or r.caption_entities
                original_text = MessageHelper.entities_to_markdown(original_text, entities)
            
            file_type, file_id, method = MessageHelper.get_media_info(bot, r)
        
        else:
            return await m.reply_text(
                "❌ *Please provide a welcome message!*\n\n"
                "*Two ways to set:*\n"
                "1️⃣ `/setwelcome Your message here`\n"
                "2️⃣ Reply to a message with `/setwelcome`\n\n"
                "*Supported formats:*\n"
                "• Text messages with formatting\n"
                "• Photos, videos, animations\n"
                "• Documents, stickers, audio\n" 
                "• Messages with inline buttons\n\n"
                "*Use variables like:* `{first}`, `{mention}`, `{chatname}`\n"
                "*Button syntax:* `[Button Text](buttonurl://example.com)`\n"
                "*Same line buttons:* `[Button1](buttonurl://url1:same)[Button2](buttonurl://url2)`\n"
                "*Rules button:* Add `{rules}` anywhere in your message\n"
                "*Special:* `{preview}`, `{nonotif}`, `{protect}`, `{mediaspoiler}`",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        
        keyboard = None
        text = original_text
        has_rules_button = False
        has_rules_same = False
        rules_target_row = -1
        
        if original_text:
            text, keyboard_data, has_rules_button, has_rules_same, rules_target_row = MessageHelper.parse_buttons_from_text(original_text)
            if keyboard_data:
                keyboard = keyboard_data
        
        if r and r.reply_markup and not keyboard:
            keyboard = r.reply_markup.to_dict()
        
        if not file_type or not file_id:
            file_type = "text"
            method = bot.send_message
        
        buttons = MessageHelper.create_setup_buttons('welcome', chat_id)
        
        welcome_temp[chat_id] = {
            'text': text,
            'keyboard': keyboard,
            'file_type': file_type,
            'file_id': file_id,
            'method': method,
            'has_rules_button': has_rules_button,
            'has_rules_same': has_rules_same,
            'rules_target_row': rules_target_row,
            'timestamp': datetime.now().timestamp()
        }
        
        rules_info = "\n📋 *Rules button will be added automatically!*" if has_rules_button else ""
        
        await m.reply_text(
            f"⚠️ *Please verify your welcome message before setting it.*{rules_info}\n\n"
            "• *Preview:* Shows how the message will look\n"
            "• *Confirm:* Sets the message as welcome\n"
            "• *Cancel:* Cancels the setup process",
            parse_mode=constants.ParseMode.MARKDOWN,
            reply_markup=buttons
        )
    
    except Exception as e:
        print(f"[SetWelcome] Error: {e}")
        await m.reply_text(font("❌ An error occurred while setting welcome message."))
