import csv
import json
import io
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, constants
from telegram.ext import ContextTypes
from AloneX import app, BOT_ID, BOT_USERNAME, SUDO_USERS, OWNER_ID, font
from AloneX.helpers.decorator import Command, admin_check, only_groups, Callbacks
from AloneX.helpers.log_helper import log_action
from AloneX.helpers.utils import extract_user
from AloneX.db.federation_db import (
    create_fed, delete_fed, get_fed_info, get_fed_by_owner,
    rename_fed, transfer_fed, add_fed_admin, remove_fed_admin,
    fban_user, unfban_user, is_user_fban, subscribe_fed,
    unsubscribe_fed, set_fed_log, unset_fed_log, set_fed_reason,
    set_fed_notif, join_fed, leave_fed, get_chat_fed,
    set_quiet_fed, is_quiet_fed, get_user_feds
)

__module__ = "𝐅ᴇᴅᴇʀᴀᴛɪᴏɴ⚖️"
__help__ = """
*Federation⚖️*

*Owner Commands:*
❂ `/newfed <name>` – Create a new federation
❂ `/renamefed <name>` – Rename your federation
❂ `/delfed` – Delete your federation
❂ `/fedtransfer <user>` – Transfer your federation
❂ `/fedpromote <user>` – Promote a user to fed admin
❂ `/feddemote <user>` – Demote a fed admin
❂ `/fednotif <on/off>` – Toggle PM notifications
❂ `/fedreason <on/off>` – Toggle mandatory reasons for bans
❂ `/subfed <ID>` – Subscribe to another federation
❂ `/unsubfed <ID>` – Unsubscribe from a federation
❂ `/fedexport` – Export ban list (CSV)
❂ `/setfedlog` – Set current chat as fed log
❂ `/unsetfedlog` – Unset fed log

*Admin Commands:*
❂ `/fban <user> [reason]` – Ban a user from the federation
❂ `/unfban <user>` – Unban a user
❂ `/feddemoteme <ID>` – Demote yourself from a federation
❂ `/myfeds` – List federations you manage

*User Commands:*
❂ `/fedinfo <ID>` – Info about a federation
❂ `/fedadmins <ID>` – List admins in a federation
❂ `/fedsubs <ID>` – List subscribed federations
❂ `/joinfed <ID>` – Join chat to a federation
❂ `/leavefed` – Leave the current federation
❂ `/fedstat [user]` – Check federation ban status
❂ `/chatfed` – Info about the chat's federation
❂ `/quietfed <on/off>` – Toggle join notifications
"""

async def is_user_fed_owner(fed_id, user_id):
    if user_id == OWNER_ID or user_id in SUDO_USERS: return True
    fed = await get_fed_info(fed_id)
    return fed and fed['owner_id'] == user_id

async def is_user_fed_admin(fed_id, user_id):
    if user_id == OWNER_ID or user_id in SUDO_USERS: return True
    fed = await get_fed_info(fed_id)
    if not fed: return False
    return fed['owner_id'] == user_id or user_id in fed.get('admins', [])

# --- Owner Commands ---

@Command("newfed")
async def newfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    u = update.effective_user
    if m.chat.type != constants.ChatType.PRIVATE:
        return await m.reply_text(font("❌ This command only works in PM."))

    if not context.args:
        return await m.reply_text(font("🙋‍♂️ Please provide a name for your federation."))

    existing = await get_fed_by_owner(u.id)
    if existing:
        return await m.reply_text(f"❌ You already own a federation: `{existing['fed_name']}` (ID: `{existing['fed_id']}`)")

    fed_name = " ".join(context.args)
    fed_id = await create_fed(u.id, fed_name)
    await m.reply_text(f"✅ **Federation Created!**\n**Name:** `{fed_name}`\n**ID:** `{fed_id}`\n\nUse `/joinfed {fed_id}` in your groups to link them.")

@Command("renamefed")
async def renamefed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    fed = await get_fed_by_owner(u.id)
    if not fed:
        return await update.effective_message.reply_text("❌ You don't own a federation.")

    if not context.args:
        return await update.effective_message.reply_text(font("🙋‍♂️ Please provide a new name."))

    new_name = " ".join(context.args)
    await rename_fed(fed['fed_id'], new_name)
    await update.effective_message.reply_text(f"✅ Federation renamed to `{new_name}`.")

