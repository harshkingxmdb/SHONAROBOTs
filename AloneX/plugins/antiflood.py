import time
from collections import defaultdict, deque
from datetime import timedelta
from telegram import Update, ChatPermissions, User
from telegram.ext import ContextTypes, filters
from AloneX import app, DEV_LIST, font
from AloneX.helpers.decorator import Command, Messages, admin_check, disableable, only_groups, get_effective_chat_id
from AloneX.db.antiflood import get_flood_config, set_flood_limit, set_flood_timer, disable_flood_timer, set_flood_action
from AloneX.db.approval_db import is_user_approved
from AloneX.helpers.utils import async_cache

__module__ = "𝐀ɴᴛɪ-𝐅ʟᴏᴏᴅ🌊"
__help__ = """
*Anti-Flood🌊*
*Description:*  
Protect your group from message flooding with automatic actions and punishments.
*Commands:*  
❂ `/setflood <number|off>` - Set flood limit  
❂ `/setfloodtimer <count> <time>` - Timed flood control  
❂ `/floodmode <action> [duration]` - Set punishment  
❂ `/clearflood` - Clear flood settings  
❂ `/flood` - View current flood status  
*Actions:* ban, kick, mute, tban, tmute  
*Time Options:* 30s, 15m, 2h, 7d  
*Examples:*  
`/setflood 5`  
`/setfloodtimer 3 10s`  
`/floodmode tmute 1h`  
*Features:*  
• Auto message deletion  
• Command immunity  
• Approved user bypass  
• Admin immunity  
• 48h deletion limit respected
"""

msg_cache = defaultdict(lambda: defaultdict(deque))

@async_cache(max_size=1000, max_idle_time=300)
async def get_flood_config_cached(chat_id: int):
    return await get_flood_config(chat_id)

@async_cache(max_size=5000, max_idle_time=600)
async def is_approved_cached(chat_id: int, user_id: int):
    return await is_user_approved(chat_id, user_id)

