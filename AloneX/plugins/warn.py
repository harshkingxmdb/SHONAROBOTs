from AloneX import DEV_LIST, font, prefix_cmds
from telegram import *
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes, filters as tg_filters
from AloneX.helpers.decorator import *
from AloneX.helpers.utils import extract_user
from AloneX.db.warn_db import *
from AloneX.db.approval_db import is_user_approved
from AloneX.helpers.log_helper import log_action
import shlex
import re
import asyncio
import html
from asyncio import gather

__module__ = "𝐖ᴀʀɴs⚠️"
__help__ = """
*Warns⚠️*

*Description:*  
A warning system to manage and moderate users in your chat.

*Commands:*  
❂ `/warn` – Issue a warning to a user  
❂ `/dwarn` – Warn and delete the message  
❂ `/warns` – View user warnings  
❂ `/unwarn` or `/resetwarn` – Remove last warning  

❂ `/addwarn <word> <response>` – Add a word to trigger a warning  
❂ `/nowarn <word>` – Remove a word from warnings  
❂ `/warnlist` – Show list of warning words  

❂ `/warnlimit <number>` – Set maximum warnings  
❂ `/strongwarn on|off` – Enable or disable strong warnings  
❂ `/setwarnaction ban|kick|mute` – Action on reaching warning limit  

❂ `/warnsall` – View all warned users  
❂ Inline buttons – Remove warning or clear all warnings
"""

user_cache = {}
admin_cache = {}
filter_cache = {}

def cache_user_info(chat_id, user_id, first_name):
    key = f"{chat_id}:{user_id}"
    user_cache[key] = first_name

def get_cached_user(chat_id, user_id):
    key = f"{chat_id}:{user_id}"
    return user_cache.get(key)

async def get_user_mention_fast(bot, chat_id, user_id):
    cached = get_cached_user(chat_id, user_id)
    if cached:
        return helpers.mention_html(user_id, cached)
    try:
        user_obj = await bot.get_chat_member(chat_id, user_id)
        cache_user_info(chat_id, user_id, user_obj.user.first_name)
        return helpers.mention_html(user_id, user_obj.user.first_name)
    except:
        return f"<code>{user_id}</code>"

async def get_chat_name(bot, chat_id):
    try:
        target_chat = await bot.get_chat(chat_id)
        if hasattr(target_chat, 'title') and target_chat.title:
            return helpers.escape(target_chat.title)
        elif hasattr(target_chat, 'username') and target_chat.username:
            return f"@{target_chat.username}"
        return str(chat_id)
    except:
        return str(chat_id)

async def is_admin_cached(chat, user_id):
    cache_key = f"{chat.id}:{user_id}"
    if cache_key in admin_cache:
        return admin_cache[cache_key]
    try:
        member = await chat.get_member(user_id)
        is_admin = member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
        admin_cache[cache_key] = is_admin
        return is_admin
    except:
        return False

async def get_filters_cached(chat_id):
    if chat_id in filter_cache:
        return filter_cache[chat_id]
    filters = await get_warn_filters(chat_id)
    filter_cache[chat_id] = filters
    return filters

def invalidate_filter_cache(chat_id):
    filter_cache.pop(chat_id, None)

async def apply_warn_punishment(chat, user_id, user_mention, limit):
    action = await get_warn_action(chat.id)
    await reset_warns(chat.id, user_id)

    if action == "ban":
        await chat.ban_member(user_id)
        return f"🚫 {user_mention} has been banned after reaching {limit} warnings."
    elif action == "kick":
        await gather(
            chat.ban_member(user_id),
            chat.unban_member(user_id)
        )
        return f"👋 {user_mention} has been removed after reaching {limit} warnings."
    elif action == "mute":
        await chat.restrict_member(user_id, ChatPermissions(can_send_messages=False))
        return f"🔇 {user_mention} has been muted after reaching {limit} warnings."
    return None

