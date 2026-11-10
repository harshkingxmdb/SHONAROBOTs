import json
import config
import aiohttp
import random
import base64
from AloneX import prefix_cmds, font
from urllib.parse import quote
from pyrogram import types, filters, enums
from pyrogram.enums import ButtonStyle
from AloneX import pbot as bot
from AloneX.helpers.scripts import Anime

__module__ = "𝐀ɴɪᴍᴇ🎌"

__help__ = """
*Anime🎌*

*Description:*  
This module provides anime-related information, including anime search, character details, quotes, and image sources.

*Commands:*  
❂ `/character` - Get information about an anime character.  
❂ `/anime` - Search for an anime.  
❂ `/animequote` - Get a random anime quote.  
❂ `/sauce` - Find the source of an image.

*Examples:*  
`/anime attack on titan`  
`/character AloneX`
"""

anime = Anime()
characters_cached = {}
anime_cached = {}


@bot.on_callback_query(filters.regex("^pyrodel"))
async def pyro_delete(_, query: types.CallbackQuery):
    user_id = int(query.data.split("#")[1])
    if (user_id == query.from_user.id) or (query.message.chat.type == enums.ChatType.PRIVATE):
        await query.message.delete()
        return await query.answer(font("Deleted!"))
    else:
        info = await query.message.chat.get_member(query.from_user.id)
        if info.privileges:
            await query.message.delete()
            return await query.answer(font("Deleted!"))
        else:
            return await query.answer("❌ You can't delete", show_alert=True)


def convert_to_keyboard(anime_id, data, user_id):
    buttons = [[
        types.InlineKeyboardButton(font("Back 🔙"), callback_data=f"anime_back#{anime_id}#{user_id}", style=ButtonStyle.PRIMARY)
    ]]
    row = []
    for character in data:
        row.append(types.InlineKeyboardButton(str(character['name']), callback_data=f"chars_info#{anime_id}#{character['character_id']}#{user_id}", style=ButtonStyle.SUCCESS))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([types.InlineKeyboardButton(font("❌ Close"), callback_data=f"pyrodel#{user_id}", style=ButtonStyle.DANGER)])
    return buttons


@bot.on_callback_query(filters.regex("^chars_back"))
async def pyro_chars_back(_, query: types.CallbackQuery):
    _, anime_id, user_id = query.data.split("#")
    if query.from_user.id != int(user_id):
        return await query.answer(font("This is not your request!"))
    characters = characters_cached.get(anime_id)
    if not characters:
        return await query.answer(font("This query was expired. search again."), show_alert=True)
    buttons = convert_to_keyboard(anime_id, characters, query.from_user.id)
    return await query.edit_message_caption(
        caption="```\nCharacters information```",
        reply_markup=types.InlineKeyboardMarkup(buttons)
    )


@bot.on_callback_query(filters.regex("^chars_info"))
async def pyro_chars_info(_, query: types.CallbackQuery):
    _, anime_id, character_id, user_id = query.data.split("#")
    if query.from_user.id != int(user_id):
        return await query.answer(font("This is not your request!"))
    character = await anime.get_character(character_id)
    if "error" in character:
        return await query.answer(f"❌ ERROR: {character['error']}", show_alert=True)

    about = character['about'] or "N/A"
    about = about[:850] + " ..." if len(about) > 850 else about
    nicknames = "\n".join(f"—» {name}" for name in character['nicknames'][:5]) if character.get('nicknames') else "Not available"
    caption = f"""
⚔️ **Character info**:

**Name**: {character['name']}, {character['name_kanji'] or "N/A"}
**NickName's**: 
`{nicknames}`

**About**: 
```\n{about}```"""

    buttons = [[
        types.InlineKeyboardButton(font("Back 🔙"), callback_data=f"chars_back#{anime_id}#{user_id}", style=ButtonStyle.PRIMARY),
        types.InlineKeyboardButton(font("❌ Close"), callback_data=f"pyrodel#{user_id}", style=ButtonStyle.DANGER)
    ]]
    await query.edit_message_media(
        media=types.InputMediaPhoto(media=character['photo_url'], caption=caption),
        reply_markup=types.InlineKeyboardMarkup(buttons)
    )


@bot.on_callback_query(filters.regex("^anime_chars"))
async def pyro_anime_chars(_, query: types.CallbackQuery):
    _, user_id, anime_id = query.data.split("#")
    if query.from_user.id != int(user_id):
        return await query.answer(font("This is not your request!"))
    characters = characters_cached.get(anime_id)
    if not characters:
        characters = await anime.get_characters(anime_id)
        if isinstance(characters, dict):
            return await query.answer(f"❌ ERROR: {characters['error']}", show_alert=True)
    characters_cached[anime_id] = characters
    buttons = convert_to_keyboard(anime_id, characters, query.from_user.id)
    return await query.edit_message_caption(
        caption="```\nCharacters information```",
        reply_markup=types.InlineKeyboardMarkup(buttons)
    )


