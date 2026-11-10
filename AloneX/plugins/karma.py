import re
import html
from pyrogram import filters, enums
from pyrogram.types import Message
from AloneX import pbot, prefix_cmds, DEV_LIST, font
from AloneX.db.karma import (
    get_karma_status,
    set_karma_status,
    get_user_karma,
    change_karma,
    get_leaderboard
)

__module__ = "𝐊ᴀʀᴍᴀ✨"
__help__ = """
*Karma System✨*

*Description:*
Karma system for groups where members can upvote or downvote each other based on their contributions.

*Upvote Keywords:*
`+`, `+1`, `thanks`, `good`, `agree`, `👍`, etc.
*Downvote Keywords:*
`-`, `-1`, `bad`, `disagree`, `👎`, etc.

*Commands:*
❂ `/karma` – Reply to a user to check their karma, or send alone for leaderboard
❂ `/karmatoggle [enable|disable]` – Enable or Disable Karma System (Admins Only)

*Note:* You cannot upvote/downvote yourself.
"""

regex_upvote = r"^(\++|\+1|thx|tnx|tq|ty|thankyou|thank you|thanx|thanks|pro|cool|good|agree|👍|\++ .+)$"
regex_downvote = r"^(-+|-1|not cool|disagree|worst|bad|👎|-+ .+)$"

async def is_admin(chat_id: int, user_id: int):
    if user_id in DEV_LIST:
        return True
    try:
        member = await pbot.get_chat_member(chat_id, user_id)
        return member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
    except:
        return False

@pbot.on_message(
    filters.text
    & filters.group
    & filters.incoming
    & filters.reply
    & filters.regex(regex_upvote, re.IGNORECASE)
    & ~filters.via_bot
    & ~filters.bot,
    group=11
)
async def upvote(_, message: Message):
    if not await get_karma_status(message.chat.id):
        return
    if not message.reply_to_message.from_user:
        return
    if not message.from_user:
        return
    if message.reply_to_message.from_user.id == message.from_user.id:
        return

    chat_id = message.chat.id
    user_id = message.reply_to_message.from_user.id
    user_mention = message.reply_to_message.from_user.mention

    new_karma = await change_karma(chat_id, user_id, 1)
    await message.reply_text(
        f"Incremented Karma of {user_mention} By 1 \nTotal Points: {new_karma}"
    )

@pbot.on_message(
    filters.text
    & filters.group
    & filters.incoming
    & filters.reply
    & filters.regex(regex_downvote, re.IGNORECASE)
    & ~filters.via_bot
    & ~filters.bot,
    group=12
)
async def downvote(_, message: Message):
    if not await get_karma_status(message.chat.id):
        return
    if not message.reply_to_message.from_user:
        return
    if not message.from_user:
        return
    if message.reply_to_message.from_user.id == message.from_user.id:
        return

    chat_id = message.chat.id
    user_id = message.reply_to_message.from_user.id
    user_mention = message.reply_to_message.from_user.mention

    new_karma = await change_karma(chat_id, user_id, -1)
    await message.reply_text(
        f"Decremented Karma of {user_mention} By 1 \nTotal Points: {new_karma}"
    )

@pbot.on_message(filters.command("karma", prefix_cmds) & filters.group)
async def command_karma(_, message: Message):
    chat_id = message.chat.id

    if not message.reply_to_message:
        m = await message.reply_text(font("Analyzing Karma Leaderboard..."))
        leaderboard = await get_leaderboard(chat_id, limit=15)

        if not leaderboard:
            return await m.edit("No karma data found for this chat.")

        output = f"✨ **Karma Leaderboard for {html.escape(message.chat.title)}**\n\n"
        for i, (user_id, karma_count) in enumerate(leaderboard, 1):
            try:
                user = await pbot.get_users(user_id)
                user_name = user.first_name if user.first_name else "Deleted User"
            except:
                user_name = f"User {user_id}"
            output += f"{i}. {user_name} — `{karma_count}`\n"

        await m.edit(output)

    else:
        if not message.reply_to_message.from_user:
            return await message.reply("Anonymous users don't have karma.")

        user_id = message.reply_to_message.from_user.id
        user_name = message.reply_to_message.from_user.first_name
        karma_value = await get_user_karma(chat_id, user_id)
        await message.reply_text(f"✨ **{user_name}** has `{karma_value}` karma points.")

@pbot.on_message(filters.command("karmatoggle", prefix_cmds) & filters.group)
async def karmatoggle(_, message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ Admins only."))

    usage = "**Usage:**\n`/karmatoggle [enable|disable]`"
    if len(message.command) != 2:
        return await message.reply_text(usage)

    state = message.command[1].lower()
    if state == "enable":
        await set_karma_status(message.chat.id, True)
        await message.reply_text(font("✅ Enabled Karma System for this chat."))
    elif state == "disable":
        await set_karma_status(message.chat.id, False)
        await message.reply_text(font("❌ Disabled Karma System for this chat."))
    else:
        await message.reply_text(usage)
