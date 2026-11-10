import time
import html
from pyrogram import filters, enums
from pyrogram.types import ChatMemberUpdated, ChatAdministratorRights, Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ButtonStyle, ChatMemberStatus
from AloneX import pbot, prefix_cmds, BOT_ID, font
from AloneX.db.autodemote_db import get_autodemote_settings, set_autodemote_status, set_autodemote_limits
from AloneX.helpers.decorator import protected_ids

# Track bans: {chat_id: {admin_id: [timestamp1, timestamp2, ...]}}
BAN_TRACKER = {}

__module__ = "𝐀ᴜᴛᴏ-𝐃ᴇᴍᴏᴛᴇ📉"
__help__ = """
*Auto-Demote📉* — Prevent admin abuse by automatically demoting admins who ban too many users too quickly

• `/autodemote` — Toggle protection or check settings.
• `/setautodemote <limit> <seconds>` — Set ban limits (Default: 3 bans in 10s).

*Example:*
`/setautodemote 5 15`

*Note:* Bot needs 'can_promote_members' permission. Owners are immune.
"""

async def is_user_admin(chat_id: int, user_id: int):
    from AloneX.helpers.decorator import user_admin_cache
    if user_id in protected_ids:
        return True
    k = (chat_id, user_id, 'a')
    res = user_admin_cache.get(k)
    if res is not None:
        return res
    try:
        member = await pbot.get_chat_member(chat_id, user_id)
        res = member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
        user_admin_cache[k] = res
        return res
    except:
        return False

async def get_autodemote_keyboard(chat_id: int):
    settings = await get_autodemote_settings(chat_id)
    enabled = settings["enabled"]
    if enabled:
        text = "🟢 Autodemote: ON"
        style = ButtonStyle.SUCCESS
    else:
        text = "🔴 Autodemote: OFF"
        style = ButtonStyle.DANGER

    return InlineKeyboardMarkup([[InlineKeyboardButton(font(text), callback_data="ad_toggle", style=style)]])