def get_warn_keyboard(user_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("- 𝟏", callback_data=f"warn_decrease_{user_id}"),
            InlineKeyboardButton("+ 𝟏", callback_data=f"warn_increase_{user_id}")
        ],
        [InlineKeyboardButton("❌ 𝐂ʟᴇᴀʀ 𝐀ʟʟ 𝐖ᴀʀɴɪɴɢs", callback_data=f"warn_delete_{user_id}")]
    ])

@Command(["warn", "dwarn"])
@disableable(["warn", "dwarn"])
@no_self_action
@mod_permission("warn")
async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)

    # Prefix-agnostic command detection
    is_dwarn = False
    full_text = m.text or m.caption
    if full_text:
        words = full_text.split()
        if words:
            first_word = words[0].lower()
            if any(first_word.startswith(p) for p in prefix_cmds):
                # find which prefix matched
                for p in prefix_cmds:
                    if first_word.startswith(p):
                        cmd_name = first_word[len(p):]
                        is_dwarn = cmd_name.startswith("dwarn")
                        break
    
    if m.reply_to_message and m.reply_to_message.sender_chat:
        sender_chat = m.reply_to_message.sender_chat
        reason = " ".join(context.args) if context.args else "No reason provided"
        
        try:
            readable_name = await get_chat_name(context.bot, sender_chat.id)
            await context.bot.ban_chat_sender_chat(chat_id=chat_id, sender_chat_id=sender_chat.id)
            if is_dwarn:
                try:
                    await m.reply_to_message.delete()
                except:
                    pass
            await m.reply_html(
                f"⚠️ Channel <b>{readable_name}</b> has been banned from this chat.\n"
                f"📝 <b>Reason:</b> {helpers.escape(reason)}"
            )
            return
        except Exception as e:
            return await m.reply_text(f"❌ Error: {str(e)}")
    
    user_id = await extract_user(m, self=False)
    if not user_id:
        msg = await m.reply_text(font("Please reply to a message, mention a user (@username), or provide user ID to issue a warning."))
        await asyncio.sleep(3)
        try:
            await msg.delete()
        except:
            pass
        return
    
    try:
        target_member = await m.chat.get_member(user_id)
        if target_member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return await m.reply_text(font("**❌ Cannot warn administrators!**"))
    except:
        pass
    
    if user_id in DEV_LIST:
        return await m.reply_text(font("**❌ Cannot warn bot developers!**"))
    
    reason = "No reason provided"
    if context.args:
        if m.reply_to_message:
            reason = " ".join(context.args)
        else:
            if len(context.args) > 1:
                reason = " ".join(context.args[1:])
    
    tasks = []
    if is_dwarn and m.reply_to_message:
        tasks.append(m.reply_to_message.delete())
    
    try:
        if tasks:
            await gather(*tasks, return_exceptions=True)
        
        await add_warn(chat_id, user_id, reason)
        warns, limit = await gather(
            get_warns(chat_id, user_id),
            get_warn_limit(chat_id)
        )
    except Exception as e:
        return await m.reply_text(f"❌ Database error: {str(e)}")
    
    if len(warns) >= limit:
        try:
            user_mention = await get_user_mention_fast(context.bot, chat_id, user_id)

            # Get target chat object for punishment
            target_chat_obj = await context.bot.get_chat(chat_id)
            punish_text = await apply_warn_punishment(target_chat_obj, user_id, user_mention, limit)
            if punish_text:
                return await m.reply_html(punish_text)
        except Exception as e:
            await m.reply_text(f"⚠️ Warning applied but unable to apply punishment: {str(e)}")
    
    user_mention = await get_user_mention_fast(context.bot, chat_id, user_id)
    escaped_reason = helpers.escape(reason)
    await m.reply_html(
        f"⚠️ {user_mention} has received a warning\n"
        f"📝 <b>Reason:</b> {escaped_reason}\n"
        f"📊 <b>Warnings:</b> {len(warns)}/{limit}",
        reply_markup=get_warn_keyboard(user_id)
    )

    title = update.effective_chat.title
    if chat_id != update.effective_chat.id:
        try:
            target_chat = await context.bot.get_chat(chat_id)
            title = target_chat.title
        except:
            title = str(chat_id)

    log_text = f"⚠️ <b>Warned</b>\n" \
               f"<b>Group:</b> {html.escape(title)}\n" \
               f"<b>User:</b> {user_mention} (<code>{user_id}</code>)\n" \
               f"<b>By:</b> {update.effective_user.mention_html()}\n" \
               f"<b>Reason:</b> {escaped_reason}\n" \
               f"<b>Warnings:</b> {len(warns)}/{limit}"
    asyncio.create_task(log_action(context.bot, chat_id, "warns", log_text))

