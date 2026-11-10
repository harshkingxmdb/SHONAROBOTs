
import json

from AloneX import app, font
from AloneX.helpers.decorator import Command, Messages, admin_check, only_groups
from AloneX.helpers.scripts import Translator
from AloneX.helpers.utils import Langs
from AloneX.db.translate import get_chat, CHAT_IDS, add_chat, remove_chat, get_all_chats
from telegram import constants
from telegram.ext import filters



__module__ = "𝐓ʀᴀɴsʟᴀᴛᴏʀ📶"

__help__ = """
*Commands*
/translator, /tr

```
Note: Only for groups!
/translator <lang_code> or off: Turn on the translator to convert all messages in other languages to the specified <lang_code>. Use /translator off to disable the translator in the chat.
```

```
For a single translation:
Use /tr {language code} and reply to a message.
```
"""



translator = Translator()


@Command('langs')
async def GetLangs(update, context):
      m = update.effective_message
      langs = list(Langs.keys())
      text = [",".join(str(y) for y in langs[i:i+4]) for i in range(0, len(langs), 4)]
      text = "\n".join(text)
      return await m.reply_text(
            f"🌐 *Language codes*:\n{text}", parse_mode=constants.ParseMode.MARKDOWN
      )

@Command("tr")
async def Translate(update, context):
      m = update.effective_message
      if len(m.text.split()) < 2:
             to_lang = "en"
             lang = None
      else:
          lang_list = list(Langs.keys())
          args = m.text.split()[1:]
          if "|" in args:
              lang = args[0]
              to_lang = args[2]
              if lang not in lang_list:
                     return await m.reply_text(font("*Incorrect to source lang do /langs for know about it.*"), parse_mode=constants.ParseMode.MARKDOWN)
          else:
              to_lang = args[0]
              lang = None
                
          if to_lang not in lang_list:
                 return await m.reply_text(font("*Incorrect translate language code !!!* use /langs to know supported languages"), parse_mode=constants.ParseMode.MARKDOWN)
      if not (reply := m.reply_to_message) or (reply and not reply.text):
           return await m.reply_text(font("*Kindly reply to a text message to translate!*"), parse_mode=constants.ParseMode.MARKDOWN)

      try:
          if lang:
              tl = await translator.translate(
                   text=reply.text,
                   to_language=to_lang,
                   source_language=lang
                   
                )
          else:
               tl = await translator.translate(
                     text=reply.text,
                     to_language=to_lang               
                )

          text = (
                   "🆎 *Original Lang*: {ol}\n"
                   "🆎 *Translated Lang*: {dl}\n\n"
                   "✨ *Translated Text*: {text}"
            )
          return await m.reply_text(
                  text.format(ol=tl.original_language, dl=tl.dest_language, text=tl.translated_text),
                  parse_mode=constants.ParseMode.MARKDOWN
            )
                  
      except Exception as e:
              return await m.reply_text(
                    text=f"❌ ERROR: `{e}`",
                    parse_mode=constants.ParseMode.MARKDOWN
              )
          
      

@Messages(filters=(filters.TEXT & filters.ChatType.GROUPS), group=15)
async def sendTranslator(update, context) -> None:
      m = message = update.effective_message
      message_text: str = m.text


      if len(message_text) >= 2500: return
      if not m.chat.id in CHAT_IDS: return
        
      detector = await translator.detector(message_text)
  
      if detector:
        
          lang = detector.get('language', 'en')
          slang = await get_chat(m.chat.id)
          
          if lang != (to_lang:=slang.get('lang', 'en')):

              translate = await translator.translate(
                   message_text, 
                   to_lang,
                   lang
              )
            
              text = (
                f"*❓ (Detected)! Translated {translate.original_language} to {translate.dest_language}.*\n\n"
                f"*⚡ Translate Text*:\n\n{translate.translated_text}"
              )
              return await m.reply_text(
                  text=text, 
                  parse_mode=constants.ParseMode.MARKDOWN
              )
              





@Command('translator')
@admin_check("can_change_info")
@only_groups
async def translatorCmd(update, context) -> None:
      m = message = update.effective_message

      if len(m.text.split()) > 1 and m.text.split()[1].lower() == 'off':
        
          await remove_chat(message.chat.id)
          if message.chat.id in CHAT_IDS: CHAT_IDS.remove(message.chat.id)
            
          return await m.reply_text(
             text=f"*{message.chat.title} is has been removed for translate*.",
             parse_mode=constants.ParseMode.MARKDOWN
           )
  
      elif len(m.text.split()) > 1 and len((lang:= m.text.split()[1].lower())) == 2 and lang in list(Langs.keys()):
            lang_data = Langs[lang]
            langName, lang_NativeName = lang_data['name'], lang_data['nativeName']
            
            await add_chat(message.chat.id, lang)
            if message.chat.id not in CHAT_IDS: CHAT_IDS.append(message.chat.id)
              
            return await m.reply_text(
                 f"⚡ *Starting now i will translate {message.chat.title}'s every all other language into {langName} except the actual {lang_NativeName} language*.",
                 parse_mode=constants.ParseMode.MARKDOWN
            )
            
      else:
          return await m.reply_text(font("🙋 Query required! READ PM!!!"))
      
      
      