@bot.on_callback_query(filters.regex("^anime_back"))
async def pyro_anime_back(_, query: types.CallbackQuery):
    _, anime_id, user_id = query.data.split("#")
    if query.from_user.id != int(user_id):
        return await query.answer(font("This is not your request!"))
    result = anime_cached.get(anime_id)
    if not result:
        return await query.answer(font("This query was expired, search again."), show_alert=True)

    synopsis = result["synopsis"] or "N/A"
    synopsis = synopsis[:700] + " ..." if len(synopsis) > 700 else synopsis
    trailer = result["trailer"] or f"https://www.youtube.com/results?search_query={quote(result['title_english'] + '+trailer')}"

    text = f"""
🎬 **Title (English)**: `{result['title_english']}`
🎥 **Title (Japanese)**: `{result['title_japanese']}`
📚 **Source**: `{result['source']}`
📺 **Episodes**: `{result['episodes']}`
✅ **Status**: `{result['status']}`
🗓️ **Aired**: `{result['aired']}`
⏳ **Duration**: `{result['duration']}`
⭐ **Rating**: `{result['rating']}`

📝 **Synopsis**:
`{synopsis}`
"""
    buttons = types.InlineKeyboardMarkup([[
        types.InlineKeyboardButton(font("🎬 Trailer"), url=trailer, style=ButtonStyle.PRIMARY),
        types.InlineKeyboardButton(font("📝 Info"), url=result['mal_url'], style=ButtonStyle.SUCCESS)], [
        types.InlineKeyboardButton(font("⚔️ Character"), callback_data=f"anime_chars#{user_id}#{anime_id}", style=ButtonStyle.SUCCESS),
        types.InlineKeyboardButton(font("❌ Close"), callback_data=f"pyrodel#{user_id}", style=ButtonStyle.DANGER)
    ]])
    return await query.edit_message_media(
        media=types.InputMediaPhoto(media=result['photo_url'], caption=text),
        reply_markup=buttons
    )


@bot.on_message(filters.command("character", prefix_cmds) & ~filters.forwarded, group=2)
async def search_character(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(font("Character name required."))
    name = m.text.split(maxsplit=1)[1]
    user = m.from_user
    character = await anime.character(name)
    if "error" in character:
        return await m.reply_text(f"❌ ERROR: {character['error']}")
    about = character['about'] or "N/A"
    about = about[:1000] + " ..." if len(about) > 1000 else about
    nicknames = "\n".join(f"—» {name}" for name in character['nicknames']) if character['nicknames'] else "Not available"

    caption = f"""
⚔️ **Character info**[\u200B]({character['photo_url']}):

**Name**: {character['name']}, {character['name_kanji']}
**NickName's**: 
`{nicknames}`

**About**: 
```\n{about}```"""

    buttons = [[types.InlineKeyboardButton(font("❌ Close"), callback_data=f"pyrodel#{user.id}", style=ButtonStyle.DANGER)]]
    return await m.reply_text(text=caption, reply_markup=types.InlineKeyboardMarkup(buttons))


@bot.on_message(filters.command("anime", prefix_cmds) & ~filters.forwarded, group=3)
async def search_anime(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(font("Anime name required."))
    name = m.text.split(maxsplit=1)[1]
    result = await anime.search(name)
    if "error" in result:
        return await m.reply_text(f"❌ ERROR: `{result['error']}`")
    anime_cached[str(result['anime_id'])] = result
    synopsis = result["synopsis"] or "N/A"
    synopsis = synopsis[:700] + " ..." if len(synopsis) > 700 else synopsis
    trailer = result["trailer"] or f"https://www.youtube.com/results?search_query={quote((result['title_english'] or result['title_japanese']) + '+trailer')}"

    text = f"""
🎬 **Title (English)**: `{result['title_english']}`
🎥 **Title (Japanese)**: `{result['title_japanese']}`
📚 **Source**: `{result['source']}`
📺 **Episodes**: `{result['episodes']}`
✅ **Status**: `{result['status']}`
🗓️ **Aired**: `{result['aired']}`
⏳ **Duration**: `{result['duration']}`
⭐ **Rating**: `{result['rating']}`

📝 **Synopsis**:
`{synopsis}`
"""

    buttons = types.InlineKeyboardMarkup([[
        types.InlineKeyboardButton(font("🎬 Trailer"), url=trailer, style=ButtonStyle.PRIMARY),
        types.InlineKeyboardButton(font("📝 Info"), url=result['mal_url'], style=ButtonStyle.SUCCESS)], [
        types.InlineKeyboardButton(font("⚔️ Character"), callback_data=f"anime_chars#{m.from_user.id}#{result['anime_id']}", style=ButtonStyle.SUCCESS),
        types.InlineKeyboardButton(font("❌ Close"), callback_data=f"pyrodel#{m.from_user.id}", style=ButtonStyle.DANGER)
    ]])
    return await m.reply_photo(photo=result['photo_url'], caption=text, reply_markup=buttons)


@bot.on_message(filters.command("sauce", prefix_cmds) & ~filters.forwarded, group=4)
async def _sauce(_, m: types.Message):
    r = m.reply_to_message
    if r and r.photo:
        photo = await r.download(in_memory=True)
        encoded_string = base64.b64encode(bytes(photo.getbuffer()))
        data = {
            'api_token': 'TEST-API-TOKEN',
            'photo_b64': encoded_string.decode()
        }
        url = "http://cheatbot.twc1.net/getName"
        msg = await m.reply(font("🔎 **Checking for character info ...**"))
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status != 200:
                    return await msg.edit_text(font("🤧 Api down or something went wrong server side."))
                result = await response.json()
                if "message" in result:
                    return await msg.edit_text(result["message"])
                name = result['name']
                prefix = result['prefix']
                sbot = result['bot_name']
                text = f"ℹ️ **Character**: {name}\n🤖 **From bot**: @{sbot}\n\n⚡ **Copy**: `{prefix} {name}`"
                return await msg.edit_text(text)
    else:
        return await m.reply(font("*Reply to Anime Character Photo*."))


@bot.on_message(filters.command("animequote", prefix_cmds) & ~filters.forwarded, group=5)
async def animeQuote(_, message):
    with open("./AloneX/helpers/data/anime_quote.json") as file:
        data = json.load(file)
    quote = random.choice(data)
    text = f"""
#AnimeQuote

>{quote['content']}

Anime: **{quote['anime']['name']}**
By: **{quote['character']['name']}**
"""
    await message.reply_text(text, quote=True)
