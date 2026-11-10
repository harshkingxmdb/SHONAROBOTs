import config
import re
from io import BytesIO
import asyncio
import io
import os
import sys
import traceback
import time
import subprocess
import asyncio
import datetime as dt
import uuid
import config
import html
from contextlib import redirect_stdout
from AloneX import app, pbot, DEV_LIST, BOT_USERNAME, BOT_ID, LOGS_CHANNEL, database, OWNER_ID, SUDO_USERS, font
from telegram import Update, constants, ReplyParameters
from telegram.constants import ParseMode
from telegram.ext import filters, ContextTypes, ApplicationHandlerStop, CallbackQueryHandler, CallbackContext  
from AloneX.helpers.decorator import Command, Messages, devs_only, sudos_only, protect_sudos, Callbacks, RestrictedCallback
from AloneX.helpers.scripts import paste
from AloneX.helpers.utils import get_as_document, extract_user
from AloneX.db.users import get_all_users, get_user_id_by_username, add_user, update_users_status_to_inactive, update_users_status_to_active, get_all_active_users
from AloneX.db.chats import get_all_chats
from AloneX import db, LOGGER
from AloneX.db import ignore
from pyrogram import enums, types, StopPropagation
from AloneX.db import *
from AloneX.db.sudo import get_all_sudo_users
from AloneX.db.gban import *
from telegram.error import BadRequest
from telegram.constants import ParseMode
import datetime as dt

__module__ = '𝐃ᴇᴠs-𝐓ᴏᴏʟ🤴'


__help__ = '''
*Commands*:
/logs, /eval, /peval, 
/sh, /echo, /stats,
/send, /left, /bcast,
/block, /unblock, /blocklist
/mongodb, /restart

```
- /logs: Get current bot logs.
- /eval <code>: Execute code in the bot.
- /peval <code>: Execute pyrogram code in the bot.
- /sh <code>: Execute a shell command in the bot.
- /echo <text>: Echo the given text or reply to a message.
- /stats: Check bot statistics.
- /send <chat_id>: Send a message to a specific chat or user (reply to a message).
- /left <chat_id>: Leave a specific chat.
- /bcast: Broadcast a message to all users.
- /block: Block a user from interacting with the bot.
- /unblock: Unblock a user, allowing them to interact with the bot again.
- /blocklist: View the list of blocked users.
- /mongodb: shows mongodb stats.
- /restart: restart bot
```

```Note:
Required privileges.
```
'''

@Command('mongodb')
@devs_only
async def MongoDBInfo(update, context):
      m = update.effective_message
      result = await database.command({"dbStats": 1})
      LDS = round(result['dataSize']/(1024*1024), 2)
      SS = round(result['storageSize']/(1024*1024), 2)
      IS = round(result['indexSize']/(1024*1024), 2)
      TCC = result['collections']
      text = (
         "📊 <b>MONGO-DATABASE Status</b>:\n\n"
         f"<b>✰ Logical Data Size</b>: <code>{LDS} MB</code>\n"
         f"<b>✰ Storage Size</b>: <code>{SS} MB</code>\n"
         f"<b>✰ Index Size</b>: <code>{IS} MB</code>\n"
         f"<b>✫ Total Collection Count</b>: <code>{TCC}</code>\n"
      )
      return await m.reply_text(text, parse_mode=constants.ParseMode.HTML)
      

RESTART_FILE = "restart_chat.txt"

@Command('restart')
@devs_only
async def restart(update, context):
    msg = await update.effective_message.reply_text("🔄 Bot Restarting...")

    # save chat_id and message_id for editing after restart
    with open("restart_data.txt", "w") as f:
        f.write(f"{msg.chat.id}:{msg.message_id}")

    os.execl(sys.executable, sys.executable, "-m", "AloneX")

@Command(("ignorelist", "blocklist"))
@devs_only
async def _ignoreUserlist(update, context):
    m = update.effective_message
    if m.from_user.id in config.DEV_LIST:
        users = list(map(str, await ignore.get_all_users()))
        if not users:
             return await m.reply_text("Currently None blocked users.")
        text = "🚫 *Blocked Users*:"
        text += "\n".join(f"–› `{user}`" for user in users)
        return await m.reply_text(text, parse_mode=constants.ParseMode.MARKDOWN)


