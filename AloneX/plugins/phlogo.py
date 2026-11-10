import asyncio
from AloneX import pbot, font
from pyrogram import filters
from phlogo import generate
import os
from PIL import Image, ImageFont
from pyrogram.enums import ChatAction

__module__ = "𝐏ʜ-𝐋ᴏɢᴏ🎨"
__help__ = """
*PhLogo Commands*:

❂ `/phlogo <text1> <text2>` - Generate PornHub style logo
❂ `/phst <text1> <text2>` - Generate PornHub style sticker

*Example*:
`/phlogo Alone Bot`
"""

original_getsize = getattr(ImageFont.FreeTypeFont, 'getsize', None)
if original_getsize is None:
    def getsize_replacement(self, text):
        bbox = self.getbbox(text)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])
    ImageFont.FreeTypeFont.getsize = getsize_replacement

@pbot.on_message(filters.command("phlogo") & ~filters.forwarded, group=-888)
async def phlogo(b, m):
    await b.send_chat_action(m.chat.id, ChatAction.UPLOAD_PHOTO)
    try:
        text = m.text.split(maxsplit=2)
        if len(text) < 3:
            return await m.reply_text(font("**Example:**\n\n`/phlogo text1 text2`"))
        firs_name = text[1]
        last_name = text[2]
        result = generate(firs_name, last_name)
    except Exception as e:
        return await m.reply_text(f"**Error:** {str(e)}")
    try:
        result.save("sahil.png")
        x = Image.open("sahil.png")
        x.save("sahil.png")
        x.close()
        await m.reply_photo("sahil.png")
        if os.path.exists("sahil.png"):
            os.remove("sahil.png")
    except Exception as e:
        if os.path.exists("sahil.png"):
            os.remove("sahil.png")
        return await m.reply_text(f"**Error:** {str(e)}")

@pbot.on_message(filters.command("phst") & ~filters.forwarded, group=-777)
async def phst(b, m):
    await b.send_chat_action(m.chat.id, ChatAction.UPLOAD_PHOTO)
    try:
        text = m.text.split(maxsplit=2)
        if len(text) < 3:
            return await m.reply_text(font("**Example:**\n\n`/phst text1 text2`"))
        firs_name = text[1]
        last_name = text[2]
        result = generate(firs_name, last_name)
    except Exception as e:
        return await m.reply_text(f"**Error:** {str(e)}")
    try:
        result.save("sahil.png")
        x = Image.open("sahil.png")
        r, g, b = x.split()
        x = Image.merge("RGB", (b, g, r))
        sticker_size = (512, 512)
        x.thumbnail(sticker_size)
        x.save("sahil.WEBP", "WEBP")
        x.close()
        await m.reply_sticker("sahil.WEBP")
        if os.path.exists("sahil.WEBP"):
            os.remove("sahil.WEBP")
        if os.path.exists("sahil.png"):
            os.remove("sahil.png")
    except Exception as e:
        if os.path.exists("sahil.WEBP"):
            os.remove("sahil.WEBP")
        if os.path.exists("sahil.png"):
            os.remove("sahil.png")
        return await m.reply_text(f"**Error:** {str(e)}")
