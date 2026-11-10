from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import ChatAdminRequired, UserNotParticipant, ChannelPrivate, BadRequest

from AloneX import pbot as app, font
from AloneX import OWNER_ID
from AloneX.db.blchats import add_blchat, rm_blchat, is_blchat, get_all_blchats
from AloneX.helpers.pyro_utils import is_admin

__module__ = "𝐁ʟ-𝐂ʜᴀᴛs❌"

__help__ = """
*Bl-Chats*

*Description:*  
Manage chats that are blacklisted. Only developers can use these commands.

*Commands (Dev-only):*  
❂ `/blchat <chat_id>` – Blacklist a chat and leave immediately  
❂ `/unblchat <chat_id>` – Remove a chat from the blacklist  
❂ `/blchats` – Show all blacklisted chats
"""

# Sudoers check
SUDOERS = filters.user(OWNER_ID)

@app.on_message(filters.command(["blchat", "blacklistchat"]) & SUDOERS)
async def blacklist_chat_func(client, message: Message):
    try:
        if len(message.command) != 2:
            return await message.reply_text(font("⚠️ **Usage:** `/blchat <chat_id>`"))
        
        try:
            chat_id = int(message.text.strip().split()[1])
        except ValueError:
            return await message.reply_text(font("⚠️ **Invalid chat ID!**"))
        
        # Check if already blacklisted
        if await is_blchat(chat_id):
            return await message.reply_text(f"🚫 **Chat `{chat_id}` is already blacklisted!**")
        
        # Add to blacklist
        blacklisted = await add_blchat(chat_id)
        if not blacklisted:
            return await message.reply_text(font("❌ **Failed to blacklist chat!**"))
            
        await message.reply_text(f"✅ **Chat `{chat_id}` has been blacklisted!**")
        
        # Try to leave chat
        try:
            await app.leave_chat(chat_id)
            await message.reply_text(f"🚪 **Left chat `{chat_id}`**")
        except ChannelPrivate:
            await message.reply_text(f"⚠️ **Bot is not in chat `{chat_id}`**")
        except Exception:
            await message.reply_text(f"⚠️ **Couldn't leave chat `{chat_id}` - bot not in chat**")
    except Exception as e:
        print(f"blchat error: {e}")

@app.on_message(filters.command(["whitelistchat", "unblacklistchat", "unblchat"]) & SUDOERS)
async def whitelist_chat_func(client, message: Message):
    try:
        if len(message.command) != 2:
            return await message.reply_text(font("⚠️ **Usage:** `/unblchat <chat_id>`"))
        
        try:
            chat_id = int(message.text.strip().split()[1])
        except ValueError:
            return await message.reply_text(font("⚠️ **Invalid chat ID!**"))
        
        # Check if blacklisted
        if not await is_blchat(chat_id):
            return await message.reply_text(f"✅ **Chat `{chat_id}` is not blacklisted!**")
        
        # Remove from blacklist
        whitelisted = await rm_blchat(chat_id)
        if whitelisted:
            return await message.reply_text(f"♻️ **Chat `{chat_id}` has been removed from blacklist!**")
        
        await message.reply_text(font("❌ **Failed to remove chat from blacklist!**"))
    except Exception as e:
        print(f"unblchat error: {e}")

@app.on_message(filters.command(["blchats", "blacklistedchats"]) & SUDOERS)
async def all_blacklisted_chats(client, message: Message):
    try:
        chats = await get_all_blchats()
        
        if not chats:
            return await message.reply_text(font("📭 **No blacklisted chats found!**"))
        
        text = "🚫 **Blacklisted Chats:**\n\n"
        
        for count, chat_id in enumerate(chats, 1):
            try:
                chat = await app.get_chat(chat_id)
                title = chat.title or "ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ"
            except:
                title = "ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ"
            
            text += f"{count}. **{title}** [`{chat_id}`]\n"
        
        await message.reply_text(text)
    except Exception as e:
        print(f"blchats error: {e}")

# Auto leave handler for blacklisted chats
@app.on_message(filters.group, group=999)
async def check_blacklist_and_leave(client, message: Message):
    try:
        chat_id = message.chat.id
        
        # Check if chat is blacklisted
        if await is_blchat(chat_id):
            try:
                await app.leave_chat(chat_id)
                print(f"Left blacklisted chat: {chat_id}")
            except Exception as e:
                print(f"Failed to leave blacklisted chat {chat_id}: {e}")
    except:
        pass

# Auto leave when bot is added to blacklisted chat
@app.on_chat_member_updated()
async def member_update_handler(client, chat_member_updated):
    try:
        # Check if bot was added to a chat
        if (chat_member_updated.old_chat_member and 
            chat_member_updated.new_chat_member and
            chat_member_updated.new_chat_member.user.id == app.me.id):
            
            old_status = chat_member_updated.old_chat_member.status
            new_status = chat_member_updated.new_chat_member.status
            
            # Bot was added (from left/kicked to member/admin)
            if (old_status in ["left", "kicked"] and 
                new_status in ["member", "administrator"]):
                
                chat_id = chat_member_updated.chat.id
                
                # Check if chat is blacklisted
                if await is_blchat(chat_id):
                    try:
                        await app.leave_chat(chat_id)
                        print(f"Left blacklisted chat after being added: {chat_id}")
                    except Exception as e:
                        print(f"Failed to leave blacklisted chat after being added {chat_id}: {e}")
    except:
        pass
