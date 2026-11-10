from AloneX import font
import re
import html
from telegram import Update, constants, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
from telegram.ext import ContextTypes, filters as tg_filters
from AloneX.helpers.decorator import Command, Messages, Callbacks, admin_check, only_groups, spam_control, flood_safe, get_effective_chat_id
from AloneX.helpers.log_helper import log_action
from AloneX.db.filter import *
from AloneX.helpers.markdown_parser import parse_buttons_from_text, dict_to_keyboard
import asyncio

__module__ = "𝐅ɪʟᴛᴇʀs⏩"
__help__ = """
❂ *Filters Module* — Automate responses in your group!

❂ *Description*:
Set custom keywords in your chat. When a user sends a message containing a filtered word, the bot automatically replies with the preset response.

────────────────────────

 *Admin Only Commands*:
❂ /filter <keyword> <reply> — Add a filter with a specific keyword and response.
❂ /stop <keyword> — Remove a filter by its keyword.
❂ /filters — Show all active filters in the chat.
❂ /stopall — Delete all filters in the chat.
"""

@flood_safe
async def safe_reply_text(message, text, **kwargs):
    return await message.reply_text(text, **kwargs)

@flood_safe
async def safe_reply_photo(message, photo, **kwargs):
    return await message.reply_photo(photo, **kwargs)

@flood_safe
async def safe_reply_document(message, document, **kwargs):
    return await message.reply_document(document, **kwargs)

@flood_safe
async def safe_reply_video(message, video, **kwargs):
    return await message.reply_video(video, **kwargs)

@flood_safe
async def safe_reply_sticker(message, sticker, **kwargs):
    return await message.reply_sticker(sticker, **kwargs)

@flood_safe
async def safe_reply_audio(message, audio, **kwargs):
    return await message.reply_audio(audio, **kwargs)

@flood_safe
async def safe_reply_voice(message, voice, **kwargs):
    return await message.reply_voice(voice, **kwargs)

@flood_safe
async def safe_reply_animation(message, animation, **kwargs):
    return await message.reply_animation(animation, **kwargs)

def _text_with_entities_as_html(message):
    text = message.text or message.caption or ""
    if not text:
        return ""
    entities = getattr(message, "entities", None) or getattr(message, "caption_entities", None) or []
    if not entities:
        return html.escape(text)
    res = text
    for ent in sorted(entities, key=lambda e: e.offset, reverse=True):
        start, end = ent.offset, ent.offset + ent.length
        segment = res[start:end]
        if ent.type == MessageEntity.TEXT_LINK:
            replacement = f'<a href="{html.escape(ent.url, quote=True)}">{html.escape(segment)}</a>'
        elif ent.type == MessageEntity.TEXT_MENTION:
            user = getattr(ent, "user", None)
            if user:
                replacement = f'<a href="tg://user?id={user.id}">{html.escape(segment)}</a>'
            else:
                replacement = html.escape(segment)
        elif ent.type == MessageEntity.URL:
            replacement = f'<a href="{html.escape(segment, quote=True)}">{html.escape(segment)}</a>'
        elif ent.type == MessageEntity.BOLD:
            replacement = f'<b>{html.escape(segment)}</b>'
        elif ent.type == MessageEntity.ITALIC:
            replacement = f'<i>{html.escape(segment)}</i>'
        elif ent.type == MessageEntity.CODE:
            replacement = f'<code>{html.escape(segment)}</code>'
        elif ent.type == MessageEntity.PRE:
            replacement = f'<pre>{html.escape(segment)}</pre>'
        elif ent.type == MessageEntity.UNDERLINE:
            replacement = f'<u>{html.escape(segment)}</u>'
        elif ent.type == MessageEntity.STRIKETHROUGH:
            replacement = f'<s>{html.escape(segment)}</s>'
        else:
            replacement = html.escape(segment)
        res = res[:start] + replacement + res[end:]
    return res

