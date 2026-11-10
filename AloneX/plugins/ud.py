from AloneX import pbot as app, font
from pyrogram import filters, types, enums
import aiohttp
import config


__module__ = "𝐔ᴅ📖"

__help__ = """
*UD📖*

*Description:*  
Get meanings of urban slang and abbreviations, including common internet terms.

*Commands:*  
❂ `/ud <query>` – Search the Urban Dictionary for a word or phrase

*Example:*  
`/ud lol`  
`/ud imao`
"""

@app.on_message(filters.command("ud"), group=-46)
async def urban(_, m):  
    user_id = m.from_user.id
    if len(m.text.split()) == 1:
        return await m.reply(font("Enter the text for which you would like to find the definition."))
    
    text = m.text.split(None,1)[1]
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.urbandictionary.com/v0/define?term={text}") as response:
            api = await response.json()
    
    mm = api["list"]
    if 0 == len(mm):
        return await m.reply(font("=> No results Found!"))
    
    string = f"🔍 **Ward**: {mm[0].get('word')}\n\n📝 **Definition**: {mm[0].get('definition')}\n\n✏️ **Example**: {mm[0].get('example')}\n\n**By {config.BOT_USERNAME}**"
    
    if 1 == len(mm):
        return await m.reply(text=string, quote=True)
    else:
        num = 0
        return await m.reply(
            text=string, 
            reply_markup=types.InlineKeyboardMarkup([
                [types.InlineKeyboardButton(font('Next'), callback_data=f"udnxt:{user_id}:{text}:{num}", style=enums.ButtonStyle.PRIMARY)]
            ]), 
            quote=True
        )
              
@app.on_callback_query(filters.regex("^udnxt"))   
async def udnext(_, query):
    user_id = int(query.data.split(":")[1])
    text = str(query.data.split(":")[2])
    num = int(query.data.split(":")[3])+1
    
    if not query.from_user.id == user_id:
        return await query.answer(font("This is not for You!"))
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.urbandictionary.com/v0/define?term={text}") as response:
            api = await response.json()
    
    mm = api["list"]
    uwu = mm[num]
    
    if num == len(mm)-1:
        string = f"🔍 **Ward**: {uwu.get('word')}\n\n📝 **Definition**: {uwu.get('definition')}\n\n✏️ **Example**: {uwu.get('example')}\n\n"
        string += f"Page: {num+1}/{len(mm)}\n\n**By {config.BOT_USERNAME}**"
        return await query.message.edit(
            text=string, 
            reply_markup=types.InlineKeyboardMarkup([
                [types.InlineKeyboardButton(font('➡️ Back'), callback_data=f"udbck:{query.from_user.id}:{text}:{num}", style=enums.ButtonStyle.PRIMARY)]
            ])
        )
    else:
        string = f"🔍 **Ward**: {uwu.get('word')}\n\n📝 **Definition**: {uwu.get('definition')}\n\n✏️ **Example**: {uwu.get('example')}\n\n"
        string += f"Page: {num+1}/{len(mm)}\n\n**By {config.BOT_USERNAME}**"
        buttons = [[
            types.InlineKeyboardButton(font("Back ⏮️"), callback_data=f"udbck:{query.from_user.id}:{text}:{num}", style=enums.ButtonStyle.PRIMARY),
            types.InlineKeyboardButton(font("Next ⏭️"), callback_data=f"udnxt:{query.from_user.id}:{text}:{num}", style=enums.ButtonStyle.PRIMARY)
        ]]
        return await query.message.edit(
            text=string, 
            reply_markup=types.InlineKeyboardMarkup(buttons)
        )

@app.on_callback_query(filters.regex("^udbck"))   
async def udback(_, query):
    user_id = int(query.data.split(":")[1])
    text = str(query.data.split(":")[2])
    num = int(query.data.split(":")[3])-1
    
    if not query.from_user.id == user_id:
        return await query.answer(font("This is not for You!"))
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.urbandictionary.com/v0/define?term={text}") as response:
            api = await response.json()
    
    mm = api["list"]
    uwu = mm[num]
    
    if num == 0:
        string = f"🔍 **Ward**: {uwu.get('word')}\n\n📝 **Definition**: {uwu.get('definition')}\n\n✏️ **Example**: {uwu.get('example')}\n\n"
        string += f"Page: {num+1}/{len(mm)}\n\n**By {config.BOT_USERNAME}**"
        return await query.message.edit(
            text=string, 
            reply_markup=types.InlineKeyboardMarkup([
                [types.InlineKeyboardButton(font('➡️ Next'), callback_data=f"udnxt:{query.from_user.id}:{text}:{num}", style=enums.ButtonStyle.PRIMARY)]
            ])
        )
    else:
        string = f"🔍 **Ward**: {uwu.get('word')}\n\n📝 **Definition**: {uwu.get('definition')}\n\n✏️ **Example**: {uwu.get('example')}\n\n"
        string += f"Page: {num+1}/{len(mm)}\n\n**By {config.BOT_USERNAME}**"
        buttons = [[
            types.InlineKeyboardButton(font("Back ⏮️"), callback_data=f"udbck:{query.from_user.id}:{text}:{num}", style=enums.ButtonStyle.PRIMARY),
            types.InlineKeyboardButton(font("Next ⏭️"), callback_data=f"udnxt:{query.from_user.id}:{text}:{num}", style=enums.ButtonStyle.PRIMARY)
        ]]
        return await query.message.edit(
            text=string, 
            reply_markup=types.InlineKeyboardMarkup(buttons)
        )
