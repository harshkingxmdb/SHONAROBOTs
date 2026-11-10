from AloneX import pbot, font, app
from AloneX.db import connection_db
from AloneX.helpers.decorator import Command, only_private
from AloneX.helpers.pyro_utils import check_membership
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, constants
from telegram.ext import ContextTypes
import config

async def is_user_admin(chat_id: int, user_id: int, bot):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in [constants.ChatMemberStatus.ADMINISTRATOR, constants.ChatMemberStatus.OWNER]
    except Exception:
        return False

@Command('connect')
async def connect_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    bot = context.bot

    if chat.type != constants.ChatType.PRIVATE:
        # In a group, connect to the current group
        if await check_membership(chat.id, user.id):
            await connection_db.connect(user.id, chat.id)
            await message.reply_text(font(f"✅ Successfully connected to {chat.title}!"))
        else:
            await message.reply_text(font("❌ You must be a member to connect to this chat."))
        return

    # In Private Chat
    args = context.args
    if not args:
        # List history
        history = await connection_db.get_history(user.id)
        if not history:
            await message.reply_text(font("You haven't connected to any chats yet!"))
            return

        txt = "Recently connected chats:\n"
        keyboard = []
        for cid in history:
            try:
                target_chat = await bot.get_chat(cid)
                title = target_chat.title or target_chat.username or str(cid)
                keyboard.append([InlineKeyboardButton(title, callback_data=f"connect_{cid}")])
            except:
                continue

        if not keyboard:
            await message.reply_text(font("Could not retrieve information for recently connected chats."))
        else:
            await message.reply_text(txt, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    query = args[0]
    try:
        if query.startswith("-100") or (query.startswith("-") and query[1:].isdigit()) or query.isdigit():
            target_chat_id = int(query)
        else:
            target_chat = await bot.get_chat(query)
            target_chat_id = target_chat.id

        target_chat_obj = await bot.get_chat(target_chat_id)
        if await check_membership(target_chat_id, user.id):
            await connection_db.connect(user.id, target_chat_id)
            await message.reply_text(font(f"✅ Successfully connected to {target_chat_obj.title}!"))
        else:
            await message.reply_text(font("❌ You must be a member in the target chat to connect."))
    except Exception as e:
        await message.reply_text(font(f"❌ Error: {str(e)}"))

@Command('disconnect')
async def disconnect_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prev = await connection_db.disconnect(user_id)
    if prev:
        await update.effective_message.reply_text(font("✅ Disconnected from the current chat."))
    else:
        await update.effective_message.reply_text(font("❌ You are not connected to any chat."))

@Command('reconnect')
async def reconnect_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    res = await connection_db.reconnect(user_id)
    if res:
        try:
            target_chat = await context.bot.get_chat(res)
            await update.effective_message.reply_text(font(f"✅ Reconnected to {target_chat.title}!"))
        except:
            await update.effective_message.reply_text(font("✅ Reconnected to previous chat."))
    else:
        await update.effective_message.reply_text(font("❌ No previous connection found."))

@Command('connection')
async def connection_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    connected_id = await connection_db.get_connected_chat(user_id)
    if connected_id:
        try:
            target_chat = await context.bot.get_chat(connected_id)
            await update.effective_message.reply_text(font(f"Current connection: {target_chat.title} (`{connected_id}`)"))
        except:
            await update.effective_message.reply_text(font(f"Current connection chat ID: `{connected_id}`"))
    else:
        await update.effective_message.reply_text(font("You are currently not connected to any chat."))

# Callback handler for history buttons
from AloneX.helpers.decorator import Callbacks

@Callbacks(r"^connect_-?\d+")
async def connect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    target_chat_id = int(query.data.split("_")[1])

    if await check_membership(target_chat_id, user_id):
        await connection_db.connect(user_id, target_chat_id)
        try:
            target_chat = await context.bot.get_chat(target_chat_id)
            await query.edit_message_text(font(f"✅ Successfully connected to {target_chat.title}!"))
        except:
            await query.edit_message_text(font("✅ Successfully connected!"))
    else:
        await query.answer(font("❌ You are no longer a member in this chat."), show_alert=True)

__mod_name__ = "𝐂ᴏɴɴᴇᴄᴛɪᴏɴs🖇"
__help__ = """
**Connections**

Allows you to manage notes and filters of a group from your private chat.

• /connect <chat_id/username>: Connect to a chat.
• /disconnect: Disconnect from the current chat.
• /reconnect: Reconnect to the previous chat.
• /connection: Show current connection info.

**Notes:**
- You must be an administrator in the group to connect.
- In a group, /connect connects you to that group.
- In private, /connect lists recent connections.
"""