@Messages(filters=~tg_filters.COMMAND & tg_filters.ChatType.GROUPS)
@spam_control
async def filter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_id = message.chat.id
    text = (message.text or message.caption or "").lower()
    
    chat_filters = await get_filters(chat_id)
    if not chat_filters:
        return
    
    for f in chat_filters:
        trigger = f["trigger"].lower()
        pattern = rf"(?<!\w){re.escape(trigger)}(?!\w)"
        if re.search(pattern, text):
            rtype = f["reply_type"]
            rdata = f["reply_data"]
            caption = f.get("caption", "")
            buttons_data = f.get("buttons")
            keyboard = dict_to_keyboard(buttons_data) if buttons_data else None

            try:
                if rtype == "text":
                    await safe_reply_text(message, rdata, parse_mode="HTML", disable_web_page_preview=True, reply_markup=keyboard)
                elif rtype == "photo":
                    await safe_reply_photo(message, rdata, caption=caption if caption else None, parse_mode="HTML" if caption else None, reply_markup=keyboard)
                elif rtype == "document":
                    await safe_reply_document(message, rdata, caption=caption if caption else None, parse_mode="HTML" if caption else None, reply_markup=keyboard)
                elif rtype == "video":
                    await safe_reply_video(message, rdata, caption=caption if caption else None, parse_mode="HTML" if caption else None, reply_markup=keyboard)
                elif rtype == "sticker":
                    await safe_reply_sticker(message, rdata, reply_markup=keyboard)
                elif rtype == "audio":
                    await safe_reply_audio(message, rdata, caption=caption if caption else None, parse_mode="HTML" if caption else None, reply_markup=keyboard)
                elif rtype == "voice":
                    await safe_reply_voice(message, rdata, caption=caption if caption else None, parse_mode="HTML" if caption else None, reply_markup=keyboard)
                elif rtype == "animation":
                    await safe_reply_animation(message, rdata, caption=caption if caption else None, parse_mode="HTML" if caption else None, reply_markup=keyboard)
            except:
                pass
            break

@Command("filter", block=True)
@admin_check("can_change_info", protect_target=False)
@spam_control
async def add_filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_id = await get_effective_chat_id(update)
    reply_msg, args = message.reply_to_message, context.args
    
    if not reply_msg or not args:
        return await safe_reply_text(message, "❌ Reply to a message with <code>/filter trigger</code>", parse_mode="HTML")
    
    raw_triggers = " ".join(args)
    triggers = [t.strip().lower() for t in re.split(r"[,\|]+", raw_triggers) if t.strip()]
    if not triggers:
        return await safe_reply_text(message, "❌ Trigger cannot be empty!")
    
    caption_html = None
    keyboard_data = None

    if reply_msg.text:
        reply_type = "text"
        raw_text = _text_with_entities_as_html(reply_msg)
        reply_data, keyboard_data = parse_buttons_from_text(raw_text)
    elif reply_msg.photo:
        reply_type = "photo"
        reply_data = reply_msg.photo[-1].file_id
        if reply_msg.caption:
            caption_raw = _text_with_entities_as_html(reply_msg)
            caption_html, keyboard_data = parse_buttons_from_text(caption_raw)
    elif reply_msg.document:
        reply_type = "document"
        reply_data = reply_msg.document.file_id
        if reply_msg.caption:
            caption_raw = _text_with_entities_as_html(reply_msg)
            caption_html, keyboard_data = parse_buttons_from_text(caption_raw)
    elif reply_msg.video:
        reply_type = "video"
        reply_data = reply_msg.video.file_id
        if reply_msg.caption:
            caption_raw = _text_with_entities_as_html(reply_msg)
            caption_html, keyboard_data = parse_buttons_from_text(caption_raw)
    elif reply_msg.sticker:
        reply_type = "sticker"
        reply_data = reply_msg.sticker.file_id
    elif reply_msg.audio:
        reply_type = "audio"
        reply_data = reply_msg.audio.file_id
        if reply_msg.caption:
            caption_raw = _text_with_entities_as_html(reply_msg)
            caption_html, keyboard_data = parse_buttons_from_text(caption_raw)
    elif reply_msg.voice:
        reply_type = "voice"
        reply_data = reply_msg.voice.file_id
        if reply_msg.caption:
            caption_raw = _text_with_entities_as_html(reply_msg)
            caption_html, keyboard_data = parse_buttons_from_text(caption_raw)
    elif reply_msg.animation:
        reply_type = "animation"
        reply_data = reply_msg.animation.file_id
        if reply_msg.caption:
            caption_raw = _text_with_entities_as_html(reply_msg)
            caption_html, keyboard_data = parse_buttons_from_text(caption_raw)
    else:
        return await safe_reply_text(message, "❌ Unsupported message type!")
    
    added, updated = [], []
    for trigger in triggers:
        existed = await get_filter_by_trigger(chat_id, trigger)
        if caption_html or reply_type != "text":
            await add_filter_with_caption(chat_id, trigger, reply_type, reply_data, message.from_user.id, caption_html, keyboard_data)
        else:
            await add_filter(chat_id, trigger, reply_type, reply_data, message.from_user.id, keyboard_data)
        if existed:
            updated.append(trigger)
        else:
            added.append(trigger)
    
    resp = []
    if added:
        resp.append(f"✅ Added: {', '.join(f'<code>{t}</code>' for t in added)}")
    if updated:
        resp.append(f"🔄 Updated: {', '.join(f'<code>{t}</code>' for t in updated)}")

    title = update.effective_chat.title
    if chat_id != update.effective_chat.id:
        try:
            target_chat = await context.bot.get_chat(chat_id)
            title = target_chat.title
        except:
            title = str(chat_id)

    log_text = f"⏩ <b>Filter Added/Updated</b>\n" \
               f"<b>Group:</b> {html.escape(title)}\n" \
               f"<b>Triggers:</b> {', '.join(triggers)}\n" \
               f"<b>By:</b> {update.effective_user.mention_html()}"
    asyncio.create_task(log_action(context.bot, chat_id, "filters", log_text))

    return await safe_reply_text(message, "\n".join(resp), parse_mode="HTML")

