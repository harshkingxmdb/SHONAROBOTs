from zoneinfo import ZoneInfo
from telegram.constants import ChatAction
from datetime import datetime, timedelta
from telegram.ext import ContextTypes
import asyncio
import time
import config
from AloneX import pbot as bot, START_TIME, font
from telegram import constants
from pyrogram import filters, types, enums
from pyrogram.enums import ButtonStyle
from AloneX.helpers.decorator import Command
from AloneX.helpers.utils import time_formatter, shuffle_text, shout_text, owo_text, copypasta_text, get_ua, encode_to_base64, decode_to_base64, is_base64_encoded
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction as PTBAction
from AloneX import (
    pbot,
    app as ptb_app,
    START_TIME,
    BOT_USERNAME,
)

__module__ = "𝐄xᴛʀᴀ⚠️"

__help__ = """
*Extra Fun & Utility Commands*  

*Commands*:
❂ /morse ❂ /morsed  ❂ /encode  ❂ /decode  ❂ /shout  
❂ /owo  ❂ /copypasta  ❂ /ping  ❂ /shuffle  ❂ /table  ❂ /alive

*Description*:
A collection of miscellaneous tools to enhance your Telegram experience!  
Encode/decode text, style your messages, generate multiplication tables, check bot status, and have fun with text transformations.

────────────────────────

*Command Details*:
❂ /morse & /morsed — Encode or decode text into Morse code.  
❂ /encode or /decode — Base64 encryption/decryption.  
❂ /shout — Convert your text to uppercase loudly.  
❂ /owo — Transform text in a cute “neko” style.  
❂ /copypasta — Add emojis and stylize text for fun.  
❂ /ping — Check bot response and latency.  
❂ /shuffle — Randomly shuffle letters in replied text (upper/lower).  
❂ /table <int> — Generate multiplication table (default 15 rows).  
"""




def multiplication_table(num: int, row: int = 15) -> str:
    return "\n".join(f"{i} x {num} = {num * i}" for i in range(1, row + 1))

@Command('table')
async def MTable(update, context):
    m = update.effective_message
    if not context.args or not context.args[0].isdigit():
        return await m.reply_text(font("e.g: <code>/table 9</code>"), parse_mode=constants.ParseMode.HTML)
    
    text = multiplication_table(int(context.args[0]))
    return await m.reply_text(f"<pre>{text}</pre>", parse_mode=constants.ParseMode.HTML)

    


@Command(['shuffle', 'shout', 'copypasta', 'owo'])
async def randomTextStyle(update, context):
       m = update.effective_message
       r = m.reply_to_message
       cmd = m.text.split()[0][1:]
       code = m.text.split(maxsplit=1)[1] if len(m.text.split()) > 1 else (r.text or r.caption) if r and (r.text or r.caption) else None
       if not code: return await m.reply_text(font('Reply to text'))
       if cmd == "shout":
             text = shout_text(code)
       elif cmd == "owo":
             text = owo_text(code)
       elif cmd == "shuffle":
             text = shuffle_text(code)
       else:
             text = copypasta_text(code)

       return await (r if r else m).reply_text(text[:4000])
       

@Command("getua")
async def getUserAgent(update, context):
    m = update.effective_message
    user_agent = get_ua()
    await m.reply_text(f"*User Agent*:\n`{user_agent}`", parse_mode=constants.ParseMode.MARKDOWN)


@Command(['encode', 'decode'])
async def Base64Encrypter(update, context):
  
    m = update.effective_message
    r = m.reply_to_message
    command = m.text.split()[0][1:]
    string = r.text if (not len(m.text.split()) > 1 and r and r.text) else m.text.replace(str(m.text[0]+command), '') if len(m.text.split()) > 1 else None
  
    if not string:
        return await m.reply_text(
          text=f"Uhm string to {command} do?".title()
        )


    if command.lower() == 'decode':
      
        if is_base64_encoded(string):
            decode = decode_to_base64(string)
            return await m.reply_text(decode)
        else:
           return await m.reply_text(font("It seems not a base64 encoded string 🤷"))
          
    else:
      
        if is_base64_encoded(string):
            return await m.reply_text("Doesn't it already encoded? 🙋")
        else:
            encode = encode_to_base64(string)
            return await m.reply_text(encode)





