
import config
import base64
from pyrogram import filters, types, enums
from AloneX import pbot as bot, font
from AloneX.helpers.decorator import only_premium



__module__ = "𝐅ɪʟᴇ-𝐒ᴛᴏʀᴇ🫙"

__help__ = '''
*Commands*:
❂ /getlink
❂ /getlink: Get a sharable link for a media file

*Usage*:
Reply to a sticker, audio, document, video, photo, or animation with this command.

*Example*:
Reply to an image with `/getlink`
'''

@bot.on_message(filters.command("getlink"))
@only_premium
async def getFileLink(_, message):
        m = message
        chat = message.chat
        r = m.reply_to_message
  
        #if chat.type != enums.ChatType.PRIVATE:
        #     return await m.reply_text(font("This command currently work only in PRIVATE!"))
        if not m.reply_to_message or (r and getattr(r, 'media') is None):
             return await m.reply_text(font("Reply to the media for store 🧐"))
          
        media = [
         enums.MessageMediaType.ANIMATION,
         enums.MessageMediaType.VIDEO,
         enums.MessageMediaType.STICKER,
         enums.MessageMediaType.PHOTO,
         enums.MessageMediaType.DOCUMENT,
         enums.MessageMediaType.AUDIO
       ]
        if r.media not in media:
             return await m.reply_text(font("This is not a supported media type!"))
          
        else:
             
            try:
               forward = await r.forward(config.FILE_DB_CHANNEL)
               msg_id = forward.id

               s_media = ["document", "video", "sticker", "photo", "animation", "audio"]
               for kind in s_media:
                    media = getattr(r, kind, None)
                    if media is not None:
                         unique_id = getattr(media, "file_unique_id")
      
               encoded_data_url = base64.b64encode(f"{msg_id}&{unique_id}".encode()).decode()
               file_link = f"https://t.me/{bot.me.username}?start=getfile-{encoded_data_url}"
               button = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(font("⚡ Share link"), url=file_link, style=enums.ButtonStyle.SUCCESS)]])
               return await m.reply_text(f"**Copy the sharable link**: `{file_link}`", reply_markup=button, quote=True)
              
            except Exception as e:
                return await m.reply(f"❌ ERROR: {e}")
            


