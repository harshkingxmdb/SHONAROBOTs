from AloneX.helpers.decorator import only_groups
from pyrogram import filters
from pyrogram.types import Message
from AloneX import pbot, DEV_LIST, font
from datetime import datetime, timedelta, timezone
from AloneX.db.antiraid import (
    enable_antiraid,
    disable_antiraid,
    set_raid_time,
    set_ban_time,
    set_auto_trigger,
    get_antiraid_config,
)
import re

__module__ = "𝐀ɴᴛɪ-𝐑ᴀɪᴅ🚨"

__help__ = """
*𝐀ɴᴛɪ-𝐑ᴀɪᴅ🚨*

*Description:*  
Prevent group raids where users join in bulk and spam. Admins can enable temporary protection or automate it during high join rates.

*Commands:*  
❂ `/antiraid <time|off>` - Enable/disable anti-raid  
❂ `/raidtime <time>` - Set duration for anti-raid active period (default: 6h)  
❂ `/raidactiontime <time>` - Set temporary ban time for new joins (default: 1h)  
❂ `/autoantiraid <number|off>` - Enable auto anti-raid when X joins per minute  

*Note:* Only admins with Ban permissions or developers can use these commands.
"""



def parse_time(text: str) -> int:
    match = re.match(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", text.strip().lower())
    if not match:
        return 0
    h = int(match[1]) if match[1] else 0
    m = int(match[2]) if match[2] else 0
    s = int(match[3]) if match[3] else 0
    return h * 3600 + m * 60 + s


def human_time(seconds: int) -> str:
    parts = []
    for name, count in [("h", 3600), ("m", 60), ("s", 1)]:
        val = seconds // count
        if val:
            seconds %= count
            parts.append(f"{val}{name}")
    return " ".join(parts) or "0s"


async def check_admin_rights(chat_id: [str, int], user_id: [int, str], permission: str) -> bool:
    if int(user_id) in DEV_LIST:
        return True
    try:
        member = await pbot.get_chat_member(chat_id, user_id)
        if member.privileges:
            return getattr(member.privileges, permission, False)
    except Exception:
        pass
    return False


@pbot.on_message(filters.command("antiraid"), group=-988)
@only_groups
async def antiraid_handler(_, m: Message):
    if not await check_admin_rights(m.chat.id, m.from_user.id, "ban_users"):
        return await m.reply(font("Only admins with ban rights or devs can use this."))

    chat_id = m.chat.id
    args = m.text.split(maxsplit=1)

    if len(args) == 1:
        config = await get_antiraid_config(chat_id)
        until = config.get("enabled_until")
        if until and until > datetime.now(timezone.utc):
            return await m.reply(font("🛡️ AntiRaid is currently active."))
        return await m.reply(font("❌ AntiRaid is not enabled."))

    arg = args[1].strip().lower()
    if arg in ("off", "no", "disable"):
        await disable_antiraid(chat_id)
        return await m.reply(font("✅ AntiRaid has been disabled."))

    duration = parse_time(arg)
    if not duration:
        return await m.reply(font("❌ Invalid time. Use format like `3h`, `30m`, etc."))

    until = datetime.now(timezone.utc) + timedelta(seconds=duration)
    await enable_antiraid(chat_id, until)
    return await m.reply(f"✅ AntiRaid enabled for {human_time(duration)}.")


@pbot.on_message(filters.command("raidtime"), group=-989)
@only_groups
async def raidtime_handler(_, m: Message):
    if not await check_admin_rights(m.chat.id, m.from_user.id, "ban_users"):
        return await m.reply(font("You need ban permission to set raid time."))

    args = m.text.split(maxsplit=1)
    chat_id = m.chat.id
    config = await get_antiraid_config(chat_id)

    if len(args) == 1:
        time_set = config.get("raid_time", 21600)
        return await m.reply(f"📌 Current AntiRaid duration: {human_time(time_set)}")

    duration = parse_time(args[1])
    if not duration:
        return await m.reply(font("❌ Invalid time format."))
    await set_raid_time(chat_id, duration)
    await m.reply(f"✅ AntiRaid duration set to {human_time(duration)}.")


@pbot.on_message(filters.command("raidactiontime"), group=-990)
@only_groups
async def raidactiontime_handler(_, m: Message):
    if not await check_admin_rights(m.chat.id, m.from_user.id, "ban_users"):
        return await m.reply(font("You need ban permission to set action time."))

    args = m.text.split(maxsplit=1)
    chat_id = m.chat.id
    config = await get_antiraid_config(chat_id)

    if len(args) == 1:
        ban_time = config.get("ban_time", 3600)
        return await m.reply(f"🔒 Current ban time for new joins: {human_time(ban_time)}")

    duration = parse_time(args[1])
    if not duration:
        return await m.reply(font("❌ Invalid time format."))
    await set_ban_time(chat_id, duration)
    await m.reply(f"✅ Join ban duration set to {human_time(duration)}.")


@pbot.on_message(filters.command("autoantiraid"), group=-991)
@only_groups
async def autoantiraid_handler(_, m: Message):
    if not await check_admin_rights(m.chat.id, m.from_user.id, "ban_users"):
        return await m.reply(font("You need ban permission to modify auto antiraid."))

    args = m.text.split(maxsplit=1)
    chat_id = m.chat.id
    config = await get_antiraid_config(chat_id)

    if len(args) == 1:
        val = config.get("auto_trigger", 0)
        if val == 0:
            return await m.reply(font("🚫 AutoAntiRaid is disabled."))
        return await m.reply(f"🚨 AutoAntiRaid will trigger if {val}+ users join in 1 minute.")

    arg = args[1].strip().lower()
    if arg in ("off", "no", "0"):
        await set_auto_trigger(chat_id, 0)
        return await m.reply(font("❌ AutoAntiRaid disabled."))
    if not arg.isdigit():
        return await m.reply(font("❌ Please provide a valid number."))

    threshold = int(arg)
    await set_auto_trigger(chat_id, threshold)
    await m.reply(f"✅ AutoAntiRaid will now trigger after {threshold} joins/min.")
