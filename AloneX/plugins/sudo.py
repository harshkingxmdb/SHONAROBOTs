from AloneX import font
import html
from telegram import constants
from telegram.helpers import mention_html
import config
from AloneX.helpers.decorator import Command, sudos_only, owner_only
from AloneX.db.sudo import add_sudo_user, remove_sudo_user, get_all_sudo_users, add_whitelist_user, remove_whitelist_user, get_all_whitelist_users, add_support_user, remove_support_user, get_all_support_users

_user_cache = {}

async def get_user_info(context, uid):
    if uid in _user_cache:
        return _user_cache[uid]
    try:
        user = await context.bot.get_chat(uid)
        name = mention_html(user.id, html.escape(user.full_name))
        result = f"{name} [{uid}]"
    except:
        result = f"<code>{uid}</code>"
    _user_cache[uid] = result
    return result

@Command("sudolist")
@sudos_only
async def sudolist(update, context):
    msg = update.effective_message
    parts = ["💥 <b>Current Superusers :</b>\n\n"]
    owner_ids = []
    if hasattr(config, 'OWNER_ID') and config.OWNER_ID:
        owner_ids = config.OWNER_ID if isinstance(config.OWNER_ID, list) else [config.OWNER_ID]
    dev_ids = []
    if hasattr(config, 'DEV_LIST') and config.DEV_LIST:
        dev_ids = list(set(config.DEV_LIST))
    sudos = await get_all_sudo_users()
    supports = await get_all_support_users()
    wls = await get_all_whitelist_users()
    if owner_ids:
        parts.append(" 🔱 <b>Owner:</b>\n\n")
        for owner in owner_ids:
            parts.append(f"• {await get_user_info(context, owner)}\n")
        parts.append("\n")
    if dev_ids:
        parts.append(" 👨‍💻 <b>Developers:</b>\n\n")
        for dev in dev_ids:
            parts.append(f"• {await get_user_info(context, dev)}\n")
        parts.append("\n")
    if sudos:
        parts.append(" 🔰 <b>Sudoers:</b>\n\n")
        for sudo in sudos:
            parts.append(f"• {await get_user_info(context, sudo)}\n")
        parts.append("\n")
    if supports:
        parts.append(" 🛡 <b>Support:</b>\n\n")
        for sup in supports:
            parts.append(f"• {await get_user_info(context, sup)}\n")
        parts.append("\n")
    if wls:
        parts.append(" ✅ <b>Whitelisted:</b>\n\n")
        for wl in wls:
            parts.append(f"• {await get_user_info(context, wl)}\n")
    text = "".join(parts)
    await msg.reply_text(text, parse_mode=constants.ParseMode.HTML)

@Command("wl")
@owner_only
async def manage_whitelist(update, context):
    await _manage_list(update, context, "Whitelist")

@Command("sudo")
@owner_only
async def manage_sudo(update, context):
    await _manage_list(update, context, "Sudo")

@Command("support")
@owner_only
async def manage_support(update, context):
    await _manage_list(update, context, "Support")

@Command("whitelist")
@sudos_only
async def whitelist_list(update, context):
    users = await get_all_whitelist_users()
    if not users:
        return await update.message.reply_text(font("⚡ No whitelisted users found."), parse_mode=constants.ParseMode.HTML)
    parts = ["📝 <b>AloneX's Whitelisted Users</b>:\n\n"]
    for user_id in users:
        parts.append(f"• {await get_user_info(context, user_id)}\n")
    await update.message.reply_text("".join(parts), parse_mode=constants.ParseMode.HTML)

@Command("supportlist")
@sudos_only
async def support_list(update, context):
    users = await get_all_support_users()
    if not users:
        return await update.message.reply_text(font("⚡ No support users found."), parse_mode=constants.ParseMode.HTML)
    parts = ["🙋 <b>AloneX's Support Users</b>:\n\n"]
    for user_id in users:
        parts.append(f"• {await get_user_info(context, user_id)}\n")
    await update.message.reply_text("".join(parts), parse_mode=constants.ParseMode.HTML)

async def _manage_list(update, context, list_type: str):
    msg = update.effective_message
    args = msg.text.split()
    if len(args) != 3:
        return await msg.reply_text(f"❌ Usage: `/{list_type.lower()} <user_id> <-add/-rm>`", parse_mode=constants.ParseMode.MARKDOWN)
    _, user_id, action = args
    if not user_id.isdigit() or action.lower() not in ["-add", "-rm"]:
        return await msg.reply_text(f"❌ Invalid input!\nUsage: `/{list_type.lower()} <user_id> <-add/-rm>`", parse_mode=constants.ParseMode.MARKDOWN)
    user_id = int(user_id)
    db_add, db_remove = None, None
    if list_type == "Sudo":
        db_add, db_remove = add_sudo_user, remove_sudo_user
    elif list_type == "Whitelist":
        db_add, db_remove = add_whitelist_user, remove_whitelist_user
    elif list_type == "Support":
        db_add, db_remove = add_support_user, remove_support_user
    if action == "-add":
        success = await db_add(user_id)
        _user_cache.pop(user_id, None)
        if success:
            try:
                user = await context.bot.get_chat(user_id)
                name = html.escape(user.full_name)
                text = f"✅ <b>{name}</b> (<code>{user_id}</code>) added to {list_type}."
            except:
                text = f"✅ <code>{user_id}</code> added to {list_type}."
        else:
            text = f"🧐 <code>{user_id}</code> is already in {list_type} or is a config user."
    elif action == "-rm":
        success = await db_remove(user_id)
        _user_cache.pop(user_id, None)
        if success:
            try:
                user = await context.bot.get_chat(user_id)
                name = html.escape(user.full_name)
                text = f"❌ <b>{name}</b> (<code>{user_id}</code>) removed from {list_type}."
            except:
                text = f"❌ <code>{user_id}</code> removed from {list_type}."
        else:
            text = f"🧐 <code>{user_id}</code> is not in {list_type} or is a protected config user."
    await msg.reply_text(text, parse_mode=constants.ParseMode.HTML)
