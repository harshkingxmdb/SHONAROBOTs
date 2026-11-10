from pyrogram import Client, filters
from pyrogram.types import Message
from AloneX import pbot, font
from AloneX.db import reaction
from AloneX.helpers.pyro_utils import is_admin
import random

REACTION_EMOJIS = ["👍", "❤️", "🔥", "🎉", "😍", "👏", "😂", "🤔", "😎", "💯", "⚡", "🌟", "✨", "💪", "🙌"]

@pbot.on_message(filters.command("reaction") & (filters.group | filters.private))
async def reaction_command(client: Client, message: Message):
    if not message.from_user:
        return
    
    
    if message.chat.type in ["group", "supergroup"]:
        if not await is_admin(message.chat.id, message.from_user.id):
            await message.reply_text(font("❌ This command is only for admins!"))
            return

    
    if len(message.command) == 1:
        status = await reaction.get_reaction_status(message.chat.id)
        status_text = "ᴇɴᴀʙʟᴇᴅ ✅" if status else "ᴅɪꜱᴀʙʟᴇᴅ ❌"
        await message.reply_text(f"**ʀᴇᴀᴄᴛɪᴏɴ ꜱᴛᴀᴛᴜꜱ:** {status_text}")
        return

    arg = message.command[1].lower()
    if arg == "on":
        await reaction.set_reaction_status(message.chat.id, True)
        await message.reply_text("✅ **ʀᴇᴀᴄᴛɪᴏɴꜱ ᴇɴᴀʙʟᴇᴅ!**\n\nʙᴏᴛ ᴡɪʟʟ ʀᴇᴀᴄᴛ ᴡɪᴛʜ ʀᴀɴᴅᴏᴍ ᴇᴍᴏᴊɪ'ꜱ ᴛᴏ ɴᴇᴡ ᴍᴇꜱꜱᴀɢᴇꜱ.")
    elif arg == "off":
        await reaction.set_reaction_status(message.chat.id, False)
        await message.reply_text(font("❌ **ʀᴇᴀᴄᴛɪᴏɴꜱ ᴅɪꜱᴀʙʟᴇᴅ!**"))
    else:
        await message.reply_text(font("❌ Invalid argument! Use: /reaction <on/off>"))

@pbot.on_message((filters.group | filters.private) & ~filters.bot & ~filters.command("reaction"))
async def auto_react(client: Client, message: Message):
    status = await reaction.get_reaction_status(message.chat.id)
    if status:
        try:
            emoji = random.choice(REACTION_EMOJIS)
            await client.send_reaction(
                chat_id=message.chat.id,
                message_id=message.id,
                emoji=emoji
            )
        except Exception:
            pass

__module__ = "𝐑ᴇᴀᴄᴛɪᴏɴ〽️"
__help__ = """
**ʀᴇᴀᴄᴛɪᴏɴꜱ ᴍᴏᴅᴜʟᴇ**

 ✪ /reaction <on/off>: set reaction status
 ✪ /reaction : get current reaction status

ʙᴏᴛ ᴡɪʟʟ ʀᴇᴀᴄᴛ ᴡɪᴛʜ ʀᴀɴᴅᴏᴍ ᴇᴍᴏᴊɪ'ꜱ ᴛᴏ ɴᴇᴡ ᴍᴇꜱꜱᴀɢᴇꜱ

**ᴡᴏʀᴋꜱ ɪɴ ʙᴏᴛʜ ɢʀᴏᴜᴘꜱ & ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛꜱ**
**ᴀᴅᴍɪɴ ᴏɴʟʏ ɪɴ ɢʀᴏᴜᴘꜱ**
"""
