from AloneX import font
import config
from AloneX.helpers.decorator import Command, devs_only
from AloneX.db.users import update_user_premium, get_all_premium_users
from telegram import constants
from telegram.error import BadRequest

@Command('premium_users')
@devs_only
async def get_premium_users_func(update, context):
    """Handler to fetch and display all premium users."""
    try:
        users = await get_all_premium_users()
        if not users:
            return await update.message.reply_text(font("No premium users found."), parse_mode=constants.ParseMode.HTML)
        
        text = "✨ <b>miaksa's Premium Users</b>:\n\n"
        text += "".join(f"<code>{user}</code>\n" for user in users)
        await update.message.reply_text(text, parse_mode=constants.ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

@Command('premium')
@devs_only
async def update_premium_func(update, context):
    """Handler to add or remove premium status for a user."""
    try:
        message = update.effective_message
        args = message.text.split()

        # Validate command format
        if len(args) != 3:
            return await message.reply_text(font("❌ Incorrect format! Usage: /premium <user_id> <-add/-rm>"))

        _, user_id, action = args
        action = action.lower()

        # Validate user_id and action
        if not user_id.isdigit() or action not in ['-add', '-rm']:
            return await message.reply_text(font("❌ Invalid input! Usage: /premium <user_id> <-add/-rm>"))

        user_id = int(user_id)
        if action == "-add":
            success = await update_user_premium(user_id, True)
            text = "✅ *AloneX's Premium successfully granted to the user.*" if success else "🧐 *User is already premium.*"
            if success and user_id not in config.PREMIUM_USERS:
                config.PREMIUM_USERS.append(user_id)
        elif action == "-rm":
            success = await update_user_premium(user_id, False)
            text = "❌ *AloneX's Premium removed from the user.*" if success else "🧐 *User is not a premium user.*"
            if success and user_id in config.PREMIUM_USERS:
                config.PREMIUM_USERS.remove(user_id)

        await message.reply_text(text, parse_mode=constants.ParseMode.MARKDOWN)
    except BadRequest as e:
        await message.reply_text(f"Telegram API error: {e}")
    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")
