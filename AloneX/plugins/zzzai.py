import os
from AloneX import aiohttpsession as session, font
from AloneX.helpers.utils import is_base64_encoded, get_as_document, encode_to_base64, decode_to_base64
from AloneX.helpers.decorator import Command
from AloneX.helpers.scripts import GetZzzCodeAi, ZzzAiCodeGenerator, ZzzAiCodeConverter
from telegram import constants


__module__ = "𝐙ᴀɪ💻"

__help__ = """
*ZAi💻*

*Description:*  
This module provides AI-powered code generation and conversion tools. Convert code between languages, generate new code, and retrieve previous outputs using unique IDs.

*Commands:*  
❂ `/zzzcai` — Convert code from one language to another. Example: `/zzzcai py | c` (convert Python code to C).  
❂ `/zzzai` — Generate code in any programming language. Example: `/zzzai html code for my first web page`.  
❂ `/getzzzai <id>` — Retrieve the output of a response using a unique identifier.

*Examples:*  
`/zzzai hey make me blush`  
`/zzzcai py | c # reply to file or message text`
"""

@Command('getzzzai')
async def GetZzzAiOutput(update, context):
   user = update.effective_user
   m = update.effective_message
   chat = update.effective_chat
   bot = context.bot
   
   if len(m.text.split()) < 2:
        return await m.reply_text("🧐 Where's that unique file id ?")
      
   file_id = m.text.split(maxsplit=1)[1]
   isVaild = is_base64_encoded(file_id)
   if not isVaild:
       return await m.reply_text(font("🕵️ Why did you give me some random string instead of a actual file id"))
   request_url = decode_to_base64(file_id)
   result = await GetZzzCodeAi(request_url)
   output = result.get('output')
   if output:
       if output > 3500:
            file_path = get_as_document(output)
            return await m.reply_document(
                 file_path, quote=True, parse_mode=constants.ParseMode.MARKDOWN
         )
       else:       
           return await m.reply_text(
              text=result.get('output'),
              parse_mode=constants.ParseMode.MARKDOWN
       )
   else:
       return await m.reply_text(
          "🙋 *Something went wrong try again some later if its still didn't work try request again 🤷*", 
          parse_mode=constants.ParseMode.MARKDOWN
       )

@Command('zzzcai')
async def ZzzAiConvert(update, context):
   user = update.effective_user
   m = update.effective_message
   chat = update.effective_chat
   bot = context.bot
  
   r = m.reply_to_message
   isDocument = (
       True if r and r.document and r.document.mime_type.startswith('text') else None
       )
   textArgs = (
       r.text if r and r.text else None
   )
   
   if isDocument:
       file_id = r.document.file_id
       file = await bot.get_file(file_id)
       file_path = await file.download_to_drive()
       with open(file_path, 'r') as document:
            code = document.read()
            os.remove(file_path)
         
   elif textArgs:
         code = textArgs
      
   else:
       return await m.reply_text(
         "*🙋 Make sure you to reply a code txt document or text message. with* `/zzzcai lang to_lang`🙋",
          parse_mode=constants.ParseMode.MARKDOWN
       )
      
   if len(m.text.split()) < 3:
        return await m.reply_text(
           "🧐 E.g. ```python\n /zzzcai py | c``` for convert python code to c program.",
           parse_mode=constants.ParseMode.MARKDOWN
         )
   try:
     lang, to_lang = m.text.split(maxsplit=1)[1].split('|')
   except Exception as e:
       return await m.reply_text(f"❌ Error: {str(e)}")

   msg = await m.reply_text(
      "⏳ *Please wait! Started to converting...*",
      parse_mode=constants.ParseMode.MARKDOWN
   )
   
   result = await ZzzAiCodeConverter(lang, to_lang, code)
   request_url = result['request_url']
   api_url = result['api_url']
   result = await GetZzzCodeAi(api_url, request_url)
   request_url = encode_to_base64(request_url)
   output = result.get('output')


   if output:
       if len(output) > 3500:
            file_path = get_as_document(output)
            await m.reply_document(
                 file_path, 
                 caption=f"Converted the code to *{to_lang}* by @{bot.username}",                 parse_mode=constants.ParseMode.MARKDOWN
            )
            return await msg.delete()
          
       else:       
           return await msg.edit_text(
              text=result.get('output'),
              parse_mode=constants.ParseMode.MARKDOWN
           )
   else:
       await msg.edit_text(
           f"🙋 hey {user.first_name}!, Sorry the code has been started to convert but please wait and try again later with `/getzzzai {request_url}` for get the code...",
           parse_mode=constants.ParseMode.MARKDOWN
       )



@Command('zzzai')
async def ZzzAiGenerator(update, context):
   user = update.effective_user
   m = update.effective_message
   chat = update.effective_chat
   bot = context.bot
   r = m.reply_to_message
   
   if len(m.text.split()) < 2:
        return await m.reply_text(
           "🧐 E.g ```\n/zzzai write a code a say hello in c, cpp, py, js```",
           parse_mode=constants.ParseMode.MARKDOWN
         )
   try:
     lang = "anything"
     code = m.text.split(maxsplit=1)[1]
   except Exception as e:
       return await m.reply_text(f"❌ Error: {e}")

   msg = await m.reply_text(
      "⏳ *Please wait! started to generating...*",
      parse_mode=constants.ParseMode.MARKDOWN
   )
   
   result = await ZzzAiCodeGenerator(lang, code)
   request_url = result['request_url']
   api_url = result['api_url']
   result = await GetZzzCodeAi(api_url, request_url)
   request_url = encode_to_base64(request_url)
   output = result.get('output')

   if output:
       if len(output) > 3500:
            file_path = get_as_document(output)
            await m.reply_document(
                 file_path, 
                 caption=f"Generated the code in *{lang}* by @{bot.username}",
                 parse_mode=constants.ParseMode.MARKDOWN
            )
            return await msg.delete()
          
       else:       
           return await msg.edit_text(
              text=result.get('output'),
              parse_mode=constants.ParseMode.MARKDOWN
           )
   else:
       await msg.edit_text(
           f"🙋 hey {user.first_name}!, Sorry the code has been started to generate but please wait and try again later with `/getzzz {request_url}` for get the code...",
           parse_mode=constants.ParseMode.MARKDOWN
       )