@Command(["unwarn", "resetwarn"])
@disableable(["unwarn", "resetwarn"])
@no_self_action
@mod_permission("warn", protect_target=False)
async def unwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    if m.reply_to_message and m.reply_to_message.sender_chat:
        sender_chat = m.reply_to_message.sender_chat
        try:
            readable_name = await get_chat_name(context.bot, sender_chat.id)
            await context.bot.unban_chat_sender_chat(chat_id=chat_id, sender_chat_id=sender_chat.id)
            return await m.reply_html(f"✅ Channel <b>{readable_name}</b> has been unbanned.")
        except Exception as e:
            return await m.reply_text(f"❌ Error: {str(e)}")
    
    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text(font("Please reply to or mention a user to remove their warning."))
    
    try:
        await remove_last_warn(chat_id, user_id)
        await m.reply_text(font("✅ Latest warning has been removed successfully."))

        title = update.effective_chat.title
        if chat_id != update.effective_chat.id:
            try:
                target_chat = await context.bot.get_chat(chat_id)
                title = target_chat.title
            except:
                title = str(chat_id)

        user_mention = await get_user_mention_fast(context.bot, chat_id, user_id)
        log_text = f"💙 <b>Unwarned</b>\n" \
                   f"<b>Group:</b> {html.escape(title)}\n" \
                   f"<b>User:</b> {user_mention} (<code>{user_id}</code>)\n" \
                   f"<b>By:</b> {update.effective_user.mention_html()}"
        asyncio.create_task(log_action(context.bot, chat_id, "warns", log_text))
    except Exception as e:
        await m.reply_text(f"❌ Error removing warning: {str(e)}")