@Command("delfed")
async def delfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    fed = await get_fed_by_owner(u.id)
    if not fed:
        return await update.effective_message.reply_text("❌ You don't own a federation.")

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(font("Yes, Delete"), callback_data=f"fed_del:{fed['fed_id']}"),
        InlineKeyboardButton(font("Cancel"), callback_data="close_admin")
    ]])
    await update.effective_message.reply_text(f"⚠️ **Are you sure?**\nDeleting `{fed['fed_name']}` will unlink all chats. This cannot be undone.", reply_markup=kb)

@Command("fedpromote")
async def fedpromote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    u = update.effective_user
    fed = await get_fed_by_owner(u.id)
    if not fed:
        return await m.reply_text("❌ You don't own a federation.")

    user_id = await extract_user(m)
    if not user_id:
        return await m.reply_text(font("🙋‍♂️ Mention or reply to a user to promote."))

    if user_id == u.id:
        return await m.reply_text(font("❌ You are already the owner."))

    if user_id in fed.get('admins', []):
        return await m.reply_text(font("❌ This user is already a fed admin."))

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(font("Accept Promotion"), callback_data=f"fed_accept:{fed['fed_id']}:{user_id}")
    ]])
    await m.reply_text(f"❓ Promotion request sent to the user. They must click below to confirm.", reply_markup=kb)

@Command("feddemote")
async def feddemote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    u = update.effective_user
    fed = await get_fed_by_owner(u.id)
    if not fed:
        return await m.reply_text("❌ You don't own a federation.")

    user_id = await extract_user(m)
    if not user_id:
        return await m.reply_text(font("🙋‍♂️ Mention or reply to a user to demote."))

    if user_id not in fed.get('admins', []):
        return await m.reply_text(font("❌ This user is not a fed admin."))

    await remove_fed_admin(fed['fed_id'], user_id)
    await m.reply_text(font("✅ User demoted from federation."))

@Command("setfedlog")
@only_groups
@admin_check("can_change_info")
async def setfedlog_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    u = update.effective_user
    fed = await get_fed_by_owner(u.id)
    if not fed:
        return await m.reply_text("❌ You don't own a federation.")

    await set_fed_log(fed['fed_id'], m.chat.id)
    await m.reply_text(f"✅ **Fed Logs Set!**\nAll actions for `{fed['fed_name']}` will be logged here.")

@Command("unsetfedlog")
@only_groups
@admin_check("can_change_info")
async def unsetfedlog_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    u = update.effective_user
    fed = await get_fed_by_owner(u.id)
    if not fed:
        return await m.reply_text("❌ You don't own a federation.")

    await unset_fed_log(fed['fed_id'])
    await m.reply_text(font("✅ Federation log unset."))

@Command("fedtransfer")
async def fedtransfer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    u = update.effective_user
    fed = await get_fed_by_owner(u.id)
    if not fed:
        return await m.reply_text("❌ You don't own a federation.")

    user_id = await extract_user(m)
    if not user_id:
        return await m.reply_text(font("🙋‍♂️ Mention or reply to the new owner."))

    if user_id == u.id:
        return await m.reply_text(font("❌ You are already the owner."))

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(font("Transfer Fed"), callback_data=f"fed_transfer:{fed['fed_id']}:{user_id}")
    ]])
    await m.reply_text(f"❓ Are you sure you want to transfer `{fed['fed_name']}` to this user?", reply_markup=kb)

@Command("fednotif")
async def fednotif_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    fed = await get_fed_by_owner(u.id)
    if not fed: return await update.effective_message.reply_text(font("❌ Unauthorized."))

    if not context.args:
        return await update.effective_message.reply_text(font("Usage: `/fednotif <on/off>`"))

    state = context.args[0].lower() in ['on', 'yes']
    await set_fed_notif(fed['fed_id'], state)
    await update.effective_message.reply_text(f"✅ Federation notifications set to: `{state}`")

@Command("fedreason")
async def fedreason_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    fed = await get_fed_by_owner(u.id)
    if not fed: return await update.effective_message.reply_text(font("❌ Unauthorized."))

    if not context.args:
        return await update.effective_message.reply_text(font("Usage: `/fedreason <on/off>`"))

    state = context.args[0].lower() in ['on', 'yes']
    await set_fed_reason(fed['fed_id'], state)
    await update.effective_message.reply_text(f"✅ Mandatory ban reasons set to: `{state}`")

@Command("subfed")
async def subfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    fed = await get_fed_by_owner(u.id)
    if not fed: return await update.effective_message.reply_text(font("❌ Unauthorized."))

    if not context.args:
        return await update.effective_message.reply_text(font("🙋‍♂️ Provide a Fed ID to subscribe to."))

    sub_id = context.args[0]
    target_fed = await get_fed_info(sub_id)
    if not target_fed:
        return await update.effective_message.reply_text(font("❌ Federation not found."))

    await subscribe_fed(fed['fed_id'], sub_id)
    await update.effective_message.reply_text(f"✅ Subscribed to `{target_fed['fed_name']}`.")

