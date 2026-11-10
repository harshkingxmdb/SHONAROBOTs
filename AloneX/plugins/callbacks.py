import asyncio
import time
import html
import re
from functools import lru_cache
from AloneX import SUPPORT_CHAT, UPDATE_CHANNEL, BOT_NAME
from AloneX.helpers.pyro_utils import gen_link
from AloneX import font, MODULE, HELP_CMD_IMG, HELP_MODULE_IMG, pbot
from AloneX.plugins.base import SE
from AloneX.helpers.misc import help_button, help_keyboard_data, get_help_button
from pyrogram.enums import ButtonStyle
from pyrogram import filters as pfilters, types as ptypes
import config

_ESCAPE_PATTERN = re.compile(r'([_*\[\]()~`>#+=|{}.!-])')
_ASTERISK_PATTERN = re.compile(r'(?<!\*)\*(?!\*)')
_NEWLINE_PATTERN = re.compile(r'\n{3,}')
_CODE_BLOCK_PATTERN = re.compile(r'```\s*\n?([^`]+?)```')
_INLINE_CODE_PATTERN = re.compile(r'`([^`\n]+)`')
_BOLD_PATTERN = re.compile(r'\*\*([^*\n]+?)\*\*')
_ITALIC_PATTERN = re.compile(r'(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)')
_SPECIAL_CHARS_PATTERN = re.compile(r'[^\w\s\-_!@#$%^&*()+={}[\]|\\:";\'<>,.?/~`]')
_ZERO_WIDTH_PATTERN = re.compile(r'[\u2060\u200b\ufeff]')

help_pagination_sessions = {}
_cleanup_task = None
_bot_info_cache = None

async def get_cached_bot_info(client):
    global _bot_info_cache
    if _bot_info_cache is None:
        _bot_info_cache = await client.get_me()
    return _bot_info_cache

@lru_cache(maxsize=256)
def escape_markdown_v2(text: str) -> str:
    return _ESCAPE_PATTERN.sub(r'\\\1', text)

def convert_markdown_for_pyrogram(text: str) -> str:
    if not text:
        return text
    return _NEWLINE_PATTERN.sub('\n\n', text)

def safe_markdown_text(text) -> str:
    if not text:
        return "No help available for this module."
    text = str(text).strip()
    if not text:
        return "No help available for this module."
    text = html.unescape(text)
    text = _ZERO_WIDTH_PATTERN.sub('', text)
    text = _CODE_BLOCK_PATTERN.sub(r'```\n\1\n```', text)
    text = _INLINE_CODE_PATTERN.sub(r'`\1`', text)
    text = _BOLD_PATTERN.sub(r'**\1**', text)
    text = _ITALIC_PATTERN.sub(r'__\1__', text)
    return convert_markdown_for_pyrogram(text)

@lru_cache(maxsize=128)
def clean_module_name(name: str) -> str:
    if not name:
        return "Unknown Module"
    cleaned = str(name).strip()
    return _SPECIAL_CHARS_PATTERN.sub('', cleaned)

def convert_to_pyrogram_buttons(telegram_pages) -> list:
    pyrogram_pages = []
    for page in telegram_pages:
        pyrogram_page = []
        for row in page:
            pyrogram_row = []
            for button in row:
                try:
                    if button.callback_data:
                        pyrogram_row.append(ptypes.InlineKeyboardButton(text=font(button.text), callback_data=button.callback_data, style=ButtonStyle.SUCCESS))
                except AttributeError:
                    try:
                        if button.url:
                            pyrogram_row.append(ptypes.InlineKeyboardButton(text=font(button.text), url=button.url, style=ButtonStyle.SUCCESS))
                    except AttributeError:
                        continue
            if pyrogram_row:
                pyrogram_page.append(pyrogram_row)
        if pyrogram_page:
            pyrogram_pages.append(pyrogram_page)
    return pyrogram_pages

async def cleanup_old_sessions():
    while True:
        await asyncio.sleep(3600)
        cutoff = time.time() - 3600
        global help_pagination_sessions
        help_pagination_sessions = {k: v for k, v in help_pagination_sessions.items() if v.get("timestamp", 0) > cutoff}

