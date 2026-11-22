# =======================================================
# ©️ 2025-26 All Rights Reserved by Purvi Bots (Im-Notcoder) 🚀
# Adapted for SHONAROBOTs (Python-Telegram-Bot + Buttons)
# =======================================================

import asyncio
import random
from telegram import Update, constants, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext

import AloneX
from AloneX import LOGGER
from AloneX.helpers.decorator import Command, send_action, spam_control
from AloneX.music import userbot as us
from AloneX.music.core.userbot import assistants
from pyrogram.raw.functions.messages import DeleteHistory

__module__ = "Sɢ🆕"

__help__ = """
*Sangmata History Module*

*Description:*
This module allows you-to check user history (Name/Username history) using Sangmata bots via your assistant userbot with interactive buttons.

*Commands:*
❂ `/sg [user_id / username]` or reply to a user to check their history.

*Examples:*
`/sg @username`
(Or reply to any user's message with `/sg`)
"""

# Standard Inline Keyboard for closing output
def get_sg_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close_ai_msg")]
    ])


@Command("sg")
@send_action(constants.ChatAction.TYPING)
@spam_control
async def sg_command(update: Update, context: CallbackContext) -> None:
    m = update.effective_message
    reply = m.reply_to_message
    args = m.text.split(maxsplit=1)

    if len(args) == 1 and not reply:
        return await m.reply_text(
            "**➤ ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴜsᴇʀ ɪᴅ/ᴜsᴇʀɴᴀᴍᴇ ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜsᴇʀ.**",
            parse_mode=constants.ParseMode.MARKDOWN
        )

    if reply:
        user_identifier = reply.from_user.id
    else:
        user_identifier = args[1]

    loading = await m.reply_text("**❖ ᴘʀᴏᴄᴇssɪɴɢ...**", parse_mode=constants.ParseMode.MARKDOWN)

    sangmata_bots = ["sangmata_bot", "sangmata_beta_bot"]
    target_bot = random.choice(sangmata_bots)

    if 1 in assistants:
        ubot = us.one
    else:
        return await loading.edit_text("**✘ ɴᴏ ᴀssɪsᴛᴀɴᴛ ᴜsᴇʀʙᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ.**", parse_mode=constants.ParseMode.MARKDOWN)

    try:
        sent = await ubot.send_message(target_bot, str(user_identifier))
        await sent.delete()
    except Exception as e:
        return await loading.edit_text(f"**✘ ᴇʀʀᴏʀ :-** {e}", parse_mode=constants.ParseMode.MARKDOWN)

    await asyncio.sleep(2)

    found = False
    async for msg in ubot.search_messages(target_bot):
        if not msg.text:
            continue
        keyboard = get_sg_keyboard()
        await m.reply_text(
            f"🧾 <b>ʜɪsᴛᴏʀʏ :-</b>\n\n{msg.text}",
            parse_mode=constants.ParseMode.HTML,
            reply_markup=keyboard
        )
        found = True
        break

    if not found:
        await m.reply_text("**✘ ɴᴏ ʀᴇsᴘᴏɴsᴇ ʀᴇᴄᴇɪᴠᴇᴅ ғʀᴏᴍ ᴛʜᴇ sᴀɴɢᴍᴀᴛᴀ ʙᴏᴛ.**", parse_mode=constants.ParseMode.MARKDOWN)

    try:
        peer = await ubot.resolve_peer(target_bot)
        await ubot.send(DeleteHistory(peer=peer, max_id=0, revoke=True))
    except Exception:
        pass

    await loading.delete()

# =======================================================
# ©️ 2025-26 All Rights Reserved by Purvi Bots (Im-Notcoder) 😎
# =======================================================
