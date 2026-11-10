from AloneX import font

import aiohttp
import random
import html

from AloneX.helpers.decorator import Messages, Command, admin_check

from AloneX.db.riddle import CHAT_IDS, update_chat_riddle, update_chat_riddle_count, get_chat_riddle_count

from telegram import constants, Update
from telegram.ext import CallbackContext, filters


__module__ = "𝐑ɪᴅᴅʟᴇ🧠"

__help__ = """
*Commands*:
/riddle

*Description:*  
🧠 Solve GK questions and riddles with your friends competitively in your group chat!

*Usage:*  
❂ `/riddle on|off` — Enable or disable riddles in the chat  
❂ `/setriddle <N>` — Spawn a riddle every N messages (default 15, minimum 9)

*Examples:*  
`/riddle on`  
`/riddle off`  
`/setriddle 9`
"""



# Temporary storage for tracking messages
temp = {}
chat_riddle = {}
MAX_COUNT = 10


RIDDLE_TEXT = """
<b>🆎 Type:</b> <code>{type}</code>
<b>⚔️ Level:</b> <code>{level}</code>
<b>📝 Category:</b> <code>{category}</code>

<b>⁉️ Question:</b>
<code>{question}</code>

<b>🧠 Options:</b>
<code>{options}</code>
"""

CONGRATS_TEXT = """
<b>✨ Congratulations, {mention}! 🎉</b>
<b>⚡ You were the first to solve the riddle! 🧠💡</b>
"""

ERROR_TEXT = "<b>❌ API Error!</b> Unable to fetch riddle. Please try again later."

async def get_riddle(amount=1, category=9):
    """Fetches a riddle from OpenTDB API."""
    api_url = f"https://opentdb.com/api.php?amount={amount}&category={category}"

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            if response.status != 200:
                return None  # Indicating an API error
            data = await response.json()

            # Ensure valid riddle data exists
            if not data.get("results"):
                return None

            return data["results"][0]


@Messages(filters=filters.TEXT, group=8)
async def check_answers(update: Update, context: CallbackContext):
    """Checks if the user's answer is correct."""
    m = update.effective_message
    user = update.effective_user

    if m.chat.id in CHAT_IDS:
        riddle = chat_riddle.get(m.chat.id)
        if riddle and m.text.casefold() == riddle["correct_answer"].encode().decode().casefold():
            del chat_riddle[m.chat.id]
            mention = user.mention_html()
            await m.reply_text(
CONGRATS_TEXT.format(mention=mention), parse_mode=constants.ParseMode.HTML
            )



@Messages(filters=filters.ALL, group=10)
async def check_send_riddle(update: Update, context: CallbackContext):
    """Sends a new riddle after `MAX_COUNT` messages in a chat."""
    
    global chat_riddle
    m = update.effective_message

    if m.chat.id in CHAT_IDS:
        temp[m.chat.id] = temp.get(m.chat.id, 0) + 1

        chat_count = await get_chat_riddle_count(m.chat.id)

        if temp[m.chat.id] >= (chat_count if chat_count else MAX_COUNT):
            temp[m.chat.id] = 0  # Reset counter after sending riddle
            riddle_data = await get_riddle()

            if not riddle_data:
                return await m.reply_text(ERROR_TEXT, parse_mode=constants.ParseMode.HTML)

            # Format options
            options = riddle_data["incorrect_answers"] + [riddle_data["correct_answer"].encode().decode()]
            random.shuffle(options)
            options_str = ",\n".join(options)


            # Store new riddle
            chat_riddle[m.chat.id] = riddle_data

            await m.chat.send_message(
                RIDDLE_TEXT.format(
                    type=riddle_data["type"],
                    level=riddle_data["difficulty"],
                    category=riddle_data["category"],
                    question=riddle_data["question"].encode().decode(),
                    options=options_str,
                ),
                parse_mode=constants.ParseMode.HTML,
            )
            await m.chat.send_message(font("<b>👀 Waiting for an answer...</b>"), parse_mode=constants.ParseMode.HTML)




@Command("setriddle")
@admin_check()
async def set_chat_riddle_count(update: Update, context: CallbackContext):
    m = update.effective_message
    args = m.text.split()

    if len(args) != 2 or not args[1].isdigit() or int(args[1]) < 8:
        return await m.reply_text(font("Usage: /setriddle <count> (minimum: 8)"))

    success = await update_chat_riddle_count(m.chat.id, int(args[1]))
    msg = "✅ Successfully updated riddle count!" if success else "❌ Error! Try /riddle first or contact /support."
    
    await m.reply_text(f"<b>{msg}</b>", parse_mode=constants.ParseMode.HTML)      




@Command("riddle")
@admin_check()
async def set_chat_riddle(update: Update, context: CallbackContext):
    """Enables or disables the riddle game in a chat."""
    m = update.effective_message
    args = m.text.split()

    if len(args) != 2:
        return await m.reply_text(font("<b>❌ Incorrect usage!</b> Use <code>/riddle on|off</code>."), parse_mode=constants.ParseMode.HTML)

    toggle_options = {"on": True, "off": False}
    user_input = args[1].lower()

    if user_input not in toggle_options:
        return await m.reply_text(font("<b>👀 Incorrect usage!</b> Try <code>/riddle on</code> or <code>/riddle off</code>."), parse_mode=constants.ParseMode.HTML)

    is_enabled = toggle_options[user_input]
    await update_chat_riddle(m.chat.id, is_enabled)

    if not is_enabled:
       if m.chat.id in CHAT_IDS:
           CHAT_IDS.remove(m.chat.id)
    else:
       if not m.chat.id in CHAT_IDS:
           CHAT_IDS.append(m.chat.id)

    response_text = "<b>✅ Riddle Enabled!</b>" if is_enabled else "<b>✅ Riddle Disabled!</b>"
    await m.reply_text(response_text, parse_mode=constants.ParseMode.HTML)
