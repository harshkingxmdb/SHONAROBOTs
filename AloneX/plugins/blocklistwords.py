import re
import logging
import asyncio
import config
from telegram import constants, ChatPermissions
from telegram.ext import filters

from AloneX import BOT_ID, font
from AloneX.helpers.decorator import Messages, Command, admin_check, only_groups, devs_only, disableable, get_effective_chat_id
from AloneX.helpers.utils import get_as_document
from AloneX.db.blocklistwords import (
    get_words, get_mode, update_mode,
    add_word, remove_word, get_all_chats
)
from AloneX.db.approval_db import is_user_approved
from AloneX.helpers.log_helper import log_action
import html

# ✅ Setup Logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.WARNING,
    format='[%(levelname)s] %(message)s'
)

CHATS = []

__module__ = "𝐁ʟᴏᴄᴋʟɪsᴛ🚫"

__help__ = """
*Blocklist*

*Description:*  
Manage words that are blocked in the chat to prevent unwanted messages.

*Commands:*  
❂ `/addblword <word>` – Add a word to the blocklist  
❂ `/rmblword <word>` – Remove a word from the blocklist  
❂ `/blwords on|off` – Enable or disable blocklist  
❂ `/blwordslist` – Show all blocked words
"""


# ✅ Safe word-boundary match
def search_text(words, text):
    if not text:
        return False
    pattern = "|".join(re.escape(word) for word in words)
    return bool(re.search(rf"\b({pattern})\b", text, re.IGNORECASE))


# ✅ Filter to find and delete blacklisted words
@Messages(filters=((filters.TEXT | filters.CAPTION) & filters.ChatType.GROUPS), group=3)
async def _findAndDelete(update, context):
    m = update.effective_message
    user = update.effective_user
    chat_id = m.chat.id
    text = m.text or m.caption or ""

    if not CHATS:
        CHATS.extend(await get_all_chats())

    if chat_id in CHATS:
        if await is_user_approved(chat_id, user.id):
            return

        mode = await get_mode(chat_id)
        if not mode:
            return

        words = await get_words(chat_id)

        if words and search_text(words, text) and user.id != BOT_ID:
            member = await m.chat.get_member(user.id)
            if member.status not in [constants.ChatMemberStatus.ADMINISTRATOR, constants.ChatMemberStatus.OWNER]:
                try:
                    await m.delete()
                    logger.info(f"[BL] Deleted message from {user.id} containing blocked word.")
                except Exception as e:
                    logger.warning(f"[BL] Deletion error: {e}")


@Command("addblword")
@disableable("addblword")
@admin_check("can_delete_messages")
async def _addBlockListWord(update, context):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    if len(m.text.split(maxsplit=1)) < 2:
        return await m.reply_text(
            "🚫 You need to specify words to block.\n\nExamples:\n"
            "`/addblword porn child abuse`\n"
            "`/addblword\nporn\nchild\nabuse`\n"
            '`/addblword "bad full phrase" word2 word3`  (use quotes for a full phrase)',
            parse_mode=constants.ParseMode.MARKDOWN
        )

    # ✅ Extract words (multi-line OR space separated) + quoted phrases as single items
    raw_text = m.text.split(maxsplit=1)[1]
    phrases = [p.strip().lower() for p in re.findall(r'"([^"]+)"', raw_text) if p.strip()]
    remaining_text = re.sub(r'"[^"]+"', ' ', raw_text)
    # split by both spaces and newlines
    words = list(set(w.strip().lower() for w in remaining_text.replace("\n", " ").split() if w.strip()))
    words = list(set(words + phrases))

    bl_words = await get_words(chat_id)
    added, skipped = [], []

    # ✅ 50 limit check
    if len(bl_words) >= 50:
        return await m.reply_text("❌ You can't add more than 50 words in blocklist.")

    for word in words:
        if word in bl_words or word in added:
            skipped.append(word)
        else:
            await add_word(chat_id, word)
            added.append(word)

    if chat_id not in CHATS:
        CHATS.append(chat_id)

    title = update.effective_chat.title
    if chat_id != update.effective_chat.id:
        try:
            target_chat = await context.bot.get_chat(chat_id)
            title = target_chat.title
        except:
            title = str(chat_id)

    log_text = f"🚫 <b>Blocklist Word Added</b>\n" \
               f"<b>Group:</b> {html.escape(title)}\n" \
               f"<b>Words:</b> {', '.join(added)}\n" \
               f"<b>By:</b> {update.effective_user.mention_html()}"
    asyncio.create_task(log_action(context.bot, chat_id, "blocklists", log_text))

    mode = await get_mode(chat_id)
    mode = "on" if mode else "off"

    msg = ""
    if added:
        msg += f"✅ Added: `{', '.join(added)}`\n"
    if skipped:
        msg += f"⚠️ Skipped (duplicate/already exists): `{', '.join(skipped)}`\n"
    msg += f"📌 Blocklist is currently *{mode}*."

    return await m.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)


