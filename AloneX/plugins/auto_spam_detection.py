import re
from pyrogram import filters, types, enums
from AloneX import pbot as Client, LOGGER as log

# List of spam-related regex patterns
CONTEXT = [
    r"crypto",
    r"cash",
    r"win",
    r"bonus",
    r"spins",
    r"sell",
    r"bet",
    r"usdt",
    r"regist",
    r"profit",
    r"invest",
    r"reward",
    r"score",
    r"money",
    r"\d+x",
    r"price",
    r"promot",
    r"premium",
    r"digital",
    r"asset",
    r"nude",
    r"porn",
    r"sex",
    r"airdrop",
    r"referral",
    r"earn",
    r"withdrawal",
    r"buy",
    r"fuck",
]

PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in CONTEXT]

async def check_spam(text: str):
    """
    Checks if the provided text matches spam patterns.
    Returns:
        A list of matched keywords if more than 2 patterns match; otherwise, False.
    """
    if not text:
        return False

    matched = [pattern.pattern for pattern in PATTERNS if pattern.search(text)]
    return matched if len(matched) > 2 else False

def censor_word(word: str) -> str:
    """
    Replaces every second character of a word with an asterisk (e.g., 'cash' -> 'c*s*').
    """
    return ''.join(c if i % 2 == 0 else '*' for i, c in enumerate(word))

@Client.on_message((filters.text | filters.caption) & filters.group, group=-4)
async def auto_detect_spammers(client: Client, message: types.Message):
    """
    Automatically deletes messages that are detected as spam and notifies the user.
    """
    # Check if the sender exists
    if not message.from_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    # Skip if the user is an admin
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return
    except Exception as e:
        log.warning(f"Couldn't get member status: {e}")
        return

    # Extract message text or caption
    text = message.text or message.caption or ""
    spammers = await check_spam(text)

    if spammers:
        try:
            await message.delete()
        except Exception as e:
            log.error(f"Error deleting message: {e}")
            return

        # Censor spam keywords
        censored_keywords = [censor_word(keyword) for keyword in spammers]
        keywords = ", ".join(censored_keywords)

        # Compose warning message WITHOUT admin mentions
        warning_text = (
            f"⚠️ <b>User {message.from_user.mention(style='html')}'s message has been deleted "
            f"due to spam detection.\n\nDetected keywords</b>: <code>{keywords}</code>\n\n"
            f"🤖 <i>Auto-spam detection is active</i>"
        )

        try:
            await message.reply_text(warning_text, parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            log.error(f"Error sending spam warning: {e}")
