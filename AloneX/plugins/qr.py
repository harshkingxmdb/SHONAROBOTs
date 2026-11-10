
from pyrogram import types, filters
from AloneX import pbot as bot, font
from urllib.parse import quote

import aiohttp
import os


__module__ = "𝐐ʀ📱"

__help__ = """
*Commands*:
/createqr, /readqr

*Description:*  
Generate or read QR codes directly in Telegram.

*Usage:*  
❂ `/createqr` — Reply to a text message or provide text to generate a QR code  
❂ `/readqr` — Scan and decode a QR code from an image

*Example:*  
`/createqr Hello World`  
`/readqr` (reply to a QR code image)
"""
@bot.on_message(filters.command("readqr") & ~filters.forwarded, group=-555)
async def readqr(c, m):
    if not m.reply_to_message:
        return await m.reply(font("Please reply with a photo that contains a valid QR Code."))
    if not m.reply_to_message.photo:
        return await m.reply(font("Please reply with a photo that contains a valid QR Code."))
    
    # Download the photo
    foto = await m.reply_to_message.download()
    
    try:
        # Prepare the file for upload
        async with aiohttp.ClientSession() as session:
            url = "http://api.qrserver.com/v1/read-qr-code/"
            
            # Create multipart form data
            data = aiohttp.FormData()
            data.add_field('file', 
                           open(foto, 'rb'), 
                           filename=os.path.basename(foto))
            
            # Post the request
            async with session.post(url, data=data) as r:
                # Check the response
                response = await r.json()
                data = response[0]["symbol"][0]["data"]
                
                if data is None:
                    return await m.reply_text(font("Could not read the QR code."))
                
                await m.reply_text(
                    f"<b>QR Code Reader by @{c.me.username}:</b> <code>{data}</code>",
                    quote=True,
                )
    
    except Exception as e:
        await m.reply_text(f"An error occurred: {str(e)}")
    
    finally:
        # Remove the downloaded photo
        if os.path.exists(foto):
            os.remove(foto)



@bot.on_message(filters.command("createqr") & ~filters.forwarded, group=-444)
async def makeqr(c, m):
    if m.reply_to_message and m.reply_to_message.text:
        teks = m.reply_to_message.text
    elif len(m.command) > 1:
        teks = m.text.split(None, 1)[1]
    else:
        return await m.reply(
            "Please add text after command or reply to text to convert text -> QR Code."
        )
    
    # URL encode the text to handle special characters
    encoded_text = quote(teks)
    
    # QR Code generation API URL
    url = f"https://api.qrserver.com/v1/create-qr-code/?data={encoded_text}&size=300x300"
    
    await m.reply_photo(
        url, caption=f"<b>QR Code Maker by @{c.me.username}</b>", quote=True
    )
