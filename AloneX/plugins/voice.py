
import aiohttp
import os
import config
from AloneX import pbot as bot, font
from AloneX.helpers.scripts import text_to_voice
from pyrogram import filters, types, enums

user_txt = {}



__module__ = "𝐕ᴏɪᴄᴇ🎤"

__help__ = """
*Voice*

*Description:*  
Convert text messages to speech using various available voices.  
Simply reply to a message with text and select your favorite voice.

*Commands:*  
❂ `/voice` – Reply to a text message to convert it to speech

*Example:*  
`/voice` (reply to a message containing text)
"""

voice_data = {
    # Disney Voices
    'en_us_ghostface': 'Ghost',
    'en_us_chewbacca': 'Chewie',
    'en_us_c3po': 'C3PO',
    'en_us_stitch': 'Stitch',
    'en_us_stormtrooper': 'Trooper',
    'en_us_rocket': 'Rocket',

    # English Voices
    'en_au_001': 'AU F',
    'en_au_002': 'AU M',
    'en_uk_001': 'UK M1',
    'en_uk_003': 'UK M2',
    'en_us_001': 'US F1',
    'en_us_002': 'US F2',
    'en_us_006': 'US M1',
    'en_us_007': 'US M2',
    'en_us_009': 'US M3',
    'en_us_010': 'US M4',

    # European Voices
    'fr_001': 'FR M1',
    'fr_002': 'FR M2',
    'de_001': 'DE F',
    'de_002': 'DE M',
    'es_002': 'ES M',

    # American Voices
    'es_mx_002': 'MX M',
    'br_001': 'BR F1',
    'br_003': 'BR F2',
    'br_004': 'BR F3',
    'br_005': 'BR M',

    # Asian Voices
    'id_001': 'ID F',
    'jp_001': 'JP F1',
    'jp_003': 'JP F2',
    'jp_005': 'JP F3',
    'jp_006': 'JP M',
    'kr_002': 'KR M1',
    'kr_003': 'KR F',
    'kr_004': 'KR M2',

    # Singing Voices
    'en_female_f08_salut_damour': 'Alto',
    'en_male_m03_lobby': 'Tenor',
    'en_female_f08_warmy_breeze': 'Warm',
    'en_male_m03_sunshine_soon': 'Sun',

    # Other
    'en_male_narration': 'Narr',
    'en_male_funny': 'Fun',
    'en_female_emotional': 'Peace'
}


def keyboard_buttons(user_id: int):
     row = []
     buttons = []
     for key, value in voice_data.items():
          row.append(types.InlineKeyboardButton(value, callback_data=f'voice#{user_id}#{key}', style=enums.ButtonStyle.PRIMARY))
          if len(row) == 4:
              buttons.append(row)
              row = []
     if row:
         buttons.append(row)
     buttons.append([types.InlineKeyboardButton(font('❌ Close'), callback_data=f'pyrodel#{user_id}', style=enums.ButtonStyle.DANGER)])
     return buttons
     
     

@bot.on_callback_query(filters.regex("^voice"))
async def voice_cq(_, query: types.CallbackQuery):
       user = query.from_user
       _, user_id, voice_id = query.data.split("#")
       if user.id != int(user_id):
             return await query.answer(font("This is not your request."), show_alert=True)
       else:
           text = user_txt.get(user.id)
           if not text:
               return await query.answer(font("This query was expired, try again."), show_alert=True)
           else:

                await query.message.edit("Analysing Audio ...")
                audio_bytes = await text_to_voice(text, voice_id)
                if 'error' in audio_bytes:
                     return await query.message.edit(f"❌ ERROR: {audio_bytes['error']}")
                else:
                     await query.message.edit("🗣️ **Audio preparing ...**")
                     path = f"voice_{query.id}.mp3"
                     with open(path, "wb") as file:
                           file.write(audio_bytes['audio_data'])
                       
                     await query.edit_message_media(
                          media=types.InputMediaAudio(
                            media=path,
                            file_name="AloneX Voice's",
                            title = "AloneX",
                            caption=f"**Voice model**: `{voice_data[voice_id]}`\n**By {config.BOT_USERNAME}**",
                          )
                     )
                     os.remove(path)


                                                     

@bot.on_message(filters.command("voice") & ~filters.forwarded, group=-330)
async def voice(_, m: types.Message):
        r = m.reply_to_message
        user = m.from_user
     
        if r and r.text:
             user_txt[user.id] = r.text
             buttons = keyboard_buttons(user.id)
             await m.reply_text(
                 text="```\nSelect your desired voice.```",
                 reply_markup=types.InlineKeyboardMarkup(buttons)
             )                           
        else:
           return await m.reply_text(font("Reply to message text."))