def get_or_create_session(session_id: str, user_id: int, page_num: int = 0) -> dict:
    if session_id not in help_pagination_sessions:
        telegram_pages = help_keyboard_data(user_id=user_id, columns=config.BTN_COLUMNS, rows=config.BTN_ROWS)
        pages = convert_to_pyrogram_buttons(telegram_pages)
        help_pagination_sessions[session_id] = {"pages": pages, "current_page": page_num, "timestamp": time.time(), "user_id": user_id}
    else:
        help_pagination_sessions[session_id]["timestamp"] = time.time()
    return help_pagination_sessions[session_id]

def build_pagination_buttons(page_num: int, total_pages: int, user_id: int) -> list:
    if total_pages <= 1:
        return [ptypes.InlineKeyboardButton(font('❌𝐂ʟᴏsᴇ'), callback_data=f"delete#{user_id}", style=ButtonStyle.DANGER)]
    if page_num == 0:
        return [ptypes.InlineKeyboardButton(font('❌𝐂ʟᴏsᴇ'), callback_data=f"delete#{user_id}", style=ButtonStyle.DANGER), ptypes.InlineKeyboardButton(font('➡️𝐍ᴇxᴛ'), callback_data=f"helpcq_next#{user_id}#{page_num}", style=ButtonStyle.PRIMARY)]
    elif page_num == total_pages - 1:
        return [ptypes.InlineKeyboardButton(font('⬅️𝐁ᴀᴄᴋ'), callback_data=f"helpcq_back#{user_id}#{page_num}", style=ButtonStyle.PRIMARY), ptypes.InlineKeyboardButton(font('❌𝐂ʟᴏsᴇ'), callback_data=f"delete#{user_id}", style=ButtonStyle.DANGER)]
    else:
        return [ptypes.InlineKeyboardButton(font('⬅️𝐁ᴀᴄᴋ'), callback_data=f"helpcq_back#{user_id}#{page_num}", style=ButtonStyle.PRIMARY), ptypes.InlineKeyboardButton(font('➡️𝐍ᴇxᴛ'), callback_data=f"helpcq_next#{user_id}#{page_num}", style=ButtonStyle.PRIMARY)]

@pbot.on_callback_query(pfilters.regex('^stream'))
async def stream_callback(client, query):
    await query.answer(font("⏳ Generating stream link..."))
    data = query.data
    user = query.from_user
    user_id = int(data.split('#')[1])
    if user.id != user_id:
        return await query.answer(font('💀 This is not yours!'), show_alert=True)
    msg = query.message
    log_msg = await msg.forward(config.FILE_DB_CHANNEL)
    watch, download = gen_link(log_msg)
    caption = f"```\n{msg.caption}```"
    caption += ('\n\n✨ **Your stream link has been generated**:\n\n' f'📺 **Watch link**: {watch}\n' f'📩 **Download link**: {download}\n\n' f'❤️ **By {client.me.username}**')
    buttons = [[ptypes.InlineKeyboardButton(font('Watch 📺'), url=watch, style=ButtonStyle.PRIMARY), ptypes.InlineKeyboardButton(font('Download 📩'), url=download, style=ButtonStyle.SUCCESS)]]
    await query.edit_message_caption(caption=caption, reply_markup=ptypes.InlineKeyboardMarkup(buttons))

@pbot.on_callback_query(pfilters.regex('^helpcq'))
async def help_pagination_callback(client, query):
    user = query.from_user
    data = query.data.split('#')
    cmd = data[0]
    user_id = int(data[1])
    page_num = int(data[2])
    
    if user.id != user_id:
        return await query.answer("⚠️ Don't trigger others commands!", show_alert=True)
    
    if cmd == "helpcq_next":
        page_num += 1
        await query.answer()
    elif cmd == "helpcq_back":
        page_num -= 1
        await query.answer()
    
    session_id = f"{query.message.chat.id}_{query.message.id}"
    session = get_or_create_session(session_id, user_id, page_num)
    pages = session["pages"]
    total_pages = len(pages)
    page_num = max(0, min(page_num, total_pages - 1))
    session["current_page"] = page_num
    
    pagination_buttons = build_pagination_buttons(page_num, total_pages, user_id)
    current_page_buttons = [list(row) for row in pages[page_num]]
    current_page_buttons.append(pagination_buttons)
    current_page_buttons.append([ptypes.InlineKeyboardButton(font("🔄 Back"), callback_data=f"back_{user.id}", style=ButtonStyle.PRIMARY)])
    
    try:
        await query.edit_message_reply_markup(reply_markup=ptypes.InlineKeyboardMarkup(current_page_buttons))
    except Exception as e:
        print(f"Error updating markup: {e}")

