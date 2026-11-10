from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM, Message, CallbackQuery
from pyrogram.enums import ButtonStyle, ChatMemberStatus
from AloneX import pbot, prefix_cmds, font
from AloneX.helpers.decorator import protected_ids
from AloneX.db.ghost_db import is_ghost_enabled, set_ghost, CHAT_IDS as GHOST_CACHE

__module__ = "𝐆ʜᴏsᴛ-𝐌ᴏᴅᴇ👻"
__help__ = """
❂ *Ghost Mode Module* — Automatically delete service messages like join/leave.

*Commands:*
❂ /ghostmode — Check status and toggle via buttons.
❂ /ghostmode <on/off> — Enable or disable ghost mode.

*Notes:*
- Bot must be admin with delete permission.
- **Ghost Mode is enabled by default.**
- When enabled, join and leave service messages will be deleted automatically.
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

async def get_ghost_keyboard(chat_id: int):
    enabled = await is_ghost_enabled(chat_id)
    if enabled:
        text = "🟢 Ghost Mode: ON"
        style = ButtonStyle.SUCCESS
    else:
        text = "🔴 Ghost Mode: OFF"
        style = ButtonStyle.DANGER

    return IKM([[IKB(font(text), callback_data="ghost_toggle", style=style)]])

@pbot.on_message(filters.command("ghostmode", prefixes=prefix_cmds) & filters.group)
async def ghostmode_cmd(_, message: Message):
    if not message.from_user:
        return
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    if len(message.command) > 1:
        arg = message.command[1].lower()
        if arg == "on":
            await set_ghost(message.chat.id, True)
            await message.reply_text(font("✅ Ghost Mode has been enabled."))
        elif arg == "off":
            await set_ghost(message.chat.id, False)
            await message.reply_text(font("🚫 Ghost Mode has been disabled."))
        else:
            await message.reply_text(font("❌ Invalid argument! Use on or off."))
        return

    enabled = await is_ghost_enabled(message.chat.id)
    status = "Enabled" if enabled else "Disabled"

    await message.reply_text(
        font(f"👻 Ghost Mode Status: {status}\n\nWhen enabled, I will automatically delete service messages like join/leave."),
        reply_markup=await get_ghost_keyboard(message.chat.id)
    )

@pbot.on_callback_query(filters.regex(r"^ghost_toggle$"))
async def ghost_toggle_callback(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(font("❌ This button is for admins only!"), show_alert=True)

    enabled = await is_ghost_enabled(chat_id)
    new_state = not enabled
    await set_ghost(chat_id, new_state)

    status_text = "Enabled" if new_state else "Disabled"
    await query.message.edit_text(
        font(f"👻 Ghost Mode Status: {status_text}\n\nWhen enabled, I will automatically delete service messages like join/leave."),
        reply_markup=await get_ghost_keyboard(chat_id)
    )
    await query.answer(font(f"Ghost Mode {'Enabled' if new_state else 'Disabled'}"))

@pbot.on_message(filters.service, group=-65)
async def ghost_cleaner(_, message: Message):
    chat_id = message.chat.id

    # We only care about join/leave service messages
    if not (message.new_chat_members or message.left_chat_member):
        return

    if await is_ghost_enabled(chat_id):
        try:
            await message.delete()
        except:
            pass
