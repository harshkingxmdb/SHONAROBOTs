from telegram import Update, constants
from telegram.ext import ContextTypes, ChatMemberHandler
from AloneX.helpers.decorator import ChatMembers
from AloneX import font
import asyncio

@ChatMembers(chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER)
async def autoleave_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles when the bot's own chat member status changes.
    If the bot is added as a member or demoted to a member, it leaves.
    """
    chat = update.effective_chat
    if not chat or chat.type == constants.ChatType.PRIVATE:
        return

    # Get the new status of the bot
    new_status = update.my_chat_member.new_chat_member.status

    # If bot is added as a member (not admin) or demoted to member
    if new_status == constants.ChatMemberStatus.MEMBER:
        # Give 20 seconds to allow the user to promote the bot if they are using a setup script
        await asyncio.sleep(20)

        try:
            bot_member = await chat.get_member(context.bot.id)
            if bot_member.status == constants.ChatMemberStatus.MEMBER:
                await chat.send_message(font("❌ I am not an admin in this group, so I am leaving. To use me here, add me as an admin!"))
                await context.bot.leave_chat(chat.id)
        except Exception:
            pass