@Command(("unignore", "unblock"))
@devs_only
async def _unIgnoreUser(update, context):
    m = update.effective_message
    bot = context.bot
    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text("Can't find the user.")

    msg = await m.reply_text(
        text='*Checking in database...*',
        parse_mode=constants.ParseMode.MARKDOWN
    )
      
    await ignore.remove_user(user_id)
    if user_id in ignore.USER_IDS:
        ignore.USER_IDS.remove(user_id)
        await msg.edit_text(
            '✅ *Unblocked user successfully.*',
            parse_mode=constants.ParseMode.MARKDOWN
        )

    try:
        user = await bot.get_chat(user_id)
    except Exception:
        return

    await msg.edit_text(
        f"🗣️ <b>Unblocked user {user.mention_html()} now he/she can interact with bot again.</b>",
        parse_mode=constants.ParseMode.HTML
    )

    try:
        await bot.copy_message(
            chat_id=config.LOGS_CHANNEL,
            from_chat_id=msg.chat.id,
            message_id=msg.message_id
        )
    except BadRequest as e:
        if "protected content" in str(e).lower():
            await bot.send_message(
                chat_id=config.LOGS_CHANNEL,
                text=f"🗣️ Unblocked user {user.mention_html()}",
                parse_mode=constants.ParseMode.HTML
            )
        else:
            raise
        

@Command(("ignore", "block"))
@devs_only
async def _ignoreUser(update, context):
    m = update.effective_message
    bot = context.bot

    user_id = await extract_user(m, self=False)
    if not user_id:
        return await m.reply_text("Can't find the user.")      

    await ignore.add_user(user_id)
    if user_id not in ignore.USER_IDS:
        ignore.USER_IDS.append(user_id)

    user = await bot.get_chat(user_id)
    msg = await m.reply_text(
        text=f"<b>🔇 Completely ignored user {user.mention_html()}</b>",
        parse_mode=constants.ParseMode.HTML
    )

    try:
        # First try to copy (better than forward, avoids protected content issue)
        await bot.copy_message(
            chat_id=config.LOGS_CHANNEL,
            from_chat_id=msg.chat.id,
            message_id=msg.message_id
        )
    except BadRequest as e:
        if "protected content" in str(e).lower():
            # If still protected, just send plain text
            await bot.send_message(
                chat_id=config.LOGS_CHANNEL,
                text=f"🔇 Completely ignored user {user.mention_html()}",
                parse_mode=constants.ParseMode.HTML
            )
        else:
            raise
              
@Messages(group=-1000000, block=True)
async def UserPtbIgnore(update, context):
    m = update.effective_message
    if m.from_user:
        if m.from_user.id in DEV_LIST or m.from_user.id in SUDO_USERS or m.from_user.id == OWNER_ID:
            return
        if m.from_user.id in ignore.USER_IDS:
             raise ApplicationHandlerStop

@pbot.on_message(group=-1000000)
async def UserPyroIgnore(_, message):
     if message.from_user:
         if message.from_user.id in DEV_LIST or message.from_user.id in SUDO_USERS or message.from_user.id == OWNER_ID:
             return
         if message.from_user.id in ignore.USER_IDS:
              raise StopPropagation

@Callbacks(pattern=None, block=True, group=-1000000)
async def UserPtbCallbackIgnore(update, context):
    q = update.callback_query
    if q.from_user:
        if q.from_user.id in DEV_LIST or q.from_user.id in SUDO_USERS or q.from_user.id == OWNER_ID:
            return
        if q.from_user.id in ignore.USER_IDS:
             await q.answer(font("🚫 You are blocked from interacting with the bot."), show_alert=True)
             raise ApplicationHandlerStop

@pbot.on_callback_query(group=-1000000)
async def UserPyroCallbackIgnore(_, query):
     if query.from_user:
         if query.from_user.id in DEV_LIST or query.from_user.id in SUDO_USERS or query.from_user.id == OWNER_ID:
             return
         if query.from_user.id in ignore.USER_IDS:
              await query.answer(font("🚫 You are blocked from interacting with the bot."), show_alert=True)
              raise StopPropagation