@pbot.on_callback_query(pfilters.regex('^delete'))
async def delete_message_callback(client, query):
    message = query.message
    data = query.data
    user_id = int(data.split("#")[1]) if "#" in data else int(data.replace("delete", ""))
    
    if query.from_user.id == user_id:
        await query.answer(font("⛔ Deleting..."), show_alert=False)
        await message.delete()
        return
    
    try:
        member = await message.chat.get_member(query.from_user.id)
        if member.status in [ptypes.ChatMemberStatus.ADMINISTRATOR, ptypes.ChatMemberStatus.OWNER]:
            await query.answer(font("⛔ Deleting..."), show_alert=False)
            await message.delete()
            return
    except:
        pass
    
    await query.answer("❌ You can't delete this message!", show_alert=True)

@pbot.on_callback_query(pfilters.regex('^help_callback'))
async def music_help_callback(client, query):
    user = query.from_user
    data = query.data.split()
    
    if len(data) < 2:
        return await query.answer(font("❌ Invalid callback data!"), show_alert=True)
    
    callback_type = data[1]
    if len(data) >= 3 and data[2].isdigit():
        user_id = int(data[2])
        if user.id != user_id:
            return await query.answer("⚠️ Don't trigger others commands!", show_alert=True)
    
    await query.answer(f"Music help for {callback_type}")

