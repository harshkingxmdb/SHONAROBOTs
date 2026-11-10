from AloneX import font
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from AloneX.helpers.decorator import Command, admin_check, only_groups, disableable
from AloneX.helpers.utils import extract_user
from AloneX.db.mod import *
from AloneX.helpers.mod_helper import clear_mod_cache
import html

__module__ = "𝐌ᴏᴅᴇʀᴀᴛᴏʀs👮"
__help__ = """
*Moderators👮*
*Description:* Assign special moderator roles with limited permissions.
*Roles:*
• **Moderator** - Has all permissions
• **Warner** - Can warn users only
• **Muter** - Can mute/unmute users only
• **Cleaner** - Can delete messages only
*Commands:*
❂ `/mod <user>` - Add general moderator
❂ `/rmmod <user>` - Remove moderator
❂ `/warner <user>` - Add Warner role
❂ `/rmwarner <user>` - Remove Warner
❂ `/muter <user>` - Add Muter role
❂ `/rmmuter <user>` - Remove Muter
❂ `/cleaner <user>` - Add Cleaner role
❂ `/rmcleaner <user>` - Remove Cleaner
❂ `/modlist` - List all moderators
*Note:* Admins can also be assigned mod roles for additional control.
"""

async def get_user_mention_html(bot, chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        fn = member.user.first_name
        return f"<a href='tg://user?id={user_id}'>{html.escape(fn)}</a>"
    except:
        return f"<code>{user_id}</code>"

@Command("mod")
@admin_check("can_restrict_members")
@only_groups
@disableable("mod")
async def add_mod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text(font("Please reply to a user or mention them to add as moderator."))
    existing_roles = await get_user_all_roles(m.chat.id, user_id)
    if "mod" in existing_roles:
        mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
        return await m.reply_html(f"⚠️ {mention} is already a <b>Moderator</b>!")
    await remove_all_user_mods(m.chat.id, user_id)
    result = await add_mod_role(m.chat.id, user_id, "mod")
    if result:
        clear_mod_cache(m.chat.id, user_id)
        mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
        await m.reply_html(f"✅ {mention} added as <b>Moderator</b>\nCan: Warn, Mute, Ban, Delete messages")

@Command("rmmod")
@admin_check("can_restrict_members")
@only_groups
@disableable("rmmod")
async def rm_mod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text(font("Please reply to a user or mention them."))
    result = await remove_mod_role(m.chat.id, user_id, "mod")
    clear_mod_cache(m.chat.id, user_id)
    mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
    if result:
        await m.reply_html(f"✅ {mention} removed from moderators")
    else:
        await m.reply_html(f"❌ {mention} is not a moderator")

@Command("warner")
@admin_check("can_restrict_members")
@only_groups
@disableable("warner")
async def add_warner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text(font("Please reply to a user or mention them."))
    existing_roles = await get_user_all_roles(m.chat.id, user_id)
    if "mod" in existing_roles:
        mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
        return await m.reply_html(f"⚠️ {mention} is already a <b>Moderator</b> (has all permissions)!")
    if "warner" in existing_roles:
        mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
        return await m.reply_html(f"⚠️ {mention} is already a <b>Warner</b>!")
    result = await add_mod_role(m.chat.id, user_id, "warner")
    if result:
        clear_mod_cache(m.chat.id, user_id)
        mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
        await m.reply_html(f"✅ {mention} added as <b>Warner</b>\nCan: Warn users only")

@Command("rmwarner")
@admin_check("can_restrict_members")
@only_groups
@disableable("rmwarner")
async def rm_warner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text(font("Please reply to a user or mention them."))
    result = await remove_mod_role(m.chat.id, user_id, "warner")
    clear_mod_cache(m.chat.id, user_id)
    mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
    if result:
        await m.reply_html(f"✅ {mention} removed from warners")
    else:
        await m.reply_html(f"❌ {mention} is not a warner")

@Command("muter")
@admin_check("can_restrict_members")
@only_groups
@disableable("muter")
async def add_muter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text(font("Please reply to a user or mention them."))
    existing_roles = await get_user_all_roles(m.chat.id, user_id)
    if "mod" in existing_roles:
        mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
        return await m.reply_html(f"⚠️ {mention} is already a <b>Moderator</b> (has all permissions)!")
    if "muter" in existing_roles:
        mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
        return await m.reply_html(f"⚠️ {mention} is already a <b>Muter</b>!")
    result = await add_mod_role(m.chat.id, user_id, "muter")
    if result:
        clear_mod_cache(m.chat.id, user_id)
        mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
        await m.reply_html(f"✅ {mention} added as <b>Muter</b>\nCan: Mute/Unmute users only")

@Command("rmmuter")
@admin_check("can_restrict_members")
@only_groups
@disableable("rmmuter")
async def rm_muter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text(font("Please reply to a user or mention them."))
    result = await remove_mod_role(m.chat.id, user_id, "muter")
    clear_mod_cache(m.chat.id, user_id)
    mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
    if result:
        await m.reply_html(f"✅ {mention} removed from muters")
    else:
        await m.reply_html(f"❌ {mention} is not a muter")

@Command("cleaner")
@admin_check("can_delete_messages")
@only_groups
@disableable("cleaner")
async def add_cleaner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text(font("Please reply to a user or mention them."))
    existing_roles = await get_user_all_roles(m.chat.id, user_id)
    if "mod" in existing_roles:
        mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
        return await m.reply_html(f"⚠️ {mention} is already a <b>Moderator</b> (has all permissions)!")
    if "cleaner" in existing_roles:
        mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
        return await m.reply_html(f"⚠️ {mention} is already a <b>Cleaner</b>!")
    result = await add_mod_role(m.chat.id, user_id, "cleaner")
    if result:
        clear_mod_cache(m.chat.id, user_id)
        mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
        await m.reply_html(f"✅ {mention} added as <b>Cleaner</b>\nCan: Delete messages only")

@Command("rmcleaner")
@admin_check("can_delete_messages")
@only_groups
@disableable("rmcleaner")
async def rm_cleaner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text(font("Please reply to a user or mention them."))
    result = await remove_mod_role(m.chat.id, user_id, "cleaner")
    clear_mod_cache(m.chat.id, user_id)
    mention = await get_user_mention_html(context.bot, m.chat.id, user_id)
    if result:
        await m.reply_html(f"✅ {mention} removed from cleaners")
    else:
        await m.reply_html(f"❌ {mention} is not a cleaner")

@Command("modlist")
@only_groups
@disableable("modlist")
async def mod_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    mods_data = await get_all_mods(m.chat.id)
    if not mods_data:
        return await m.reply_text(font("❌ No moderators assigned in this chat."))
    text = "<b>👮 Moderators List:</b>\n\n"
    role_names = {"mod": "🛡️ Moderator","warner": "⚠️ Warner","muter": "🔇 Muter","cleaner": "🧹 Cleaner"}
    grouped = {}
    for mod in mods_data:
        role = mod["role"]
        if role not in grouped:
            grouped[role] = []
        grouped[role].append(mod["user_id"])
    for role in ["mod", "warner", "muter", "cleaner"]:
        if role in grouped:
            text += f"<b>{role_names.get(role, role)}</b>:\n"
            for uid in grouped[role]:
                mention = await get_user_mention_html(context.bot, m.chat.id, uid)
                text += f"  • {mention}\n"
            text += "\n"
    await m.reply_html(text)
