from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import ChatAdminRequired, PeerIdInvalid, ChannelInvalid
from AloneX import pbot, DEV_LIST, font
from AloneX import database2 as database

collection = database["chats"]

@pbot.on_message(filters.command("generatelink", prefixes=["/", "!"]) & filters.user(DEV_LIST))
async def generate_link_cmd(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Usage: `/generatelink -100xxxxxxxxxx`", quote=True
        )

    try:
        chat_id = int(message.command[1])
    except ValueError:
        return await message.reply_text(font("❌ Invalid chat ID format."), quote=True)

    chat = await collection.find_one({"chat_id": chat_id})
    if not chat:
        return await message.reply_text(font("⚠️ Chat not found in database."), quote=True)

    # Public chat link (if username exists)
    if chat.get("chat_username"):
        username = chat["chat_username"].lstrip("@")
        return await message.reply_text(f"🔗 **Public Link:**\nhttps://t.me/{username}", quote=True)

    # Try to generate private invite link
    try:
        link = await pbot.export_chat_invite_link(chat_id)
        return await message.reply_text(f"🔗 **Invite Link:**\n{link}", quote=True)

    except ChatAdminRequired:
        return await message.reply_text(font("🚫 The bot must be an **admin** in this chat."), quote=True)

    except PeerIdInvalid:
        return await message.reply_text(font("🚫 The bot is not a member of that chat."), quote=True)

    except ChannelInvalid:
        return await message.reply_text(font("🚫 Invalid channel or chat ID."), quote=True)

    except Exception:
        return await message.reply_text(font("❌ Unexpected error while creating link."), quote=True)