@pbot.on_callback_query(pfilters.regex('^help_'))
async def module_help_callback(client, query):
    user = query.from_user
    data = query.data.split("_")
    
    if len(data) < 2:
        return await query.answer(font("❌ Invalid callback data!"), show_alert=True)
    if not data[-1].isdigit():
        return await query.answer(font("❌ Invalid callback data!"), show_alert=True)
    
    user_id = int(data[-1])
    if user.id != user_id:
        return await query.answer("⚠️ Don't trigger others commands!", show_alert=True)
    
    if len(data) == 2:
        await query.answer(font("Here is the help menu..."))
        await asyncio.sleep(0.1)
        
        page_num = 0
        session_id = f"{query.message.chat.id}_{query.message.id}"
        session = get_or_create_session(session_id, user_id, page_num)
        pages = session["pages"]
        total_pages = len(pages)
        
        pagination_buttons = build_pagination_buttons(page_num, total_pages, user.id)
        current_page_buttons = [list(row) for row in pages[page_num]]
        current_page_buttons.append(pagination_buttons)
        current_page_buttons.append([ptypes.InlineKeyboardButton(font("🔄 Back"), callback_data=f"back_{user.id}", style=ButtonStyle.PRIMARY)])
        
        mention = f"[{user.first_name}](tg://user?id={user.id})"
        caption = (
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote><b>Hɪɪ {mention}!\n\n"
            f"**Nᴇᴇᴅ ʜᴇʟᴘ ᴏʀ ᴡᴀɴᴛ ᴛᴏ sᴜᴘᴘᴏʀᴛ ᴜs?**\n\n"
            f"- /support : ᴄᴏɴɴᴇᴄᴛ ᴡɪᴛʜ ᴏᴜʀ sᴜᴘᴘᴏʀᴛ.\n"
            f"- /donate : ꜰᴏʀ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ ᴀʙᴏᴜᴛ ᴅᴏɴᴀᴛɪᴏɴꜱ!\n"
            f"- /privacy : ʟᴇᴀʀɴ ʜᴏᴡ ᴡᴇ ᴘʀᴏᴛᴇᴄᴛ ʏᴏᴜʀ ᴘʀɪᴠᴀᴄʏ.\n"
            f"- ɪɴ ᴀ ɢʀᴏᴜᴘ: ɢᴇᴛ ʏᴏᴜʀ ɢʀᴏᴜᴘ ꜱᴇᴛᴛɪɴɢꜱ.</b></blockquote>\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
        
        try:
            await query.message.delete()
        except:
            pass

        import random
        from AloneX.plugins.base import _sp
        await _sp(cid=query.message.chat.id, p=config.HELP_CMD_IMG, c=caption, rm=ptypes.InlineKeyboardMarkup(current_page_buttons), eid=random.choice(SE))
        
    elif len(data) == 3:
        module_key = data[1]
        await query.answer(f"Here is the help for {module_key}")
        await asyncio.sleep(0.1)
        
        help_text = MODULE.get(module_key, "No help found for this module.")
        try:
            clean_help_text = safe_markdown_text(help_text)
            clean_module_name_display = clean_module_name(module_key)
            text = (
                f"**⚡ Help for the module**: **{clean_module_name_display.upper()}**\n\n"
                f"{clean_help_text}"
            )
            buttons = [[ptypes.InlineKeyboardButton(font("🔄 Back"), callback_data=f"help_{user.id}", style=ButtonStyle.PRIMARY)]]

            if len(text) > 1024:
                try:
                    await query.message.delete()
                except:
                    pass
                await client.send_message(
                    chat_id=query.message.chat.id,
                    text=text,
                    reply_markup=ptypes.InlineKeyboardMarkup(buttons),
                    disable_web_page_preview=True
                )
            else:
                await query.edit_message_caption(caption=text, reply_markup=ptypes.InlineKeyboardMarkup(buttons))
        except Exception as e:
            print(f"Error in module help for {module_key}: {e}")
            try:
                fallback_text = f"**Help for module: {module_key.upper()}**\n\n{str(help_text)}"
                fallback_text = html.escape(fallback_text)
                buttons = [[ptypes.InlineKeyboardButton(font("🔄 Back"), callback_data=f"help_{user.id}", style=ButtonStyle.PRIMARY)]]
                await query.edit_message_caption(caption=fallback_text, reply_markup=ptypes.InlineKeyboardMarkup(buttons))
            except Exception as fallback_error:
                print(f"Fallback error for {module_key}: {fallback_error}")
                plain_text = f"Help for module: {module_key}\n\n{str(help_text)[:500]}"
                if len(str(help_text)) > 500:
                    plain_text += "..."
                buttons = [[ptypes.InlineKeyboardButton(font("Back"), callback_data=f"help_{user.id}", style=ButtonStyle.PRIMARY)]]
                await query.edit_message_caption(caption=plain_text, reply_markup=ptypes.InlineKeyboardMarkup(buttons))

@pbot.on_callback_query(pfilters.regex(r"^back_[0-9]+$"))
async def back_to_start_callback(client, query):
    data = query.data.split("_")
    
    if len(data) < 2 or not data[1].isdigit():
        return await query.answer(font("❌ Invalid callback data!"), show_alert=True)
    
    user_id = int(data[1])
    if query.from_user.id != user_id:
        return await query.answer("⚠️ You can't trigger others commands!", show_alert=True)
    
    await query.answer(font("Here is the start menu..."))
    
    user = query.from_user
    mention = f"[{user.first_name}](tg://user?id={user.id})"
    bot_info = await get_cached_bot_info(client)
    bot_mention = f"[{bot_info.first_name}](tg://user?id={bot_info.id})"
    bot_username = bot_info.username
    
    support_url = SUPPORT_CHAT if SUPPORT_CHAT.startswith("http") else f'https://t.me/{SUPPORT_CHAT.lstrip("@")}'
    update_url = UPDATE_CHANNEL if UPDATE_CHANNEL.startswith("http") else f'https://t.me/{UPDATE_CHANNEL.lstrip("@")}'
    
    buttons = [
        [ptypes.InlineKeyboardButton(font('🎧 Music'), callback_data="mzpanelopen", style=ButtonStyle.SUCCESS),
         ptypes.InlineKeyboardButton(font('⚙ Help ⚙'), callback_data=f'help_{user_id}', style=ButtonStyle.PRIMARY),
         ptypes.InlineKeyboardButton(font('Update 💬'), url=update_url, style=ButtonStyle.SUCCESS)],
        [ptypes.InlineKeyboardButton(font("📝 Switch Too Inline 📝"), switch_inline_query_current_chat="", style=ButtonStyle.DANGER)],
        [ptypes.InlineKeyboardButton(font('➕ Add Me Else Your Group ➕'), url=f'https://t.me/{bot_username}?startgroup=true', style=ButtonStyle.SUCCESS)]
      #  [ptypes.InlineKeyboardButton(font('𓊈💥🔥𝔻eͥѵeͣlͫ𐍉קeℝ🔥💥𓊉'), user_id=config.ALONE_OWNER_ID, style=ButtonStyle.DANGER)]
    ]
    caption = (
        f"<blockquote><b>**⍣ 𝖧𝖾𝗒𝖺 {mention} {bot_mention} 𝖨'𝗆 𝖠𝗇 𝖠𝖽𝗏𝖺𝗇𝖼𝖾 𝖠𝖨 𝖨𝗇𝗍𝖾𝗀𝗋𝖺𝗍𝖾𝖽 𝖶𝗂𝗍𝗁 𝖱𝗈𝖻𝗈𝗍, 𝖨'𝗅𝗅 𝖬𝖺𝗇𝖺𝗀𝖾 𝖸𝗈𝗎𝗋 𝖦𝗋𝗈𝗎𝗉 𝖤𝖺𝗌𝗂𝗅𝗒.**</b></blockquote>\n"
        f"──────────────────────\n"
        f"<blockquote><b>**➛ 70+ 𝖬𝗎𝗅𝗍𝗂𝗉𝗅𝖾 𝖥𝖾𝖺𝗍𝗎ʀ𝖾𝗌 𝖶𝗂𝗍𝗁 𝖠𝗂**\n"
        f"**➛ E𝖺𝗌𝗒 𝖳𝗈 𝖴𝗌𝖾, 𝖠𝗅𝗅 𝖨𝗇 𝖮𝗇𝖾 𝖡𝗈𝗍**\n"
        f"**➛ 𝖲𝖺𝖿𝖾𝗌𝗍 𝖦𝗋𝗈𝗎𝗉 𝖬𝖺𝗇𝖺𝗀𝖾𝗆𝖾𝗇𝗍 𝖡𝗈𝗍**</b></blockquote>\n"
        f"──────────────────────\n"
        f"<blockquote><b>**⍣ 𝖧𝗂𝗍 𝖳𝗁𝖾 /help 𝖡𝗎𝗍𝗍𝗈𝗇 𝖳𝗈 𝖪𝗇𝗈𝗐 𝖬𝗒 𝖠𝖻𝗂𝗅𝗂𝗍𝗂𝖾𝗌</b></blockquote>**"
    )
    
    try:
        await query.message.delete()
    except:
        pass

    import random
    from AloneX.plugins.base import _sp
    await _sp(cid=query.message.chat.id, p=config.PM_START_IMG, c=caption, rm=ptypes.InlineKeyboardMarkup(buttons), eid=random.choice(SE))



@pbot.on_callback_query(pfilters.regex(r"^mzpanelopen$"))
async def open_music_help(client, query: ptypes.CallbackQuery):
    """The Music button of the start menu opens the music command panel."""
    try:
        from pyrogram.enums import ParseMode
        from AloneX.music.runner import is_active
        if not is_active():
            return await query.answer(
                font("🎧 Music system is not active right now. Please try again later."),
                show_alert=True,
            )

        from AloneX.music import lang as music_lang
        from AloneX.music.helpers import buttons as music_buttons

        message = query.message
        chat_lang = await music_lang.get_lang(message.chat.id)
        markup = music_buttons.help_markup(chat_lang)
        text = chat_lang["help_menu"]
        await query.answer()

        if message.photo or message.video or message.animation or message.document:
            # The start menu is a media message (video/photo + caption). Page navigation of the
            # music panel edits plain text, so swap it for a fresh text panel.
            try:
                await message.delete()
            except Exception:
                pass
            await client.send_message(
                message.chat.id, text, reply_markup=markup, parse_mode=ParseMode.HTML
            )
        else:
            await message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    except Exception as e:
        print(f"[MUSIC HELP OPEN ERROR] {e}")
        try:
            await query.answer(font("❌ Could not open music help panel."), show_alert=True)
        except Exception:
            pass
