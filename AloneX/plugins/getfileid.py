from pyrogram import filters
import config
from AloneX import pbot

__module__ = "𝐅ɪʟᴇ 𝐈𝐝📎"

__help__ = """
*Commands*:
/fileid — Reply to a video, photo, GIF, or document to get its permanent Telegram file_id.

*Usage:*
Send the video to the bot (or any chat the bot is in), reply to it with /fileid, and copy the string it gives you. Use that in START_IMG / PM_START_IMG (prefix with `video:` for videos).
"""

@pbot.on_message(filters.command("fileid") & filters.user(config.OWNER_ID))
async def get_file_id(client, message):
    target = message.reply_to_message
    if not target:
        return await message.reply_text("❌ Reply to a video, photo, GIF, or document with /fileid.")

    media = target.video or target.photo or target.animation or target.document
    if not media:
        return await message.reply_text("❌ That message doesn't contain a video, photo, GIF, or document.")

    kind = (
        "video" if target.video else
        "photo" if target.photo else
        "animation" if target.animation else
        "document"
    )
    prefix = "video:" if kind in ("video", "animation") else ""

    await message.reply_text(
        f"✅ **{kind.title()} file_id:**\n`{prefix}{media.file_id}`\n\n"
        f"Copy the line above (including `video:` if present) and paste it as your START_IMG / PM_START_IMG value."
    )