@async_cache(max_size=5000, max_idle_time=300)
async def is_user_admin_cached(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

def parse_time(text: str) -> int:
    unit = text[-1]
    try:
        value = int(text[:-1])
        return {
            's': value,
            'm': value * 60,
            'h': value * 3600,
            'd': value * 86400,
        }.get(unit, 0)
    except Exception:
        return 0

@Command("setflood")
@disableable("setflood")
@admin_check("can_change_info", protect_target=False)
async def set_flood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    args = context.args
    if not args:
        return await update.effective_message.reply_text(font("Usage: /setflood <number|off>"))
    val = args[0].lower()
    if val in ["off", "no", "0"]:
        await set_flood_limit(chat_id, 0)
        get_flood_config_cached.clear_cache()
        return await update.message.reply_text(font("✅ Flood detection disabled."))
    if not val.isdigit():
        return await update.message.reply_text("❌ Invalid number or 'off'")
    await set_flood_limit(chat_id, int(val))
    get_flood_config_cached.clear_cache()
    await update.message.reply_text(f"✅ Flood trigger set to {val} messages.")

@Command("setfloodtimer")
@disableable("setfloodtimer")
@admin_check("can_change_info", protect_target=False)
async def set_flood_timer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    args = context.args
    if not args or len(args) < 2:
        if args and args[0].lower() in ["off", "no"]:
            await disable_flood_timer(chat_id)
            get_flood_config_cached.clear_cache()
            return await update.message.reply_text(font("✅ Timed flood disabled."))
        return await update.message.reply_text(font("Usage: /setfloodtimer <count> <duration>"))
    count, duration = args[0], args[1]
    if not count.isdigit():
        return await update.message.reply_text(font("❌ Invalid number for count."))
    seconds = parse_time(duration)
    if not seconds:
        return await update.message.reply_text(font("❌ Invalid duration. Use 10s, 5m, 2h, 1d etc."))
    await set_flood_timer(chat_id, int(count), seconds)
    get_flood_config_cached.clear_cache()
    await update.message.reply_text(f"✅ Timed flood set: {count} messages in {duration}")

@Command("floodmode")
@disableable("floodmode")
@admin_check("can_change_info", protect_target=False)
async def flood_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    args = context.args
    if not args:
        return await update.message.reply_text(font("Usage: /floodmode <ban/mute/kick/tban/tmute> [duration]"))
    mode = args[0].lower()
    time_value = args[1] if len(args) > 1 else None
    if mode not in ["ban", "mute", "kick", "tban", "tmute"]:
        return await update.message.reply_text(font("❌ Invalid mode. Choose from ban, mute, kick, tban, tmute"))
    await set_flood_action(chat_id, mode, time_value)
    get_flood_config_cached.clear_cache()
    await update.message.reply_text(f"✅ Flood action set to {mode}{' for ' + time_value if time_value else ''}")

@Command("clearflood")
@disableable("clearflood")
@admin_check("can_change_info", protect_target=False)
async def clear_flood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    await set_flood_limit(chat_id, 0)
    await disable_flood_timer(chat_id)
    await set_flood_action(chat_id, "mute", None)
    if chat_id in msg_cache:
        msg_cache[chat_id].clear()
    get_flood_config_cached.clear_cache()
    is_user_admin_cached.clear_cache()
    await update.message.reply_text(font("✅ Flood settings and cache cleared."))

@Command("flood")
@disableable("flood")
@admin_check("can_change_info", protect_target=False)
async def flood_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    config = await get_flood_config_cached(chat_id)
    limit = config.get("limit", 0)
    action = config.get("action", {})
    timer = config.get("timer", {})
    if limit == 0:
        return await update.message.reply_text(font("🚫 Flood detection is disabled."))
    text = f"📊 **Flood Settings:**\n\n"
    text += f"• **Limit:** {limit} messages\n"
    text += f"• **Action:** {action.get('type', 'mute')}"
    if action.get('duration'):
        text += f" for {action['duration']}"
    text += "\n"
    if timer.get('count') and timer.get('seconds'):
        text += f"• **Timer:** {timer['count']} messages in {timer['seconds']}s\n"
    active_users = len(msg_cache.get(chat_id, {}))
    text += f"• **Active users tracked:** {active_users}"
    await update.message.reply_text(text, parse_mode='Markdown')

@Messages(filters=~filters.COMMAND & ~filters.UpdateType.EDITED_MESSAGE, group=10)
async def flood_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = message.from_user
    chat = update.effective_chat
    
    if not message or not user:
        return
    
    if user.is_bot:
        return
    
    if user.id in DEV_LIST:
        return
    
    if await is_user_admin_cached(context, chat.id, user.id):
        return
    
    if await is_approved_cached(chat.id, user.id):
        return
    
    config = await get_flood_config_cached(chat.id)
    limit = config.get("limit", 0)
    if limit == 0:
        return
    
    now = time.time()
    uid = user.id
    msg_deque = msg_cache[chat.id][uid]
    msg_deque.append((now, message.message_id))
    
    while msg_deque and now - msg_deque[0][0] > 10:
        msg_deque.popleft()
    
    if len(msg_deque) > limit:
        deleted_count = await delete_flood_messages(context, chat.id, msg_deque)
        msg_deque.clear()
        return await apply_flood_action(update, context, user, config, deleted_count)
    
    timer_cfg = config.get("timer", {})
    t_count = timer_cfg.get("count")
    t_seconds = timer_cfg.get("seconds")
    if t_count and t_seconds:
        recent = [(ts, msg_id) for ts, msg_id in msg_deque if now - ts < t_seconds]
        if len(recent) > t_count:
            deleted_count = await delete_flood_messages(context, chat.id, recent)
            msg_deque.clear()
            return await apply_flood_action(update, context, user, config, deleted_count)

async def delete_flood_messages(context, chat_id, message_list):
    message_ids = [msg_id for _, msg_id in message_list]
    deleted_count = 0
    for msg_id in message_ids:
        try:
            await context.bot.delete_message(chat_id, msg_id)
            deleted_count += 1
        except Exception:
            continue
    return deleted_count

async def apply_flood_action(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, config, deleted_count=0):
    chat = update.effective_chat
    
    if await is_user_admin_cached(context, chat.id, user.id):
        return
    
    action = config.get("action", {"type": "mute", "duration": None})
    action_type = action["type"]
    duration = parse_time(action.get("duration")) if action.get("duration") else None
    
    try:
        if action_type == "ban":
            await context.bot.ban_chat_member(chat.id, user.id)
        elif action_type == "kick":
            await context.bot.ban_chat_member(chat.id, user.id)
            await context.bot.unban_chat_member(chat.id, user.id)
        elif action_type == "mute":
            await context.bot.restrict_chat_member(chat.id, user.id, permissions=ChatPermissions())
        elif action_type == "tmute" and duration:
            until = update.effective_message.date + timedelta(seconds=duration)
            await context.bot.restrict_chat_member(chat.id, user.id, permissions=ChatPermissions(), until_date=until)
        elif action_type == "tban" and duration:
            until = update.effective_message.date + timedelta(seconds=duration)
            await context.bot.ban_chat_member(chat.id, user.id, until_date=until)
        else:
            return
        
        del_text = f"\n📝 **Messages deleted:** {deleted_count}" if deleted_count > 0 else "\n⚠️ Some messages couldn't be deleted (too old)"
        notification = await update.message.reply_text(
            f"🚫 User [{user.first_name}](tg://user?id={user.id}) was {action_type}{'ped' if action_type in ['ban', 'mute'] else 'ed'} for flooding.\n"
            f"**Reason:** Exceeded flood limit\n"
            f"**Duration:** {action.get('duration', 'Permanent')}"
            f"{del_text}",
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
        try:
            context.job_queue.run_once(
                lambda context: context.bot.delete_message(chat.id, notification.message_id),
                30
            )
        except:
            pass
    except Exception as e:
        await update.message.reply_text(f"⚠️ Failed to apply flood action: {e}")
