from AloneX import font
import config
import re
from telegram import constants, helpers, ReplyParameters
from telegram.helpers import escape_markdown
from telegram.ext import filters
from AloneX.db.notes import *
from AloneX.helpers.decorator import Command, admin_check, Messages, get_effective_chat_id
from AloneX.helpers.utils import get_media_id, get_media, get_method_by_type
from AloneX.helpers.log_helper import log_action
import asyncio


__module__ = "𝐍ᴏᴛᴇs📝"

__help__ = """
❂ *Commands:*
❂ /save <tag>
❂ /get #<tag> or <index>
❂ /clear #<tag> or <index>
❂ /notes
❂ /renotes

❂ *Description:*  
❂ Save, retrieve, and manage notes or files directly in your chat quickly and easily.

❂ *Examples:*  
❂ /save AloneX  
❂ /get #AloneX or 1  
❂ /clear #AloneX or 1
"""


CHATS = set()
CHATS.update(CHAT_IDS)

@Messages(filters=(filters.Regex(r'.*#\w+') & ~filters.COMMAND), group=6)
async def SendNoteHashtag(update, context):
    m = update.effective_message
    chat = m.chat
    bot = context.bot
    
    if not chat.id in CHATS:
        return
        
    hashtag_match = re.search(r'#([\w-]+)', m.text)
    if not hashtag_match:
        return
        
    tag = hashtag_match.group(1).lower()
    
    _note = await get_note_by_tag(chat.id, tag)
    if not _note:
        return await m.reply_text(font('🔴 *Note not found!*'), parse_mode=constants.ParseMode.MARKDOWN)
        
    NOTE = _note[0]
    file_type = NOTE['type']
    reply = m.reply_to_message if m.reply_to_message else m
    method = get_method_by_type(bot, file_type)
    
    if file_type == "text":
        await reply.reply_text(NOTE['text'], parse_mode=constants.ParseMode.MARKDOWN)
    else:
        await method(
            chat.id,
            NOTE['file_id'],
            caption=NOTE.get('text'),
            parse_mode=constants.ParseMode.MARKDOWN,
            reply_parameters=ReplyParameters(message_id=reply.id)
        )

       
@Command('renotes')
async def ReNotes(update, context):
       m = update.effective_message
       chat_id = await get_effective_chat_id(update)
       changes = await reindex_notes(chat_id)
       if changes:
            return await m.reply_text(
                   text='📝 *Rearranged notes order index.*', 
                   parse_mode=constants.ParseMode.MARKDOWN
            )
       else:
           return await m.reply_text(
                  text='🟢 *All are already ordered.*',
                  parse_mode=constants.ParseMode.MARKDOWN
           )


@Command('notes')
async def GetNotes(update, context):
       m = update.effective_message
       chat = m.chat
       chat_id = await get_effective_chat_id(update)
  
       chats = await get_all_chats()
       CHATS.update(chats)

       notes = await get_notes_by_chat(chat_id)
  
       if not notes:
            return await m.reply_text(font('🔴 Notes not found'), parse_mode=constants.ParseMode.MARKDOWN)

       if chat_id != chat.id:
           try:
               target_chat = await context.bot.get_chat(chat_id)
               title = target_chat.title
           except:
               title = str(chat_id)
       else:
           title = chat.title or chat.full_name

       txt = f"📝 *Notes in {title}* — (`{chat_id}`)\n\n"
       txt += "*NOTE INDEX, NOT TAG*\n\n"
       for note in notes:
           txt += f"{note['index']}, `#{note['tag']}`\n"

       txt += "\n\n```\nGet notes by using #name or /get <index>```\n\n"
       txt += f"*By {config.BOT_USERNAME}*"
       return await m.reply_text(txt, parse_mode=constants.ParseMode.MARKDOWN)
            

            

@Command('get')
async def GetNote(update, context):
       m = update.effective_message
       chat = m.chat
       chat_id = await get_effective_chat_id(update)
       bot = context.bot
       
       pattern = m.text.split()[1] if len(m.text.split()) > 1 else None
       if not pattern:
            return await m.reply_text(font('*I want note note tag or index ..*'), parse_mode=constants.ParseMode.MARKDOWN)

       chats = await get_all_chats()
       CHATS.update(chats)
       
       async def send_note(m, chat, pattern, is_tag):
  
              if is_tag:
                    _note = await get_note_by_tag(chat_id, (pattern.lower()))
                    note = _note[0] if _note else _note
              else:
                    _note = await get_note_by_index(chat_id, pattern)
                    note = _note
                
              if not note:
                  return await m.reply_text(font('🔴 *Note not found*.'), parse_mode=constants.ParseMode.MARKDOWN)
                     
              file_type = note['type']
              reply = m.reply_to_message if m.reply_to_message else m
              method = get_method_by_type(bot, file_type)

              if file_type == "text":
                    await reply.reply_text(note['text'], parse_mode=constants.ParseMode.MARKDOWN)
              else:
                    await method(
                        chat.id,
                        note['file_id'],
                        caption=note.get('text'),
                        parse_mode=constants.ParseMode.MARKDOWN,
                        reply_parameters=ReplyParameters(message_id=reply.id)
                    )
                
       if pattern.startswith('#'):
             tag = pattern.split('#')[1]
             await send_note(m, chat, tag, is_tag=True)
       elif pattern.isdigit():
             await send_note(m, chat, int(pattern), is_tag=False)
         
       else:
            return await m.reply_text(font('*You can only get note by /note <index> or /note <#name>*'), parse_mode=constants.ParseMode.MARKDOWN)
            
             