@Command("warns")
@no_self_action
@disableable("warns")
@admin_check("can_restrict_members", protect_target=False)
async def warns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await extract_user(update.effective_message, self=False)
    chat_id = await get_effective_chat_id(update)
    if not user_id:
        return await update.effective_message.reply_text(font("Please mention or reply to a user."))
    
    try:
        warns = await get_warns(chat_id, user_id)
        limit = await get_warn_limit(chat_id)
        
        if not warns:
            return await update.effective_message.reply_text(font("✅ This user has no warnings."))
        
        user_mention = await get_user_mention_fast(context.bot, chat_id, user_id)
        
        text = f"{user_mention} has {len(warns)}/{limit} warnings. Reasons are:\n\n"
        for idx, reason in enumerate(warns, 1):
            if reason and reason.strip():
                clean_reason = re.sub(r'<[^>]+>', '', reason).strip()
                if clean_reason and clean_reason.lower() not in ["no reason specified", "no reason given", "no reason provided"]:
                    text += f"{idx} - {helpers.escape(clean_reason)}\n"
                else:
                    text += f"{idx} - No reason given\n"
            else:
                text += f"{idx} - No reason given\n"
        
        await update.effective_message.reply_html(text.rstrip(), reply_markup=get_warn_keyboard(user_id))
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Error fetching warnings: {str(e)}")
@Command("addwarn")
@admin_check("can_restrict_members")
@disableable("addwarn")
async def addwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    chat_id = await get_effective_chat_id(update)
    if not context.args:
        return await m.reply_text(
            "**Usage:** `/addwarn <trigger> <warning_message>`\n\n"
            "**Examples:**\n"
            "• `/addwarn spam Don't spam here`\n"
            "• `/addwarn \"bad word\" This word is not allowed`\n"
            "• `/addwarn \"phone number\" Contact admin for phone issues`\n\n"
            "**Note:** Use quotes for multi-word triggers",
            parse_mode=constants.ParseMode.MARKDOWN
        )
    
    full_text = " ".join(context.args)
    try:
        parsed_args = shlex.split(full_text)
    except ValueError as e:
        return await m.reply_text(
            f"❌ Error parsing command: {e}\n\n"
            "Make sure to use proper quotes for multi-word triggers.\n"
            "Example: `/addwarn \"bad word\" This is not allowed`",
            parse_mode=constants.ParseMode.MARKDOWN
        )
    
    if len(parsed_args) < 2:
        return await m.reply_text(
            "❌ **Insufficient arguments!**\n\n"
            "**Usage:** `/addwarn <trigger> <warning_message>`\n\n"
            "**Examples:**\n"
            "• `/addwarn spam Don't spam here`\n"
            "• `/addwarn \"bad word\" This word is not allowed`\n"
            "• `/addwarn \"phone number\" Contact admin for phone issues`",
            parse_mode=constants.ParseMode.MARKDOWN
        )
    
    keyword = parsed_args[0].lower().strip()
    reply = " ".join(parsed_args[1:]).strip()
    
    if not keyword or not reply:
        return await m.reply_text(
            "❌ Both trigger and warning message must be provided!\n\n"
            "**Usage:** `/addwarn <trigger> <warning_message>`",
            parse_mode=constants.ParseMode.MARKDOWN
        )
    
    try:
        existing_filters = await get_filters_cached(chat_id)
        for filter_data in existing_filters:
            if filter_data['keyword'] == keyword:
                return await m.reply_text(
                    f"❌ Warning filter `{keyword}` already exists!\n"
                    f"Use `/nowarn {keyword}` to remove it first.",
                    parse_mode=constants.ParseMode.MARKDOWN
                )
        
        await add_warn_filter(chat_id, keyword, reply)
        invalidate_filter_cache(chat_id)
        await m.reply_text(
            f"✅ **Warning filter added successfully!**\n\n"
            f"**Trigger:** `{keyword}`\n"
            f"**Response:** {helpers.escape(reply)}\n\n"
            f"Now when someone uses `{keyword}`, they will receive a warning.",
            parse_mode=constants.ParseMode.MARKDOWN
        )
    except Exception as e:
        await m.reply_text(f"❌ Failed to add warning filter: {str(e)}")
