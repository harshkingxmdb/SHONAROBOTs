# Bug report command for AloneX (Pyrogram)
# Reports go to LOGS_CHANNEL (falls back to SUPPORT_CHAT if LOGS_CHANNEL is not set).

import html
from datetime import datetime, timezone

from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from AloneX import pbot as app, OWNER_ID, SUPPORT_CHAT, LOGS_CHANNEL, prefix_cmds

__module__ = "𝐁ᴜɢs🐞"

__help__ = """
**Bug Report 🐞**

❂ `/bug <description>` – Report a bug to the developers (groups only).
"""


def extract_bug_content(msg: Message) -> str | None:
    parts = (msg.text or "").split(None, 1)
    return parts[1].strip() if len(parts) == 2 and parts[1].strip() else None


@app.on_message(filters.command("bug", prefixes=prefix_cmds))
async def report_bug(client, msg: Message):
    if msg.chat.type == enums.ChatType.PRIVATE:
        return await msg.reply_text("**This command works only in groups.**")

    bug_description = extract_bug_content(msg)
    if not bug_description:
        return await msg.reply_text("**No bug description given. Please describe the bug after the command.**")

    user = msg.from_user
    if not user:
        return
    user_id = user.id

    if user_id == OWNER_ID:
        return await msg.reply_text("**You are the owner of this bot. Please address the bug directly.**")

    chat_ref = (
        f"@{msg.chat.username}/<code>{msg.chat.id}</code>"
        if msg.chat.username
        else f"Private group/<code>{msg.chat.id}</code>"
    )
    current_date = datetime.now(timezone.utc).strftime("%d-%m-%Y")
    mention = f'<a href="tg://user?id={user_id}">{html.escape(user.first_name or "User")}</a>'

    bug_report = (
        "<b>#BUG REPORT</b>\n"
        f"<b>Reported by:</b> {mention}\n"
        f"<b>User ID:</b> <code>{user_id}</code>\n"
        f"<b>Chat:</b> {chat_ref}\n"
        f"<b>Bug description:</b> {html.escape(bug_description)}\n"
        f"<b>Date (UTC):</b> <code>{current_date}</code>"
    )

    await msg.reply_text(
        "**Bug reported successfully!**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="close")]]),
    )

    buttons = [[InlineKeyboardButton("Close", callback_data="close")]]
    if msg.chat.username:
        buttons.insert(0, [InlineKeyboardButton(
            "View bug", url=f"https://t.me/{msg.chat.username}/{msg.id}")])
    markup = InlineKeyboardMarkup(buttons)

    destinations = [d for d in (LOGS_CHANNEL, f"@{SUPPORT_CHAT}" if SUPPORT_CHAT else None) if d]
    for dest in destinations:
        try:
            await app.send_message(
                dest, bug_report, parse_mode=enums.ParseMode.HTML,
                reply_markup=markup, disable_web_page_preview=True,
            )
            return
        except Exception:
            continue                    # try the next destination
