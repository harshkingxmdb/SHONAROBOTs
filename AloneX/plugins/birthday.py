from pyrogram import filters
from pyrogram.enums import ChatAction
from pyrogram.types import Message
from AloneX import pbot, DEV_LIST, font
from datetime import datetime
import re

from AloneX.db.birthday import (
    save_birthday,
    remove_birthday,
    get_birthdays,
)
__module__ = "𝐁ɪʀᴛʜᴅᴀʏ🎂"

__help__ = """
*𝐁ɪʀᴛʜᴅᴀʏ🎂*

*Description:*  
Manage birthdays and anonymous confessions in your chat.

*Commands:*  
❂ `/confess @user <msg>` – Send an anonymous confession  
❂ `/getconfesslog` – View your confessions (devs only)  
❂ `/getconfesslog_all` – View all confessions (devs only)  
❂ `/antichannel` – Delete forwarded messages from a channel  
❂ `/setbday` – Set your birthday
"""
    

@pbot.on_message(filters.command("setbday"))
async def set_birthday(_, message: Message):
    if not message.from_user or not message.from_user.id:
        return await message.reply_text(font("❌ You must use this from a real Telegram account (not anonymous)."))

    if len(message.command) < 2:
        return await message.reply_text(font("❌ Usage: `/setbday DD-MM`"), quote=True)

    date_input = message.command[1]
    if not re.match(r"^(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[0-2])$", date_input):
        return await message.reply_text(font("❌ Invalid date format.\n✅ Use: `/setbday 25-12`"), quote=True)

    await save_birthday(message.from_user.id, message.from_user.first_name, date_input)
    await message.reply_text(f"✅ Birthday saved for `{date_input}`!", quote=True)


# ❌ /removebday
@pbot.on_message(filters.command("removebday"))
async def remove_birthday_cmd(_, message: Message):
    if not message.from_user or not message.from_user.id:
        return await message.reply_text(font("❌ You must use this from a real Telegram account."))

    await remove_birthday(message.from_user.id)
    await message.reply_text(font("🗑️ Your birthday has been removed!"))


# 📅 /listbday
@pbot.on_message(filters.command("listbday"))
async def list_birthdays(_, message: Message):
    users = await get_birthdays()
    if not users:
        return await message.reply_text(font("📭 No birthdays saved yet!"))

    text = "🎂 **Saved Birthdays:**\n\n"
    for user in users:
        name = user.get("name", "Unknown")
        date = user.get("date", "??-??")
        text += f"👤 {name} ➤ `{date}`\n"

    await message.reply_text(text)


# 🔁 /runbdaycheck (DEV only)
@pbot.on_message(filters.command("runbdaycheck") & filters.user(DEV_LIST))
async def birthday_wisher_cmd(_, message: Message):
    today = datetime.now().strftime("%d-%m")
    count = 0

    users = await get_birthdays()
    for user in users:
        if user["date"] == today:
            try:
                await pbot.send_chat_action(user["id"], ChatAction.TYPING)
                await pbot.send_message(
                    user["id"],
                    f"🎉 Happy Birthday {user['name']}! 🥳\nWishing you a wonderful year ahead!"
                )
                count += 1
            except Exception as e:
                print(f"[Birthday] ❌ Couldn't DM {user['id']}: {e}")

    await message.reply_text(f"🎂 Birthday check done!\n🎉 {count} user(s) wished today.")