@pbot.on_inline_query(group=-1000000)
async def UserPyroInlineIgnore(_, query):
     if query.from_user:
         if query.from_user.id in DEV_LIST or query.from_user.id in SUDO_USERS or query.from_user.id == OWNER_ID:
             return
         if query.from_user.id in ignore.USER_IDS:
              raise StopPropagation


@Messages(filters=filters.ChatType.PRIVATE & ~filters.COMMAND, block=True, group=66)
async def forwardToOwner(update, context):
    m = update.effective_message
    user = update.effective_user
    log_chat = config.LOGS_CHANNEL
    if m and user and user.id != log_chat and log_chat:
        try:
            await m.forward(
               chat_id=log_chat
            )
        except Exception as e:
            LOGGER.info(
              f"❌ Error forwarding message:\n{e}"
            )

@Command('echo')
@sudos_only
async def Echo(update, context):
    m = update.effective_message  
    r = m.reply_to_message
    chat = m.chat
    if len(m.text.split()) > 1:
        txt = m.text.split(maxsplit=1)[1]
        await chat.send_message(
          text=txt,
          parse_mode=ParseMode.MARKDOWN,
          reply_parameters=ReplyParameters(message_id=r.id if r else m.id)
        )
    elif r:
        await r.copy(
          chat_id=m.chat.id, 
          reply_parameters=ReplyParameters(message_id=r.id)
        )
    else:
        return await m.reply_text("*what ???*", parse_mode=constants.ParseMode.MARKDOWN)


@Command('send')
@sudos_only
async def botSend(update, context):
    m = update.effective_message
    if not len((chat:= m.text.split())) < 2 and (r:= m.reply_to_message):
      
       chat = chat[1]
       async def get_chat(chat_id: str):
           try:
               chat = await context.bot.get_chat(chat_id)
               return chat.id
           except Exception as e:
               await m.reply_text(f"❌ *Chat not found*:\n{e}", parse_mode=constants.ParseMode.MARKDOWN)
               return False
               
            
       if chat.startswith("@"):
           chat_id = await get_user_id_by_username(chat[1:])
           if not chat_id:
               chat_id = await get_chat(chat)
       else:
           chat_id = await get_chat(chat)

       if not chat_id:
           return await m.reply_text("🤷 *I couldn't find the chat/user!*", parse_mode=constants.ParseMode.MARKDOWN)
         
       try:
          await r.copy(chat_id)
       except Exception as e:
           return await m.reply_text(f"Error: {e}")
         
       return await m.reply_text("✅")
      
    else:
        return await m.reply_text("🙋 *Reply to a message & give chat id!*", parse_mode=constants.ParseMode.MARKDOWN)



@Command('left')
@devs_only
async def leftChat(update, context):
    m = update.effective_message
    if not len(m.text.split()) == 2:
        return await m.reply_text('chat id/username to left 🤔')
    
    chat_id = m.text.split()[1]
    try:
        chat = await context.bot.get_chat(chat_id)
        await m.reply_text(f"Leaving {chat.title} - ({chat.id})")
        await context.bot.leave_chat(chat.id)
    except Exception as e:
        return await m.reply_text("❌ Error occured: " + str(e))
  

@Command('bcast')
@devs_only
async def Broadcast(update, context):
   ''' info: broadcasting to all users '''
   m = update.effective_message
   if not m.reply_to_message:
       return await m.reply_text("**⚡ Reply to the message for broadcast**")
     
   failed = 0
   count = 0
   sent = 0
   errors = {}
   inactive_users_list = []
   active_users_list = []


   all_users = await get_all_active_users()
  
   msg = await m.reply_text("🔄 *Broadcasting....*", parse_mode=constants.ParseMode.MARKDOWN)
   for user_id in all_users:
       if count % 5 == 0:
           await msg.edit_text(f"⚡ *Broadcast successful done to {sent} users!*", parse_mode=constants.ParseMode.MARKDOWN)
           await asyncio.sleep(5) # sleep 5 seconds every time send to 5 chats
       try:
           fmsg = await m.reply_to_message.forward(user_id)
           active_users_list.append(user_id)
           try:
             await fmsg.pin()
           except: 
               pass
       except Exception as e:
             failed += 1
             inactive_users_list.append(user_id)
             errors[user_id] = str(e)

       sent += 1
       count += 1 

   
   if errors:
      errors_txt = ''
      for user, error in errors.items():
          errors_txt += f"[{user}]: {error}\n"
        
      document = get_as_document(errors_txt)
      await m.reply_document(document, caption="❌ Errors when sending broadcast")

   if inactive_users_list:
        await update_users_status_to_inactive(inactive_users_list) # update inactive users status in database
   if active_users_list:
        await update_users_status_to_active(active_users_list)
     
   await msg.edit_text(
       text = (
         f"—» Successfully broadcast done in (`{len(all_users)-failed}`) chats!\n"
         f"—» Failed to send broadcast in (`{failed}`) chats!\n"
       ),
         parse_mode=ParseMode.MARKDOWN
   )