@Command("unsubfed")
async def unsubfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    fed = await get_fed_by_owner(u.id)
    if not fed: return await update.effective_message.reply_text(font("❌ Unauthorized."))

    if not context.args:
        return await update.effective_message.reply_text(font("🙋‍♂️ Provide a Fed ID to unsubscribe from."))

    sub_id = context.args[0]
    await unsubscribe_fed(fed['fed_id'], sub_id)
    await update.effective_message.reply_text(f"✅ Unsubscribed from `{sub_id}`.")

@Command("fedexport")
async def fedexport_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    fed = await get_fed_by_owner(u.id)
    if not fed: return await update.effective_message.reply_text(font("❌ Unauthorized."))

    bans = fed.get('banned_users', {})
    if not bans:
        return await update.effective_message.reply_text(font("❌ No banned users to export."))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["User ID", "Reason", "Time"])
    for uid, data in bans.items():
        writer.writerow([uid, data.get('reason'), data.get('time')])

    output.seek(0)
    doc = io.BytesIO(output.read().encode('utf-8'))
    doc.name = f"{fed['fed_name']}_bans.csv"
    await update.effective_message.reply_document(doc, caption=f"Exported bans for {fed['fed_name']}")

@Command("fedimport")
async def fedimport_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    u = update.effective_user
    fed = await get_fed_by_owner(u.id)
    if not fed: return await m.reply_text(font("❌ Unauthorized."))

    if not m.reply_to_message or not m.reply_to_message.document:
        return await m.reply_text(font("❌ Reply to a CSV file to import bans."))

    doc = m.reply_to_message.document
    if not doc.file_name.endswith('.csv'):
        return await m.reply_text(font("❌ Only CSV files are supported."))

    file = await context.bot.get_file(doc.file_id)
    content = io.BytesIO()
    await file.download_to_memory(content)
    content.seek(0)

    imported = 0
    try:
        reader = csv.DictReader(content.read().decode('utf-8').splitlines())
        for row in reader:
            uid = row.get('User ID')
            reason = row.get('Reason', 'Imported ban')
            if uid and uid.isdigit():
                await fban_user(fed['fed_id'], int(uid), reason)
                imported += 1
    except Exception as e:
        return await m.reply_text(f"❌ Error during import: {e}")

    await m.reply_text(f"✅ Successfully imported `{imported}` bans to `{fed['fed_name']}`.")

@Command("setfedlang")
async def setfedlang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    fed = await get_fed_by_owner(u.id)
    if not fed: return await update.effective_message.reply_text(font("❌ Unauthorized."))

    if not context.args:
        return await update.effective_message.reply_text(font("🙋‍♂️ Provide a language code (e.g., `en`, `hi`)."))

    lang = context.args[0].lower()
    from AloneX.db.federation_db import set_fed_lang
    await set_fed_lang(fed['fed_id'], lang)
    await update.effective_message.reply_text(f"✅ Federation log language set to: `{lang}`")

@Command("quietfed")
@only_groups
@admin_check("can_change_info")
async def quietfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    if not context.args:
        return await m.reply_text(font("Usage: `/quietfed <on/off>`"))

    state = context.args[0].lower() in ['on', 'yes']
    await set_quiet_fed(m.chat.id, state)
    await m.reply_text(f"✅ Quiet mode set to: `{state}`")

# --- Admin Commands ---

