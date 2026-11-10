from AloneX import font
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMedia, constants
from AloneX.helpers.decorator import Callbacks
from AloneX.db.characters import get_character
from AloneX.db.user_characters import user_character_exists, add_user_character
from AloneX.db.game import get_cash, update_cash

# -------------------- Health Upgrade -------------------- #
@Callbacks("^chealth")
async def characterHealth(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    _, character_id, fuser_id = query.data.split("#")
    if user_id != int(fuser_id):
        return await query.answer(font("Not your request 😉"), show_alert=True)
    return await query.answer(font("Health upgrade coming soon 😉"), show_alert=True)

# -------------------- Attack Upgrade -------------------- #
@Callbacks("^cattack")
async def characterAttack(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    _, character_id, fuser_id = query.data.split("#")
    if user_id != int(fuser_id):
        return await query.answer(font("Not your request 😉"), show_alert=True)
    return await query.answer(font("Attack upgrade coming soon 😉"), show_alert=True)

# -------------------- Home View -------------------- #
@Callbacks("^chome")
async def characterHome(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    _, character_id, fuser_id = query.data.split("#")
    if user_id != int(fuser_id):
        return await query.answer(font("Not your request 😉"), show_alert=True)

    character = await get_character(character_id)
    image = random.choice(character['images'])
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(font("Shop 🛒"), callback_data=f"cshop#{character_id}#{user_id}")]
    ])
    text = f"""
🌀 **Name**: `{character['character_name']}`
💚 **Health**: `{character['health']}`
🏅 **Rarity**: `Type {character['rarity_type']}`
💸 **Cash**: `{character['cash']}`
"""
    await query.edit_message_media(
        media=InputMedia(media_type='photo', media=image, caption=text, parse_mode=constants.ParseMode.MARKDOWN),
        reply_markup=buttons
    )

# -------------------- Shop View -------------------- #
@Callbacks("^cshop")
async def characterShop(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    _, character_id, fuser_id = query.data.split("#")
    if user_id != int(fuser_id):
        return await query.answer(font("Not your request 😉"), show_alert=True)

    if not await user_character_exists(user_id, character_id):
        return await query.answer("You don't own this character yet!", show_alert=True)

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(font("Health 💚"), callback_data=f"chealth#{character_id}#{user_id}"),
         InlineKeyboardButton(font("Attack 🔴"), callback_data=f"cattack#{character_id}#{user_id}")],
        [InlineKeyboardButton(font("🏡 Home 🏡"), callback_data=f"chome#{character_id}#{user_id}")]
    ])
    text = "```\nWhat do you want to upgrade? Choose below option.\n```"
    await query.edit_message_text(text=text, parse_mode=constants.ParseMode.MARKDOWN, reply_markup=buttons)

# -------------------- Buy Character -------------------- #
@Callbacks("^cbuy")
async def characterBuy(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    _, character_id, fuser_id = query.data.split("#")
    if user_id != int(fuser_id):
        return await query.answer(font("Not your request 😉"), show_alert=True)

    if await user_character_exists(user_id, character_id):
        return await query.answer(font("You already have this character 🥴"), show_alert=True)

    character_info = await get_character(character_id)
    user_cash = await get_cash(user_id)
    if user_cash < character_info['cash']:
        return await query.answer(f"Not enough cash to buy {character_info['character_name']} 🤧", show_alert=True)

    await add_user_character(
        user_id=user_id,
        character_name=character_info['character_name'],
        character_id=character_info['character_id'],
        attack=character_info['attack'],
        health=character_info['health'],
        images=character_info['images'],
        rarity_type=character_info['rarity_type']
    )
    await update_cash(user_id, -character_info['cash'])
    await query.answer(f"Purchased {character_info['character_name']}! 🥳", show_alert=True)