def p(*args, **kwargs):
    print(*args, **kwargs)


async def aexec(code, context, bot, update, message, m, r, my, chat, ruser):
    exec(
        "async def __aexec(context, bot, update, message, m, r, my, chat, ruser): "
        + "".join(f"\n {l_}" for l_ in code.split("\n"))
    )
    return await locals()["__aexec"](context, bot, update, message, m, r, my, chat, ruser)


async def send(msg, cmd, stime, bot, update, message_id):
    taken_time = round(time.time() - stime, 3)
    chat_id = update.effective_chat.id

    if len(str(msg)) > 4000:
        if len(cmd) > 1000:
            _paste = await paste(cmd)
            caption = _paste["paste_url"] if 'error' not in _paste else "<b>Paste link not available at the moment.</b>"
        else:
            caption = f"<b>Command:</b>{cmd}\n\n⚡ <b>Taken time</b>: <code>{taken_time}</code>"

        out_file = get_as_document(msg)
        await bot.send_document(
            chat_id=chat_id,
            document=out_file,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
    else:
        escaped_msg = msg.replace("<", "&lt;").replace(">", "&gt;")
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"<b>Command:</b><pre language='python'>\n{cmd}</pre>\n\n<b>Output</b><pre language='python'>\n{msg}</pre>\n\n⚡ <b>Taken time</b>: <code>{taken_time}</code>",
                reply_parameters=ReplyParameters(message_id=message_id),
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            error = e.message
            if "Can't parse entities" in error:
                await bot.send_message(
                    chat_id=chat_id,
                    text=msg,
                    reply_parameters=ReplyParameters(message_id=message_id),
		)


@Command('logs')
@devs_only
async def SendLogs(update, context):
    '''
    Info: 
       To send a bot logging.
    '''
    message = update.effective_message
    stime = time.time()
    bot = context.bot
    cmd = 'tail logs.txt'
    logs = subprocess.getoutput(cmd)
    logs = html.escape(logs)
    
    return await send(logs, cmd, stime, bot, update, message.message_id)
         


@Command(('e', 'eval'))
@devs_only
async def evaluate(update, context):
  
    message = update.effective_message
    stime = time.time()
    if len(message.text.split()) < 2:
        return await message.reply_text(
          "**🕵️ Provide code execute...**"
       )

    bot = context.bot
    stdout = io.StringIO()
        

    cmd = message.text.split(maxsplit=1)[1]
  
    r = message.reply_to_message
    m = message
    message_id = m.message_id
        
    ruser = getattr(r, 'from_user', None)
    my = getattr(message, 'from_user', None)
    chat = getattr(message, 'chat', None)

    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    redirected_error = sys.stderr = io.StringIO()
    stdout, stderr, exc = None, None, None
  
    try:
       await aexec(
         
		            code=cmd, 
                context=context,
            		bot=bot,
                update=update,
	            	m=message, 
            		r=r,
	            	chat=chat,
	            	message=message,
		            ruser=ruser,
	            	my=my
         
       )
    except Exception as e:
        exc = traceback.format_exc()

    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
  
    sys.stdout = old_stdout
    sys.stderr = old_stderr
  
    evaluation = ""
  
    if exc:
        evaluation = exc
    elif stderr:
        evaluation = stderr
    elif stdout:
        evaluation = stdout
    else:
        evaluation = "Success"
      
    output = evaluation.strip()
    await send(output, cmd, stime, bot, update, message_id)

  
    
@Command(('sh','shell'))
@devs_only
async def shell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    bot = context.bot
    stime = time.time()
    message = update.effective_message
    chat = update.effective_chat

    message_id = message.message_id
        
    if not len(message.text.split()) >= 2:
       return await message.reply_text(
          "🕵️ Provide code execute..."
       )
    code = message.text.split(maxsplit=1)[1]
    try:
       output = subprocess.getoutput(code)
    except Exception as e:
       output = traceback.format_exc()
    await send(
	    output,
	    code, 
	    stime,
	    bot,
	    update,
	    message_id
    )

from pyrogram.types import LinkPreviewOptions, Message
from AloneX import pbot, database as db 
from pyrogram import filters, types, enums
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
# ---------- Execution Function ----------

async def pyroaexec(code, bot, message, m, r, chat, ruser, my):
    exec(
        "async def __pyroaexec(bot, message, m, r, chat, ruser, my): "
        + "".join(f"\n {l_}" for l_ in code.split("\n"))
    )
    return await locals()["__pyroaexec"](bot, message, m, r, chat, ruser, my)


# ---------- Paste Service ----------

async def paste(text: str) -> dict:
    """Simple paste service with fallback"""
    if not text:
        return {"error": "No content"}
    # Mock paste service - replace with actual implementation
    return {
        "paste_url": f"https://hastebin.com/raw/{random.randint(1000, 9999)}",
        "success": True
    }


def get_as_document(content: str) -> BytesIO:
    """Convert string to document file"""
    file = BytesIO(content.encode('utf-8'))
    file.name = "output.txt"
    file.seek(0)
    return file


# ---------- Main Command ----------

@pbot.on_message(filters.user(config.DEV_LIST) & filters.command(['pe', 'peval']))
async def pyroevaluate(bot: pbot, message: types.Message):
    from pyrogram import types, enums, filters
    
    message = m = message
    stime = time.time()
    
    if len(message.text.split()) < 2:
        return await message.reply_text("💻 **Provide code to execute...**")

    msg = await message.reply("💻 **Executing code...**")
    cmd = message.text.split(maxsplit=1)[1]
    
    r = m.reply_to_message
    message_id = m.id
    
    ruser = getattr(r, 'from_user', None)
    my = getattr(m, 'from_user', None)
    chat = getattr(m, 'chat', None)

    # Capture stdout and stderr
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    redirected_error = sys.stderr = io.StringIO()
    stdout, stderr, exc = None, None, None

    try:
        await pyroaexec(
            code=cmd,
            bot=bot,
            message=message,
            m=message,
            r=r,
            chat=chat,
            ruser=ruser,
            my=my
        )
    except Exception as e:
        exc = traceback.format_exc()

    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()

    # Restore stdout and stderr
    sys.stdout = old_stdout
    sys.stderr = old_stderr

    # Determine output
    evaluation = ""
    if exc:
        evaluation = exc
    elif stderr:
        evaluation = stderr
    elif stdout:
        evaluation = stdout
    else:
        evaluation = "**Success** ✅"

    output = evaluation.strip()
    taken_time = round(time.time() - stime, 3)

    # Handle large output
    if len(output) > 4000:
        if len(cmd) > 1000:
            _paste = await paste(cmd)
            if 'error' in _paste:
                caption = "**💻 Paste link not available at the moment.**"
            else:
                caption = f"**💻 Code**: {_paste['paste_url']}\n\n⚡ **Taken time**: `{taken_time}s`"
        else:
            caption = f"**💻 Command**:\n```python\n{cmd}\n```\n\n⚡ **Taken time**: `{taken_time}s`"

        file = get_as_document(output)
        await msg.delete()
        await m.reply_document(file, caption=caption)
    else:
        # Format output
        if output == "**Success** ✅":
            formatted_output = output
        else:
            formatted_output = f"```\n{output}\n```"

        await msg.edit_text(
            text=(
                f"**💻 Command**:\n```python\n{cmd}\n```"
                f"\n\n**📤 Output**:\n{formatted_output}"
                f"\n\n⚡ **Taken Time**: `{taken_time}s`"
            ),
            parse_mode=enums.ParseMode.MARKDOWN
		)