MORSE_CODE_DICT = { 'A':'.-', 'B':'-...',
                    'C':'-.-.', 'D':'-..', 'E':'.',
                    'F':'..-.', 'G':'--.', 'H':'....',
                    'I':'..', 'J':'.---', 'K':'-.-',
                    'L':'.-..', 'M':'--', 'N':'-.',
                    'O':'---', 'P':'.--.', 'Q':'--.-',
                    'R':'.-.', 'S':'...', 'T':'-',
                    'U':'..-', 'V':'...-', 'W':'.--',
                    'X':'-..-', 'Y':'-.--', 'Z':'--..',
                    '1':'.----', '2':'..---', '3':'...--',
                    '4':'....-', '5':'.....', '6':'-....',
                    '7':'--...', '8':'---..', '9':'----.',
                    '0':'-----', ', ':'--..--', '.':'.-.-.-',
                    '?':'..--..', '/':'-..-.', '-':'-....-',
                    '(':'-.--.', ')':'-.--.-'
       }

@bot.on_message(filters.command("morse"))
async def morse_encrypt(bot, message: types.Message):
    cmd = message.command

    msg = await message.reply_text(font("ℹ️ **Encoding ...**"))
    async def encrypt(message):
       cipher = ''
       for letter in message:
           if letter != ' ':
 
            # Looks up the dictionary and adds the
            # corresponding morse code
            # along with a space to separate
            # morse codes for different characters
                word = MORSE_CODE_DICT.get(letter, None)
                if not word:
                     await msg.edit(f"**You have invalid letter in your text '{letter}'**")
                     return None
                cipher += word + ' '


           else:
            # 1 space indicates different characters
            # and 2 indicates different words
                cipher += ' '
 
       return cipher

    main_text = ""
    if len(cmd) > 1:
        main_text = " ".join(cmd[1:])
    elif message.reply_to_message and len(cmd) == 1:
        main_text = message.reply_to_message.text
    elif not message.reply_to_message and len(cmd) == 1:
        await msg.edit("I need something to encrypt")
        await asyncio.sleep(2)
        await msg.delete()
        return

    input_str = main_text
    if not input_str:
        await msg.edit("`give me something to encrypt`")
        return
    text = await encrypt(input_str.upper())
    if text:
        await msg.edit(text, parse_mode=enums.ParseMode.DISABLED)


@bot.on_message(filters.command("morsed"))
async def morse_decrypt(bot, message: types.Message):
    cmd = message.command

    msg = await message.reply(font("**Decoding ...**"))
    def decrypt(message):
 
    # extra space added at the end to access the
    # last morse code
         message += ' '
         decipher = ''
         citext = ''
         for letter in message:
              # checks for space
            if (letter != ' '):
            # counter to keep track of space
                 i = 0
 # storing morse code of a single character
                 citext += letter
        # in case of space
            else:
            # if i = 1 that indicates a new character
               i += 1
            # if i = 2 that indicates a new word
               if i == 2 :
                  # adding space to separate words
                   decipher += ' '
               else:
                # accessing the keys using their values (reverse of encryption)
                   decipher += list(MORSE_CODE_DICT.keys())[list(MORSE_CODE_DICT.values()).index(citext)]
                   citext = ''
 
         return decipher
 

    main_text = ""
    if len(cmd) > 1:
        main_text = " ".join(cmd[1:])
    elif message.reply_to_message and len(cmd) == 1:
        main_text = message.reply_to_message.text
    elif not message.reply_to_message and len(cmd) == 1:
        await msg.edit("I need something to decrypt")
        await asyncio.sleep(2)
        await msg.delete()
        return

    input_str = main_text
    if not input_str:
        await msg.edit("`give me something to decrypt`")
        return

    await msg.edit(decrypt(input_str).lower(), parse_mode=enums.ParseMode.DISABLED)