@Command("nowarn")
@disableable("nowarn")
@admin_check("can_restrict_members", protect_target=False)
async def nowarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    if not context.args:
        return await update.effective_message.reply_text(font("**Usage:** `/nowarn <trigger>`"), parse_mode=constants.ParseMode.MARKDOWN)
    
    keyword = context.args[0].lower().strip()
    
    try:
        existing_filters = await get_filters_cached(chat_id)
        filter_exists = any(f['keyword'] == keyword for f in existing_filters)
        
        if not filter_exists:
            return await update.effective_message.reply_text(
                f"❌ Warning filter `{keyword}` does not exist.",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        
        await remove_warn_filter(chat_id, keyword)
        invalidate_filter_cache(chat_id)
        await update.effective_message.reply_text(
            f"✅ Warning filter `{keyword}` has been removed.",
            parse_mode=constants.ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Error removing filter: {str(e)}")

@Command("warnlist")
@disableable("warnlist")
async def warnlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    try:
        filters = await get_filters_cached(chat_id)
        if not filters:
            return await update.effective_message.reply_text(font("❌ No warning filters are currently set."))
        
        msg = "⚠️ **Active Warning Filters:**\n\n"
        for i, f in enumerate(filters, 1):
            msg += f"{i}. `{f['keyword']}` → {helpers.escape(f['reply'])}\n"
        
        if len(msg) < 4096:
            await update.effective_message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)
        else:
            import io
            output = io.BytesIO(msg.encode("utf-8"))
            output.name = f"warnlist_{update.effective_chat.id}.txt"
            await update.effective_message.reply_document(
                document=output,
                filename=output.name,
                caption="⚠️ Too many warn filters, here's the full list."
            )
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Error fetching warn filters: {str(e)}")

@Command("warnlimit")
@disableable("warnlimit")
@admin_check("can_restrict_members")
async def warn_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    try:
        if not context.args or not context.args[0].isdigit():
            current_limit = await get_warn_limit(chat_id)
            return await update.effective_message.reply_text(
                f"**Current warning limit:** {current_limit}\n\n"
                "**Usage:** `/warnlimit <number>`\n"
                "**Example:** `/warnlimit 3`",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        
        new_limit = int(context.args[0])
        if new_limit < 1 or new_limit > 20:
            return await update.effective_message.reply_text(font("❌ Warning limit must be between 1 and 20."))
        
        await set_warn_limit(chat_id, new_limit)
        await update.effective_message.reply_text(f"✅ Warning limit updated to {new_limit}.")
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Error setting warn limit: {str(e)}")

@Command("strongwarn")
@disableable("strongwarn")
@admin_check("can_delete_messages")
async def strongwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    try:
        if not context.args:
            current_state = await get_strong_warn(chat_id)
            return await update.effective_message.reply_text(
                f"**Strong warn mode:** {'Enabled' if current_state else 'Disabled'}\n\n"
                "**Usage:** `/strongwarn on|off`",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        
        state = context.args[0].lower() in ["on", "yes", "true", "enable"]
        await set_strong_warn(chat_id, state)
        await update.effective_message.reply_text(f"✅ Strong warning mode {'enabled' if state else 'disabled'}.")
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Error setting strong warn: {str(e)}")

@Command("setwarnaction")
@disableable("setwarnaction")
@admin_check("can_restrict_members")
async def setwarn_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    try:
        if not context.args:
            current_action = await get_warn_action(chat_id)
            return await update.effective_message.reply_text(
                f"**Current warn action:** {current_action}\n\n"
                "**Usage:** `/setwarnaction ban|kick|mute`",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        
        action = context.args[0].lower()
        if action not in ["ban", "kick", "mute"]:
            return await update.effective_message.reply_text(
                "❌ Invalid action! Use: `ban`, `kick`, or `mute`",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        
        await set_warn_action(chat_id, action)
        await update.effective_message.reply_text(f"✅ Warning action updated to **{action}**.", parse_mode=constants.ParseMode.MARKDOWN)
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Error setting warn action: {str(e)}")

@Command("warnsall")
@disableable("warnsall")
@admin_check("can_restrict_members")
async def warns_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = await get_effective_chat_id(update)
    try:
        users = await get_all_warned_users(chat_id)
        if not users:
            return await update.effective_message.reply_text(font("✅ No users currently have warnings."))
        
        text = "<b>Users with Warnings:</b>\n\n"
        for user in users:
            uid = user["user_id"]
            mention = await get_user_mention_fast(context.bot, chat_id, uid)
            text += f"• {mention} — <b>{len(user['reasons'])}</b> warning(s)\n"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton(font("🧹 Clear All Warnings"), callback_data=f"clearwarns#{chat_id}")]
        ])
        await update.effective_message.reply_html(text, reply_markup=buttons)
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Error fetching warned users: {str(e)}")

@Callbacks("^warn_decrease_")
@mod_permission("warn", protect_target=False)
async def warn_decrease_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = int(query.data.split("_")[-1])
    chat_id = await get_effective_chat_id(update)

    try:
        await remove_last_warn(chat_id, user_id)
        warns = await get_warns(chat_id, user_id)
        limit = await get_warn_limit(chat_id)
        user_mention = await get_user_mention_fast(context.bot, chat_id, user_id)

        if not warns:
            await gather(
                query.answer("✅ All warnings removed."),
                query.edit_message_text(f"✅ All warnings have been removed for {user_mention}.", parse_mode=constants.ParseMode.HTML)
            )
        else:
            await gather(
                query.answer("✅ Warning decreased."),
                query.edit_message_text(
                    f"⚠️ {user_mention} has received a warning\n"
                    f"📊 <b>Warnings:</b> {len(warns)}/{limit}",
                    reply_markup=get_warn_keyboard(user_id),
                    parse_mode=constants.ParseMode.HTML
                )
            )

        chat_obj = await context.bot.get_chat(chat_id)
        log_text = f"💙 <b>Warn Decreased</b>\n" \
                   f"<b>Group:</b> {html.escape(chat_obj.title)}\n" \
                   f"<b>User:</b> {user_mention} (<code>{user_id}</code>)\n" \
                   f"<b>By:</b> {query.from_user.mention_html()}"
        asyncio.create_task(log_action(context.bot, chat_id, "warns", log_text))
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Callbacks("^warn_increase_")
@mod_permission("warn", protect_target=False)
async def warn_increase_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = int(query.data.split("_")[-1])
    chat_id = await get_effective_chat_id(update)

    try:
        await add_warn(chat_id, user_id, "Warning increased by admin")
        warns = await get_warns(chat_id, user_id)
        limit = await get_warn_limit(chat_id)
        user_mention = await get_user_mention_fast(context.bot, chat_id, user_id)

        if len(warns) >= limit:
            chat_obj = await context.bot.get_chat(chat_id)
            punish_text = await apply_warn_punishment(chat_obj, user_id, user_mention, limit)
            if punish_text:
                await gather(
                    query.answer("🚫 Limit reached! Punishment applied."),
                    query.edit_message_text(punish_text, parse_mode=constants.ParseMode.HTML)
                )
            else:
                await query.answer("⚠️ Limit reached but no action taken.")
        else:
            await gather(
                query.answer("⚠️ Warning increased."),
                query.edit_message_text(
                    f"⚠️ {user_mention} has received a warning\n"
                    f"📊 <b>Warnings:</b> {len(warns)}/{limit}",
                    reply_markup=get_warn_keyboard(user_id),
                    parse_mode=constants.ParseMode.HTML
                )
            )

        chat_obj = await context.bot.get_chat(chat_id)
        log_text = f"⚠️ <b>Warn Increased</b>\n" \
                   f"<b>Group:</b> {html.escape(chat_obj.title)}\n" \
                   f"<b>User:</b> {user_mention} (<code>{user_id}</code>)\n" \
                   f"<b>By:</b> {query.from_user.mention_html()}\n" \
                   f"<b>Warnings:</b> {len(warns)}/{limit}"
        asyncio.create_task(log_action(context.bot, chat_id, "warns", log_text))
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Callbacks("^warn_delete_")
@mod_permission("warn", protect_target=False)
async def warn_delete_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = int(query.data.split("_")[-1])
    chat_id = await get_effective_chat_id(update)

    try:
        await reset_warns(chat_id, user_id)
        user_mention = await get_user_mention_fast(context.bot, chat_id, user_id)

        await gather(
            query.answer("🧹 Warnings cleared."),
            query.edit_message_text(f"🧹 All warnings have been cleared for {user_mention}.", parse_mode=constants.ParseMode.HTML)
        )

        chat_obj = await context.bot.get_chat(chat_id)
        log_text = f"🧹 <b>Warnings Cleared</b>\n" \
                   f"<b>Group:</b> {html.escape(chat_obj.title)}\n" \
                   f"<b>User:</b> {user_mention} (<code>{user_id}</code>)\n" \
                   f"<b>By:</b> {query.from_user.mention_html()}"
        asyncio.create_task(log_action(context.bot, chat_id, "warns", log_text))
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Callbacks("^unwarn#")
@mod_permission("warn", protect_target=False)
async def unwarn_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        _, chat_id, user_id = query.data.split("#")
        chat_id = int(chat_id)
        user_id = int(user_id)
        
        mention = await get_user_mention_fast(context.bot, chat_id, user_id)
        await remove_last_warn(chat_id, user_id)
        await gather(
            query.answer(font("✅ Warning removed successfully.")),
            query.edit_message_text(
                f"✅ Latest warning has been removed for {mention}.",
                parse_mode=constants.ParseMode.HTML
            )
        )
    except Exception as e:
        await query.answer(f"An error occurred: {str(e)}", show_alert=True)

@Callbacks("^clearwarns#")
@admin_check("can_restrict_members")
async def clearwarns_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        chat_id = int(query.data.split("#")[1])
        users = await get_all_warned_users(chat_id)
        tasks = [reset_warns(chat_id, user["user_id"]) for user in users]
        await gather(*tasks)
        await gather(
            query.answer(font("✅ All warnings cleared successfully.")),
            query.edit_message_text(font("🧹 All warnings have been cleared from this group."))
        )

        chat_obj = await context.bot.get_chat(chat_id)
        log_text = f"🧹 <b>All Warnings Cleared</b>\n" \
                   f"<b>Group:</b> {html.escape(chat_obj.title)}\n" \
                   f"<b>By:</b> {query.from_user.mention_html()}"
        asyncio.create_task(log_action(context.bot, chat_id, "warns", log_text))
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Messages(tg_filters.TEXT & tg_filters.ChatType.GROUPS, group=-2)
async def auto_warn_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    
    if msg.sender_chat:
        sender_chat = msg.sender_chat
        try:
            is_approved = await is_user_approved(msg.chat.id, sender_chat.id)
            if is_approved:
                return
        except:
            pass
        
        try:
            warn_filters = await get_filters_cached(msg.chat.id)
            if not warn_filters:
                return
        except:
            return
        
        if not msg.text or msg.text.startswith('/'):
            return
        
        message_text = msg.text.lower().strip()
        matched_filter = None
        
        for filter_data in warn_filters:
            keyword = filter_data['keyword'].lower().strip()
            if not keyword:
                continue
            
            if keyword == message_text:
                matched_filter = filter_data
                break
            
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, message_text, re.IGNORECASE):
                matched_filter = filter_data
                break
        
        if not matched_filter:
            return
        
        strong = await get_strong_warn(msg.chat.id)
        if strong:
            try:
                await msg.delete()
            except:
                pass
        
        try:
            readable_name = await get_chat_name(context.bot, sender_chat.id)
            await context.bot.ban_chat_sender_chat(chat_id=msg.chat.id, sender_chat_id=sender_chat.id)
            await msg.reply_html(
                f"⚠️ Channel <b>{readable_name}</b> has been banned for using: {helpers.escape(matched_filter['keyword'])}\n"
                f"📝 <b>Reason:</b> {helpers.escape(matched_filter['reply'])}"
            )
        except:
            pass
        return
    
    user = msg.from_user
    if not user or user.is_bot or user.id in DEV_LIST:
        return
    
    if not msg.text or msg.text.startswith('/'):
        return
    
    try:
        member = await msg.chat.get_member(user.id)
        if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return
    except:
        pass
    
    try:
        is_approved = await is_user_approved(msg.chat.id, user.id)
        if is_approved:
            return
    except:
        pass
    
    try:
        warn_filters = await get_filters_cached(msg.chat.id)
        if not warn_filters:
            return
    except:
        return
    
    message_text = msg.text.lower().strip()
    matched_filter = None
    
    for filter_data in warn_filters:
        keyword = filter_data['keyword'].lower().strip()
        if not keyword:
            continue
        
        if keyword == message_text:
            matched_filter = filter_data
            break
        
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, message_text, re.IGNORECASE):
            matched_filter = filter_data
            break
    
    if not matched_filter:
        return
    
    strong = await get_strong_warn(msg.chat.id)
    if strong:
        try:
            await msg.delete()
        except:
            pass
    
    try:
        await add_warn(msg.chat.id, user.id, matched_filter['reply'])
        warns, limit = await gather(
            get_warns(msg.chat.id, user.id),
            get_warn_limit(msg.chat.id)
        )
        
        if len(warns) >= limit:
            user_mention = await get_user_mention_fast(context.bot, msg.chat.id, user.id)
            punish_text = await apply_warn_punishment(msg.chat, user.id, user_mention, limit)
            if punish_text:
                await msg.reply_html(punish_text)
            return
        
        user_mention = await get_user_mention_fast(context.bot, msg.chat.id, user.id)
        await msg.reply_html(
            f"⚠️ {user_mention} {helpers.escape(matched_filter['reply'])}\n"
            f"📊 <b>Warnings:</b> {len(warns)}/{limit}",
            reply_markup=get_warn_keyboard(user.id)
        )
    except:
        pass
