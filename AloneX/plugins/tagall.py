import asyncio
import re
from telethon import events
from telethon.errors import UserNotParticipantError
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
from AloneX import tbot, prefix_cmds, LOGGER
import logging

__module__ = "𝐓ᴀɢ-𝐀ʟʟ📣"
__help__ = """
❂ *Tag All📣*

❂ *Description:*
Mention all members in your group quickly and efficiently. Useful for important announcements.

❂ *Commands:*
❂ `/tagall` or `@all` — Tag everyone in the group. You can reply to a message or provide text.
❂ `/cancel` — Stop an ongoing tag-all process.

*Note: Only group admins can use these commands.*
"""

spam_chats = []

async def is_admin(chat_id, user_id):
    try:
        partici_ = await tbot(GetParticipantRequest(chat_id, user_id))
        return isinstance(partici_.participant, (ChannelParticipantAdmin, ChannelParticipantCreator))
    except UserNotParticipantError:
        return False
    except Exception:
        return False

async def mentionall(event):
    chat_id = event.chat_id
    if event.is_private:
        return await event.respond("__This command can only be used in groups and channels!__")

    if not await is_admin(chat_id, event.sender_id):
        return await event.respond("__Only admins can mention all!__")

    if event.pattern_match.group(1) and event.is_reply:
        return await event.respond("__Please provide only one argument (either reply or text)!__")

    elif event.pattern_match.group(1):
        mode = "text_on_cmd"
        msg = event.pattern_match.group(1)
    elif event.is_reply:
        mode = "text_on_reply"
        msg = await event.get_reply_message()
        if msg is None:
            return await event.respond("__I can't mention members for older messages!__")
    else:
        return await event.respond("__Reply to a message or give me some text to mention others!__")

    if chat_id in spam_chats:
        return await event.respond("__A tag-all process is already running in this chat. Use /cancel to stop it first.__")

    spam_chats.append(chat_id)
    usrnum = 0
    usrtxt = ""

    try:
        async for usr in tbot.iter_participants(chat_id):
            if chat_id not in spam_chats:
                break

            if usr.bot:
                continue

            usrnum += 1
            usrtxt += f"[{usr.first_name}](tg://user?id={usr.id}), "

            if usrnum == 5:
                if mode == "text_on_cmd":
                    txt = f"{msg}\n\n{usrtxt}"
                    await tbot.send_message(chat_id, txt)
                elif mode == "text_on_reply":
                    await msg.reply(usrtxt)

                await asyncio.sleep(3)
                usrnum = 0
                usrtxt = ""

        if chat_id in spam_chats:
            spam_chats.remove(chat_id)
            if usrtxt:
                if mode == "text_on_cmd":
                    await tbot.send_message(chat_id, f"{msg}\n\n{usrtxt}")
                elif mode == "text_on_reply":
                    await msg.reply(usrtxt)

    except Exception as e:
        LOGGER.error(f"Error in tagall: {e}")
        if chat_id in spam_chats:
            spam_chats.remove(chat_id)

async def cancel_spam(event):
    if event.chat_id not in spam_chats:
        return await event.respond("__There is no tag-all process ongoing in this chat.__")

    if not await is_admin(event.chat_id, event.sender_id):
        return await event.respond("__Only admins can cancel the process!__")

    try:
        spam_chats.remove(event.chat_id)
    except:
        pass
    return await event.respond("__Stopped the mention process successfully.__")

if "tagall" not in tbot.handlers_loaded:
    prefixes = "".join(re.escape(x) for x in prefix_cmds)
    tbot.add_event_handler(mentionall, events.NewMessage(pattern=f"^[{prefixes}]tagall ?(.*)"))
    tbot.add_event_handler(mentionall, events.NewMessage(pattern="^@all ?(.*)"))
    tbot.add_event_handler(cancel_spam, events.NewMessage(pattern=f"^[{prefixes}]cancel$"))
    tbot.handlers_loaded.add("tagall")