@Command("filters", block=True)
@admin_check("can_change_info", protect_target=False)
@spam_control
async def list_filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_id = await get_effective_chat_id(update)
    filters_ = await get_filters(chat_id)
    if not filters_:
        return await safe_reply_text(message, "📝 No filters set in this chat.")
    title = update.effective_chat.title
    if chat_id != update.effective_chat.id:
        try:
            target_chat = await context.bot.get_chat(chat_id)
            title = target_chat.title
        except:
            title = str(chat_id)

    msg = f"📝 <b>Filters in {title} ({len(filters_)}):</b>\n\n"
    msg += "\n".join(f"<b>{i}.</b> <code>{f['trigger']}</code> — <i>{f['reply_type']}</i>" for i, f in enumerate(filters_, 1))
    await safe_reply_text(message, msg, parse_mode="HTML")

@Command("stop", block=True)
@admin_check("can_change_info", protect_target=False)
@spam_control
async def stop_filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat_id = await get_effective_chat_id(update)
    args = context.args
    if not args:
        # bare "/stop" stops the music stream (handled by the music system) -> stay silent
        try:
            from AloneX.music.runner import is_active as _music_active
            if _music_active():
                return
        except Exception:
            pass
        return await safe_reply_text(message, "❌ Usage: /stop <trigger>")
    raw_triggers = " ".join(args)
    triggers = [t.strip().lower() for t in re.split(r"[,\|]+", raw_triggers) if t.strip()]
    if not triggers:
        return await safe_reply_text(message, "❌ Trigger cannot be empty!")
    removed, not_found = [], []
    for trigger in triggers:
        if not await get_filter_by_trigger(chat_id, trigger):
            not_found.append(trigger)
            continue
        await remove_filter(chat_id, trigger)
        removed.append(trigger)
    resp = []
    if removed:
        resp.append(f"✅ Removed: {', '.join(f'<code>{t}</code>' for t in removed)}")
    if not_found:
        resp.append(f"❌ Not found: {', '.join(f'<code>{t}</code>' for t in not_found)}")

    if removed:
        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        log_text = f"⏩ <b>Filter Removed</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>Triggers:</b> {', '.join(removed)}\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}"
        asyncio.create_task(log_action(context.bot, chat_id, "filters", log_text))

    return await safe_reply_text(message, "\n".join(resp), parse_mode="HTML")

@Command("stopall", block=True)
@spam_control
async def stop_all_filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message, user = update.effective_message, update.effective_user
    chat_id = await get_effective_chat_id(update)

    try:
        member = await context.bot.get_chat_member(chat_id, user.id)
        if member.status != constants.ChatMemberStatus.OWNER:
             return await safe_reply_text(message, "Only the chat owner can remove all filters.")
    except:
        return await safe_reply_text(message, "Could not verify owner status.")

    count = await get_filter_count(chat_id)
    if count == 0:
        return await safe_reply_text(message, "No filters to remove.")
    buttons = [
        [InlineKeyboardButton(font("✅ Yes, remove all"), callback_data=f"stopall_confirm_{chat_id}_{user.id}")],
        [InlineKeyboardButton(font("❌ Cancel"), callback_data=f"stopall_cancel_{chat_id}_{user.id}")]
    ]
    await safe_reply_text(message, f"⚠️ Are you sure you want to remove all {count} filters?", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

@Callbacks(pattern=r"^stopall_(confirm|cancel)_(-?\d+)_([0-9]+)$", block=True)
async def stopall_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, chat_id, user_id = query.data.split("_")[1:]
    chat_id, user_id = int(chat_id), int(user_id)
    if query.from_user.id != user_id:
        return await query.answer(font("Only the one who initiated this can confirm!"), show_alert=True)
    if action == "cancel":
        await query.edit_message_text(font("❌ Operation cancelled."))
        return await query.answer(font("Cancelled."))
    count = await get_filter_count(chat_id)
    await remove_all_filters(chat_id)
    await query.edit_message_text(f"✅ Removed all {count} filters.")

    log_text = f"🧹 <b>All Filters Removed</b>\n" \
               f"<b>Group:</b> {html.escape(query.message.chat.title)}\n" \
               f"<b>Filters Removed:</b> {count}\n" \
               f"<b>By:</b> {query.from_user.mention_html()}"
    asyncio.create_task(log_action(context.bot, chat_id, "filters", log_text))

    return await query.answer(font("Filters removed."))