@Command("rmblword")
@disableable("rmblword")
@admin_check("can_delete_messages")
async def _removeBlockListWord(update, context):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    if len(m.text.split(maxsplit=1)) < 2:
        return await m.reply_text(
            "⚠️ Please specify words to remove from blocklist.\n\nExamples:\n"
            "`/rmblword porn child abuse`\n"
            "`/rmblword\nporn\nchild\nabuse`",
            parse_mode=constants.ParseMode.MARKDOWN
        )

    # ✅ Extract words (multi-line OR space separated)
    raw_text = m.text.split(maxsplit=1)[1]
    words = list(set(w.strip().lower() for w in raw_text.replace("\n", " ").split() if w.strip()))

    bl_words = await get_words(chat_id)
    removed, skipped = [], []

    for word in words:
        if word not in bl_words:
            skipped.append(word)
        else:
            await remove_word(chat_id, word)
            removed.append(word)

    if not await get_words(chat_id) and chat_id in CHATS:
        CHATS.remove(chat_id)

    title = update.effective_chat.title
    if chat_id != update.effective_chat.id:
        try:
            target_chat = await context.bot.get_chat(chat_id)
            title = target_chat.title
        except:
            title = str(chat_id)

    log_text = f"🗑️ <b>Blocklist Word Removed</b>\n" \
               f"<b>Group:</b> {html.escape(title)}\n" \
               f"<b>Words:</b> {', '.join(removed)}\n" \
               f"<b>By:</b> {update.effective_user.mention_html()}"
    asyncio.create_task(log_action(context.bot, chat_id, "blocklists", log_text))

    mode = await get_mode(chat_id)
    mode = "on" if mode else "off"

    msg = ""
    if removed:
        msg += f"✅ Removed: `{', '.join(removed)}`\n"
    if skipped:
        msg += f"⚠️ Not found in blocklist: `{', '.join(skipped)}`\n"
    msg += f"📌 Blocklist is currently *{mode}*."

    return await m.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)


@Command("blwords")
@disableable("blwords")
@admin_check("can_delete_messages")
async def _toggleBlocklist(update, context):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    mode = await get_mode(chat_id)
    current = "on" if mode else "off"

    if len(m.text.split()) < 2:
        return await m.reply_text(
            f"⚙️ Usage: `/blwords on` or `/blwords off`\nCurrent status: *{current}*",
            parse_mode=constants.ParseMode.MARKDOWN
        )

    q = m.text.split()[1].lower()
    if q not in ['on', 'off']:
        return await m.reply_text(font("❌ Only `on` or `off` allowed!"), parse_mode=constants.ParseMode.MARKDOWN)

    await update_mode(chat_id, q == 'on')
    if q == 'on' and chat_id not in CHATS:
        CHATS.append(chat_id)

    return await m.reply_text(
        "🛡️ *Blocklist enabled.*" if q == 'on' else "🚫 *Blocklist disabled.*",
        parse_mode=constants.ParseMode.MARKDOWN
    )


@Command("blwordslist")
@disableable("blwordslist")

@admin_check("can_delete_messages")
async def _showBlockWords(update, context):
    m = update.effective_message
    chat = m.chat
    chat_id = await get_effective_chat_id(update)

    words = await get_words(chat_id)
    if not words:
        return await m.reply_text(font("❌ No words currently blocked!"))

    if chat_id != chat.id:
        try:
            target_chat = await context.bot.get_chat(chat_id)
            title = target_chat.title
        except:
            title = str(chat_id)
    else:
        title = chat.title

    text = f"*{title}'s Blocked Words:*\n\n"
    text += "\n".join(f"• `{word}`" for word in words)

    if len(text) > 4000:
        return await chat.send_document(get_as_document(text), filename="blocked_words.txt")
    else:
        return await chat.send_message(text, parse_mode=constants.ParseMode.MARKDOWN)