@Command("fban")
async def fban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    u = update.effective_user

    fed_id = await get_chat_fed(m.chat.id) if m.chat.type != constants.ChatType.PRIVATE else None
    if not fed_id:
        # If in PM or no fed in chat, check if user owns a fed
        owned = await get_fed_by_owner(u.id)
        if owned: fed_id = owned['fed_id']

    if not fed_id:
        return await m.reply_text("❌ This chat is not in a federation, and you don't own one.")

    if not await is_user_fed_admin(fed_id, u.id):
        return await m.reply_text(font("❌ You are not an admin of this federation."))

    user_id = await extract_user(m)
    if not user_id:
        return await m.reply_text(font("🙋‍♂️ Mention/reply to a user to fban."))

    if user_id == u.id:
        return await m.reply_text(font("❌ You cannot fban yourself."))

    if await is_user_fed_admin(fed_id, user_id):
        return await m.reply_text(font("❌ You cannot fban another fed admin."))

    fed = await get_fed_info(fed_id)
    reason = "No reason provided."
    args = context.args
    if args:
        # Skip user mention if provided as first arg
        if args[0].isdigit() or args[0].startswith('@'):
            reason = " ".join(args[1:]) or reason
        else:
            reason = " ".join(args)

    if fed.get('reason_required') and reason == "No reason provided.":
        return await m.reply_text(font("❌ A reason is required for fedbans."))

    await fban_user(fed_id, user_id, reason)
    await m.reply_text(f"✅ **User Banned from Federation!**\n**Fed:** `{fed['fed_name']}`\n**ID:** `{user_id}`\n**Reason:** `{reason}`")

    # Log to group log channel
    if m.chat.type != constants.ChatType.PRIVATE:
        log_text = f"🚫 <b>Federation Ban</b>\n" \
                   f"<b>Fed:</b> {fed['fed_name']}\n" \
                   f"<b>User:</b> <code>{user_id}</code>\n" \
                   f"<b>By:</b> {u.mention_html()}\n" \
                   f"<b>Reason:</b> {reason}"
        asyncio.create_task(log_action(context.bot, m.chat.id, "bans", log_text))

    # Try to ban in current chat
    try:
        await m.chat.ban_member(user_id)
    except: pass

    # Log action
    if fed.get('log_channel'):
        try:
            await context.bot.send_message(fed['log_channel'], f"🚫 **Fed Ban**\n**User:** `{user_id}`\n**By:** {u.mention_html()}\n**Reason:** `{reason}`", parse_mode='HTML')
        except: pass

@Command("unfban")
async def unfban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    u = update.effective_user
    fed_id = await get_chat_fed(m.chat.id)
    if not fed_id:
        owned = await get_fed_by_owner(u.id)
        if owned: fed_id = owned['fed_id']

    if not fed_id or not await is_user_fed_admin(fed_id, u.id):
        return await m.reply_text(font("❌ Unauthorized."))

    user_id = await extract_user(m)
    if not user_id:
        return await m.reply_text(font("🙋‍♂️ Provide a user to unfban."))

    await unfban_user(fed_id, user_id)
    await m.reply_text(font("✅ User unfbanned from federation."))

    # Log to group log channel
    if m.chat.type != constants.ChatType.PRIVATE:
        log_text = f"🔓 <b>Federation Unban</b>\n" \
                   f"<b>Fed:</b> {fed_id}\n" \
                   f"<b>User:</b> <code>{user_id}</code>\n" \
                   f"<b>By:</b> {u.mention_html()}"
        asyncio.create_task(log_action(context.bot, m.chat.id, "bans", log_text))

    # Try to unban in current chat
    try:
        await m.chat.unban_member(user_id)
    except: pass

@Command("feddemoteme")
async def feddemoteme_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    u = update.effective_user
    if not context.args:
        return await m.reply_text(font("🙋‍♂️ Provide the Federation ID."))

    fed_id = context.args[0]
    fed = await get_fed_info(fed_id)
    if not fed: return await m.reply_text(font("❌ Invalid Fed ID."))

    if u.id not in fed.get('admins', []):
        return await m.reply_text(font("❌ You are not an admin of this federation."))

    await remove_fed_admin(fed_id, u.id)
    await m.reply_text(font("✅ You have been demoted from the federation."))

# --- User Commands ---

@Command("joinfed")
@only_groups
@admin_check("can_change_info")
async def joinfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    if not context.args:
        return await m.reply_text(font("🙋‍♂️ Provide a Federation ID."))

    fed_id = context.args[0]
    fed = await get_fed_info(fed_id)
    if not fed:
        return await m.reply_text(font("❌ Invalid Federation ID."))

    await join_fed(m.chat.id, fed_id)
    await m.reply_text(f"✅ Chat joined to federation: **{fed['fed_name']}**")

@Command("leavefed")
@only_groups
@admin_check("can_change_info")
async def leavefed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    fed_id = await get_chat_fed(m.chat.id)
    if not fed_id:
        return await m.reply_text(font("❌ This chat is not in a federation."))

    await leave_fed(m.chat.id)
    await m.reply_text(font("✅ Chat left the federation."))

@Command("chatfed")
@only_groups
async def chatfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    fed_id = await get_chat_fed(m.chat.id)
    if not fed_id:
        return await m.reply_text(font("❌ This chat is not in any federation."))

    fed = await get_fed_info(fed_id)
    await m.reply_text(f"⚖️ **Chat Federation Information:**\n**Name:** `{fed['fed_name']}`\n**ID:** `{fed_id}`")

