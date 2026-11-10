import config
from AloneX import pbot as bot, font
from AloneX.helpers.utils import Password
from pyrogram import filters, types
from pyrogram.enums import ParseMode, ButtonStyle

__module__ = "𝐏ᴀssᴡᴏʀᴅs🔑"

__help__ = """
❂ *Commands*:
❂ /password
❂ /passwords

❂ *Description:*  
❂ Generate secure, random, and readable passwords instantly using interactive buttons. Perfect for creating strong credentials safely.
❂
"""

# Handle command: /password
@bot.on_message(filters.command(["password", "passwords"]) & ~filters.forwarded, group=-38)
async def GenPasswordCmd(_, message):
    user = message.from_user
    text = (
        "🔐 **Password Generator**\n"
        "Click a button below to generate a secure password.\n\n"
        f"_By {config.BOT_USERNAME}_"
    )

    buttons = get_buttons(user.id)
    await message.reply_text(text, reply_markup=types.InlineKeyboardMarkup(buttons), parse_mode=ParseMode.MARKDOWN)


# Handle all password button presses
@bot.on_callback_query(filters.regex("^pw_"))
async def GenPasswordCq(_, query):
    cmd, user_id = query.data.split("#")
    user_id = int(user_id)

    if query.from_user.id != user_id:
        return await query.answer(font("This is not your request."), show_alert=True)

    password = []
    if cmd == "pw_random":
        password = Password.random_password()
    elif cmd == "pw_random_digits":
        password = Password.random_password(only_string=False)
    elif cmd == "pw_random_strings":
        password = Password.random_password(only_digit=False)
    elif cmd == "pw_normal_nouns":
        password = Password.normal_password(only_adjective=False)
    elif cmd == "pw_normal_adjectives":
        password = Password.normal_password(only_noun=False)
    elif cmd == "pw_easy_nouns":
        password = Password.easy_password(only_adjective=False)
    elif cmd == "pw_easy_adjectives":
        password = Password.easy_password(only_noun=False)
    else:
        return await query.answer(font("Unknown command"), show_alert=True)

    await edit_text(query.message, password, query.from_user.id)


# Helper: Edit message with new passwords and buttons
async def edit_text(message, password_list, user_id):
    text = "**🔐 New Passwords:**\n\n"
    text += "\n".join(f"`{p}`" for p in password_list[:5])
    text += "\n\n⚙️ **Choose more options below:**"
    text += f"\n_By {config.BOT_USERNAME}_"

    buttons = get_buttons(user_id)
    await message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(buttons), parse_mode=ParseMode.MARKDOWN)


# Helper: Generate button layout
def get_buttons(user_id):
    return [
        [
            types.InlineKeyboardButton(font("🔢 Digits"), callback_data=f"pw_random_digits#{user_id}", style=ButtonStyle.PRIMARY),
            types.InlineKeyboardButton(font("🔤 Strings"), callback_data=f"pw_random_strings#{user_id}", style=ButtonStyle.PRIMARY),
            types.InlineKeyboardButton(font("🎲 Random"), callback_data=f"pw_random#{user_id}", style=ButtonStyle.PRIMARY)
        ],
        [
            types.InlineKeyboardButton(font("📘 Normal Noun"), callback_data=f"pw_normal_nouns#{user_id}", style=ButtonStyle.PRIMARY),
            types.InlineKeyboardButton(font("📗 Normal Adjective"), callback_data=f"pw_normal_adjectives#{user_id}", style=ButtonStyle.PRIMARY)
        ],
        [
            types.InlineKeyboardButton(font("📙 Easy Noun"), callback_data=f"pw_easy_nouns#{user_id}", style=ButtonStyle.PRIMARY),
            types.InlineKeyboardButton(font("📕 Easy Adjective"), callback_data=f"pw_easy_adjectives#{user_id}", style=ButtonStyle.PRIMARY)
        ],
        [
            types.InlineKeyboardButton(font("❌ Close"), callback_data=f"pyrodel#{user_id}", style=ButtonStyle.DANGER)
        ]
    ]