@Command('clear')
@admin_check(protect_target=False)
async def ClearNote(update, context):
       m = update.effective_message
       chat = m.chat
       chat_id = await get_effective_chat_id(update)
       r = m.reply_to_message
       pattern = m.text.split()[1] if len(m.text.split()) > 1 else None
       if not pattern:
            return await m.reply_text(font('*You have to provide me tag for clear the note.*'), parse_mode=constants.ParseMode.MARKDOWN)

       if pattern.isdigit():
              note = int(pattern)
              if await delete_note_by_index(chat_id, note):
                    log_text = f"🗑️ <b>Note Deleted</b>\n" \
                               f"<b>Group:</b> {helpers.escape(chat.title)}\n" \
                               f"<b>Index:</b> {note}\n" \
                               f"<b>By:</b> {update.effective_user.mention_html()}"
                    asyncio.create_task(log_action(context.bot, chat_id, "notes", log_text))
                    return await m.reply_text(font('🗑️ *Deleted Note!*'), parse_mode=constants.ParseMode.MARKDOWN)
              else:
                    return await m.reply_text(font('🔴 *Note not found!*'), parse_mode=constants.ParseMode.MARKDOWN)
                
       elif pattern.startswith('#'):
             tag = pattern.split('#')[1]
             if await delete_note_by_tag(chat_id, (tag.lower())):
                  log_text = f"🗑️ <b>Note Deleted</b>\n" \
                             f"<b>Group:</b> {helpers.escape(chat.title)}\n" \
                             f"<b>Tag:</b> #{tag}\n" \
                             f"<b>By:</b> {update.effective_user.mention_html()}"
                  asyncio.create_task(log_action(context.bot, chat_id, "notes", log_text))
                  return await m.reply_text(font('🗑️ *Deleted Note!*'), parse_mode=constants.ParseMode.MARKDOWN)
             else:
                  return await m.reply_text(font('🔴 *Note not found!*'), parse_mode=constants.ParseMode.MARKDOWN)
       else:
             return await m.reply_text(font('*Not a valid note index or tag either.*'), parse_mode=constants.ParseMode.MARKDOWN)
            


@Command('save')
@admin_check(protect_target=False)
async def SaveNote(update, context):
       m = update.effective_message
       chat = m.chat
       chat_id = await get_effective_chat_id(update)
       r = m.reply_to_message
       tag = '-'.join(m.text.split(maxsplit=1)[1].strip().split()) if len(m.text.split()) > 1 else None

       chats = await get_all_chats()
       CHATS.update(chats)

       tags = await get_notes_name_by_chat(chat_id)
       
       if not tag:
            return await m.reply_text(font('*You have to provide me tag for save the note.*'), parse_mode=constants.ParseMode.MARKDOWN)
       elif '#' in tag:
            return await m.reply_text('*please remove the "#" word in your note name.*', parse_mode=constants.ParseMode.MARKDOWN)
       elif tag in tags:
            return await m.reply_text(font('*This note tag already used!*'), parse_mode=constants.ParseMode.MARKDOWN)
       text = None
       file_id = None

       if r:
            file_type, file_id = get_media_id(r)
              
       if r and (r.text or r.caption):
            text = escape_markdown((r.text or r.caption))
            if file_type is None:
                   file_type = "text"

       if not (text or file_id):
           return await m.reply_text(font('*What you want to save ? reply to it.*'), parse_mode=constants.ParseMode.MARKDOWN)
              
       is_saved = await save_note(chat_id, tag=(tag.lower()), type=file_type, text=text, file_id=file_id)
  
       if is_saved:
           log_text = f"📝 <b>Note Saved</b>\n" \
                      f"<b>Group:</b> {helpers.escape(chat.title)}\n" \
                      f"<b>Tag:</b> #{tag}\n" \
                      f"<b>By:</b> {update.effective_user.mention_html()}"
           asyncio.create_task(log_action(context.bot, chat_id, "notes", log_text))
           return await m.reply_text(f'🟢 *Note #{tag} saved!*\n*—› Use:* `/get #{tag}`', parse_mode=constants.ParseMode.MARKDOWN)
       else:
           return await m.reply_text(f'🔴 *Note #{tag} failed to save!*', parse_mode=constants.ParseMode.MARKDOWN)