@Command("fedstat")
async def fedstat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    user_id = await extract_user(m) or update.effective_user.id

    fed_id = None
    if context.args:
        for arg in context.args:
            if len(arg) > 10 and '-' not in arg: # Rough check for shortuuid
                fed_id = arg
                break

    if not fed_id:
        fed_id = await get_chat_fed(m.chat.id) if m.chat.type != constants.ChatType.PRIVATE else None

    if not fed_id:
        return await m.reply_text(font("❌ No federation specified or found for this chat."))

    is_banned, reason = await is_user_fban(fed_id, user_id)
    if is_banned:
        await m.reply_text(f"🚫 **User Banned!**\n**User ID:** `{user_id}`\n**Fed ID:** `{fed_id}`\n**Reason:** `{reason}`")
    else:
        await m.reply_text(f"✅ User is not banned in this federation.")

# --- Callbacks ---

@Callbacks(r"^fed_del:")
async def fed_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    fed_id = q.data.split(":")[1]
    if not await is_user_fed_owner(fed_id, q.from_user.id):
        return await q.answer(font("❌ Only the owner can do this."), show_alert=True)

    await delete_fed(fed_id)
    await q.edit_message_text(font("✅ Federation deleted."))

@Callbacks(r"^fed_accept:")
async def fed_accept_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    _, fed_id, user_id = q.data.split(":")
    user_id = int(user_id)

    if q.from_user.id != user_id:
        return await q.answer(font("❌ This button is not for you."), show_alert=True)

    await add_fed_admin(fed_id, user_id)
    await q.edit_message_text(font("✅ You are now a federation admin!"))

@Callbacks(r"^fed_transfer:")
async def fed_transfer_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    _, fed_id, user_id = q.data.split(":")
    user_id = int(user_id)

    if not await is_user_fed_owner(fed_id, q.from_user.id):
        return await q.answer(font("❌ Only the owner can do this."), show_alert=True)

    await transfer_fed(fed_id, user_id)
    await q.edit_message_text(f"✅ Federation transferred to `{user_id}`.")

# --- Extra Logic ---

@Command("fedinfo")
async def fedinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.effective_message.reply_text(font("🙋‍♂️ Provide a Fed ID."))

    fed = await get_fed_info(context.args[0])
    if not fed:
        return await update.effective_message.reply_text(font("❌ Federation not found."))

    bans = len(fed.get('banned_users', {}))
    await update.effective_message.reply_text(f"⚖️ **Fed Info:**\n**Name:** `{fed['fed_name']}`\n**ID:** `{fed['fed_id']}`\n**Owner:** `{fed['owner_id']}`\n**Bans:** `{bans}`")

@Command("fedadmins")
async def fedadmins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        fed_id = await get_chat_fed(update.effective_chat.id)
    else:
        fed_id = context.args[0]

    if not fed_id:
        return await update.effective_message.reply_text(font("❌ No Fed ID specified."))

    fed = await get_fed_info(fed_id)
    if not fed: return await update.effective_message.reply_text(font("❌ Fed not found."))

    admins = [str(fed['owner_id']) + " (Owner)"] + [str(a) for a in fed.get('admins', [])]
    await update.effective_message.reply_text(f"👥 **Admins of {fed['fed_name']}:**\n" + "\n".join(admins))

@Command("fedsubs")
async def fedsubs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        fed_id = await get_chat_fed(update.effective_chat.id)
    else:
        fed_id = context.args[0]

    if not fed_id:
        return await update.effective_message.reply_text(font("❌ No Fed ID specified."))

    fed = await get_fed_info(fed_id)
    if not fed: return await update.effective_message.reply_text(font("❌ Fed not found."))

    subs = fed.get('subs', [])
    if not subs:
        return await update.effective_message.reply_text(f"❌ `{fed['fed_name']}` is not subscribed to any federations.")

    await update.effective_message.reply_text(f"🔗 **Subscriptions for {fed['fed_name']}:**\n" + "\n".join(subs))

@Command("myfeds")
async def myfeds_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    feds = await get_user_feds(u.id)
    if not feds:
        return await update.effective_message.reply_text("❌ You don't have any federations.")

    res = "⚖️ **Your Federations:**\n"
    for f in feds:
        role = "Owner" if f['owner_id'] == u.id else "Admin"
        res += f"• `{f['fed_name']}` (ID: `{f['fed_id']}`) - *{role}*\n"
    await update.effective_message.reply_text(res)
