
from pyrogram import filters, enums
from AloneX import pbot as bot, font
from AloneX.helpers.utils import auto_delete

# add your chat ids here
chats = [
    -1001717881477
]

# channel or group ( username or chat id ) to force to join there
FORCE_CHAT_ID = "fomouschill"  # must add your bot as admin there

users = {}


TIME = 3*60 # time for auto delete message

async def checker(user_id):
    try:
        member = await bot.get_chat_member(FORCE_CHAT_ID, user_id)
        return True
    except Exception:
        member = False
    
    

@bot.on_message(group=-888)
async def force_to_join(_, message):
    m = message
    chat = m.chat
    user = m.from_user
    if chat.id in chats and chat.type == enums.ChatType.SUPERGROUP:
        try:
            member = await chat.get_member(bot.me.id)
            member.privileges.can_restrict_members
        except Exception:
           msg = await m.reply_text(font('❌ **I need administrative rights to manage members in this group!**'))
           return await auto_delete(msg, TIME)
              
        if not (await checker(user.id)):
            unique_id = chat.id + user.id
              
            count = users.get(unique_id, 1)
            
            if count >= 3:
                try:
                    await bot.ban_chat_member(chat.id, user.id)
                    await bot.unban_chat_member(chat.id, user.id)
                    await m.reply_text(
                       f"🚫 **{user.mention} has been removed from the group for not following the channel subscription requirement**."
                    )
                except Exception as err:
                    msg = await m.reply_text(
                        f"**❌ ERROR when removing user {user.mention}**: `{err}`"
                    )
                    await auto_delete(msg, TIME)
                  
                del users[unique_id]     
                return #stop

          
            users[unique_id] = count + 1
            msg = await m.reply_text(
                f"👋 **Hi {user.mention}**!\n\n"
                f"📢 **To continue chatting in this group, please join our channel first.**\n"
                f"📍 **Channel**: {FORCE_CHAT_ID}\n\n"
                f"⚠️ **Warning** {count}/3\n"
                f"❗️ **You'll be removed from the group if you don't join after 3 warnings.**"
            )
          
            await auto_delete(msg, TIME)
            return #stop