@pbot.on_message(filters.command("autodemote", prefixes=prefix_cmds) & filters.group)
async def autodemote_cmd(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    chat_id = message.chat.id
    settings = await get_autodemote_settings(chat_id)

    if len(message.command) > 1:
        arg = message.command[1].lower()
        if arg in ["on", "enable"]:
            await set_autodemote_status(chat_id, True)
            return await message.reply_text(font("✅ Autodemote protection <b>Enabled</b>."), reply_markup=await get_autodemote_keyboard(chat_id), parse_mode=enums.ParseMode.HTML)
        elif arg in ["off", "disable"]:
            await set_autodemote_status(chat_id, False)
            return await message.reply_text(font("❌ Autodemote protection <b>Disabled</b>."), reply_markup=await get_autodemote_keyboard(chat_id), parse_mode=enums.ParseMode.HTML)

    status = "Enabled" if settings["enabled"] else "Disabled"
    status_text = (
        f"📉 <b>Autodemote Status</b>\n\n"
        f"<b>Status:</b> {status}\n"
        f"<b>Limit:</b> <code>{settings['limit']}</code> bans\n"
        f"<b>Window:</b> <code>{settings['window']}</code> seconds\n\n"
        f"Click the button below to toggle."
    )
    await message.reply_text(
        font(status_text),
        reply_markup=await get_autodemote_keyboard(chat_id),
        parse_mode=enums.ParseMode.HTML
    )

@pbot.on_callback_query(filters.regex(r"^ad_toggle$"))
async def ad_toggle_cb(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(font("❌ This button is for admins only!"), show_alert=True)

    settings = await get_autodemote_settings(chat_id)
    new_state = not settings["enabled"]
    await set_autodemote_status(chat_id, new_state)

    status = "Enabled" if new_state else "Disabled"
    status_text = (
        f"📉 <b>Autodemote Status</b>\n\n"
        f"<b>Status:</b> {status}\n"
        f"<b>Limit:</b> <code>{settings['limit']}</code> bans\n"
        f"<b>Window:</b> <code>{settings['window']}</code> seconds\n\n"
        f"Click the button below to toggle."
    )
    await query.message.edit_text(
        font(status_text),
        reply_markup=await get_autodemote_keyboard(chat_id),
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer(font(f"Autodemote {'Enabled' if new_state else 'Disabled'}"))

@pbot.on_message(filters.command("setautodemote", prefixes=prefix_cmds) & filters.group)
async def setautodemote_cmd(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ Admin privilege required!"))

    chat_id = message.chat.id
    if len(message.command) < 3 or not message.command[1].isdigit() or not message.command[2].isdigit():
        return await message.reply_text(
            f"⚠️ {font('<b>Usage:</b>')} <code>/setautodemote &lt;ban_limit&gt; &lt;time_window_seconds&gt;</code>\n"
            f"Example: <code>/setautodemote 3 10</code>",
            parse_mode=enums.ParseMode.HTML
        )

    limit = int(message.command[1])
    window = int(message.command[2])

    if limit < 2 or limit > 50:
        return await message.reply_text(font("❌ Limit must be between 2 and 50."))
    if window < 5 or window > 3600:
        return await message.reply_text(font("❌ Window must be between 5s and 3600s."))

    await set_autodemote_limits(chat_id, limit, window)
    await message.reply_text(
        f"✅ {font('<b>Autodemote limits updated!</b>')}\n\n"
        f"<b>Limit:</b> <code>{limit}</code> bans\n"
        f"<b>Window:</b> <code>{window}</code> seconds",
        parse_mode=enums.ParseMode.HTML
    )

@pbot.on_chat_member_updated(group=-5)
async def autodemote_watcher(client, update: ChatMemberUpdated):
    if not update.new_chat_member:
        return

    chat_id = update.chat.id

    # Check if user was banned
    if update.new_chat_member.status != enums.ChatMemberStatus.BANNED:
        return

    # Check settings
    settings = await get_autodemote_settings(chat_id)
    if not settings["enabled"]:
        return

    # Identify who performed the ban
    actor = update.from_user
    if not actor or actor.id == BOT_ID:
        return

    # Safety: Get actor status
    try:
        actor_member = await client.get_chat_member(chat_id, actor.id)
        if actor_member.status == enums.ChatMemberStatus.OWNER:
            return # Owners are immune
        if actor_member.status != enums.ChatMemberStatus.ADMINISTRATOR:
            return # Should not happen, but for safety
    except:
        return

    # Track ban
    now = time.time()
    if chat_id not in BAN_TRACKER:
        BAN_TRACKER[chat_id] = {}
    if actor.id not in BAN_TRACKER[chat_id]:
        BAN_TRACKER[chat_id][actor.id] = []

    # Record current ban and clean up old ones
    BAN_TRACKER[chat_id][actor.id].append(now)
    BAN_TRACKER[chat_id][actor.id] = [t for t in BAN_TRACKER[chat_id][actor.id] if now - t <= settings["window"]]

    # Check limit
    if len(BAN_TRACKER[chat_id][actor.id]) >= settings["limit"]:
        # RESET TRACKER for this admin to avoid redundant demotions
        BAN_TRACKER[chat_id][actor.id] = []

        # Verify bot permissions
        try:
            bot_member = await client.get_chat_member(chat_id, "me")
            if not bot_member.privileges or not bot_member.privileges.can_promote_members:
                await client.send_message(chat_id, "⚠️ <b>Autodemote Alert!</b> Admin abuse detected but I lack <code>can_promote_members</code> permission to take action.", parse_mode=enums.ParseMode.HTML)
                return
        except:
            return

        # Perform demotion
        try:
            await client.promote_chat_member(
                chat_id,
                actor.id,
                privileges=ChatAdministratorRights(
                    can_manage_chat=False,
                    can_post_messages=False,
                    can_edit_messages=False,
                    can_delete_messages=False,
                    can_post_stories=False,
                    can_edit_stories=False,
                    can_delete_stories=False,
                    can_restrict_members=False,
                    can_promote_members=False,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False,
                    can_manage_video_chats=False,
                    is_anonymous=False
                )
            )

            mention = f"<a href='tg://user?id={actor.id}'>{html.escape(actor.first_name)}</a>"
            await client.send_message(
                chat_id,
                f"📉 <b>Autodemote Action</b>\n\n"
                f"<b>👤 Admin:</b> {mention} [<code>{actor.id}</code>]\n"
                f"<b>🚫 Reason:</b> Ban abuse detected (<code>{settings['limit']}</code> bans in <code>{settings['window']}</code>s)\n"
                f"<b>⚖️ Result:</b> Automatically demoted to member.",
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            print(f"Autodemote failed: {e}")
