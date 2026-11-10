import re
from datetime import datetime
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType, ButtonStyle

from AloneX import pbot as app, font
from AloneX import DEV_LIST, prefix_cmds
from AloneX.db.multifunction import (
    log_confession, get_confess_logs, get_confess_logs_all,
    set_antichannel_setting, get_antichannel_setting
)

# ------------------ DEV CHECK ------------------ #
def is_dev(user_id: int) -> bool:
    return user_id in DEV_LIST

# ------------------ /confess ------------------ #
@app.on_message(filters.command("confess", prefixes=prefix_cmds) & filters.private, group=55)
async def confess_command(_, m: Message):
    if len(m.command) < 3:
        return await m.reply(font("❗Usage: `/confess @username I like your work!`"))

    username = m.command[1].lstrip("@")
    text = " ".join(m.command[2:])
    try:
        user = await app.get_users(username)
        await app.send_message(user.id, f"📩 Anonymous confession:\n\n**{text}**")
        await log_confession(m.from_user.id, user.id, text)
        await m.reply(font("✅ Confession sent anonymously!"))
    except:
        await m.reply(font("❌ Failed to send. User not found or blocked the bot."))

# ------------------ /getconfesslog ------------------ #
@app.on_message(filters.command("getconfesslog", prefixes=prefix_cmds) & filters.private, group=56)
async def get_confession_logs(_, m: Message):
    if not is_dev(m.from_user.id):
        return await m.reply(font("❌ Only developers can use this command."))

    logs = await get_confess_logs(m.from_user.id)
    if not logs:
        return await m.reply(font("📭 No confession logs found."))

    text = "**🗒️ Your Confession Logs:**\n\n"
    for log in logs:
        timestamp = log["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        text += f"- `{log['message']}` (to ID: `{log['to_id']}`) at `{timestamp}`\n"

    await m.reply(text)

# ------------------ /getconfesslog_all ------------------ #
@app.on_message(filters.command("getconfesslog_all", prefixes=prefix_cmds) & filters.private, group=57)
async def get_all_confessions(_, m: Message):
    if not is_dev(m.from_user.id):
        return await m.reply(font("❌ Only developers can use this command."))

    logs = await get_confess_logs_all()
    if not logs:
        return await m.reply(font("📭 No confessions found in the database."))

    text = "**🗒️ All Confession Logs:**\n\n"
    for log in logs[:10]:
        timestamp = log["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        text += f"- `{log['message']}`\n  From: `{log['from_id']}` → To: `{log['to_id']}` at `{timestamp}`\n\n"

    await m.reply(text)

# ------------------ /antichannel ------------------ #
@app.on_message(filters.command("antichannel", prefixes=prefix_cmds) & filters.group, group=58)
async def toggle_antichannel(_, m: Message):
    member = await app.get_chat_member(m.chat.id, m.from_user.id)
    if not member or (not member.privileges and not is_dev(m.from_user.id)):
        return await m.reply(font("❌ Only group admins or devs can toggle this."))

    args = m.text.split()
    if len(args) == 1:
        enabled = await get_antichannel_setting(m.chat.id)
        btn = InlineKeyboardMarkup([[
            InlineKeyboardButton(font("✅ Enable"), callback_data="antichannel_on", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(font("❌ Disable"), callback_data="antichannel_off", style=ButtonStyle.DANGER)
        ]])
        return await m.reply(
            f"🔐 Anti-channel is currently **{'ENABLED' if enabled else 'DISABLED'}**.",
            reply_markup=btn
        )

    if args[1] not in ["on", "off"]:
        return await m.reply(font("❗Usage: `/antichannel` or `/antichannel on|off`"))

    state = args[1] == "on"
    await set_antichannel_setting(m.chat.id, state)
    await m.reply(f"✅ Anti-channel has been **{'ENABLED' if state else 'DISABLED'}** by `{m.from_user.first_name}`.")

@app.on_callback_query(filters.regex("antichannel_(on|off)"))
async def antichannel_toggle_callback(_, cb):
    chat_id = cb.message.chat.id
    user_id = cb.from_user.id
    member = await app.get_chat_member(chat_id, user_id)

    if not member or (not member.privileges and not is_dev(user_id)):
        return await cb.answer(font("Only admins or devs can toggle."), show_alert=True)

    state = cb.data.endswith("on")
    await set_antichannel_setting(chat_id, state)
    await cb.message.edit_text(
        f"✅ Anti-channel has been **{'ENABLED' if state else 'DISABLED'}** by `{cb.from_user.first_name}`."
    )
    await cb.answer(font("Toggled successfully!"))

# ------------------ Delete forwarded channel messages ------------------ #
@app.on_message(filters.group & filters.forwarded)
async def delete_forwarded_channels(_, m: Message):
    # Check if the message is forwarded from a channel
    if (m.forward_origin and 
        hasattr(m.forward_origin, 'chat') and 
        m.forward_origin.chat and
        m.forward_origin.chat.type == ChatType.CHANNEL):
        enabled = await get_antichannel_setting(m.chat.id)
        if enabled:
            try:
                await m.delete()
            except:
                pass

# ------------------ /mcommands ------------------ #
@app.on_message(filters.command("mcommands", prefixes=prefix_cmds), group=59)
async def list_commands(_, m: Message):
    text = "**🤖 Available Commands:**\n\n"
    text += "`/confess @user <msg>` - Send anonymous confession\n"
    text += "`/getconfesslog` - View your confessions (devs only)\n"
    text += "`/getconfesslog_all` - View all confessions (devs only)\n"
    text += "`/antichannel` - View/toggle anti-channel (admin/dev only)\n"
    await m.reply(text)
