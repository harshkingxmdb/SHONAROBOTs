import aiohttp
import random
import config
import os
from io import BytesIO
from PIL import Image
from pyrogram import filters
from pyrogram.enums import ParseMode
from AloneX import pbot, font

__module__ = "𝐔ᴘsᴄᴀʟᴇʀ🖼️"

__help__ = """
*Upscaler*

*Description:*  
Upscale images to higher resolution by replying to them with commands.

*Commands:*  
❂ `/upscale` – Upscale the image ×4  
❂ `/upscale anime` – Use anime upscaling mode  
❂ `/upscale lvl-high` – Use high resolution compression  
❂ `/upscale anime lvl-high` – Combine both modes

*Example:*  
`/upscale anime lvl-high` (reply to photo)
"""
users = {}

def generate_random_number(min_val: int, max_val: int) -> int:
    return random.randint(min_val, max_val)

async def upscale(buffer: bytes, anime: bool = False, level: str = None) -> str:
    try:
        random_number = generate_random_number(1_000_000, 999_999_999_999)

        with Image.open(BytesIO(buffer)) as img:
            width, height = img.size

        form_data = aiohttp.FormData()
        form_data.add_field("image_file", buffer, filename="image.jpg", content_type="image/jpeg")
        form_data.add_field("name", str(random_number))
        form_data.add_field("desiredHeight", str(height * 4))
        form_data.add_field("desiredWidth", str(width * 4))
        form_data.add_field("outputFormat", "png")
        if level:
            form_data.add_field("compressionLevel", level)
        form_data.add_field("anime", str(anime).lower())

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://upscalepics.com",
            "Referer": "https://upscalepics.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.upscalepics.com/upscale-to-size", data=form_data, headers=headers) as response:
                if response.status == 200:
                    json_response = await response.json()
                    return json_response.get("bgRemoved", "").strip()
                else:
                    raise Exception(f"API Error {response.status}")

    except Exception as e:
        print(f"[Upscale Error] {e}")
        return None

@pbot.on_message(filters.command('upscale') & ~filters.forwarded, group=-77)
async def upscale_func(_, message):
    user = message.from_user
    user_id = user.id if user else None

    if not user_id:
        return await message.reply(font("❌ Unknown user."), parse_mode=ParseMode.HTML)

    if users.get(user_id, False):
        return await message.reply(font('⚠️ <b>You already have an ongoing upscale process.</b>'), parse_mode=ParseMode.HTML)

    users[user_id] = True

    is_photo = message.reply_to_message and message.reply_to_message.photo
    if not is_photo:
        users.pop(user_id, None)
        return await message.reply(font('📷 <b>Reply to a photo to upscale it.</b>'), parse_mode=ParseMode.HTML)

    loading_msg = await message.reply(font('🔄 <b>Upscaling your image...</b>'), parse_mode=ParseMode.HTML)

    path = None
    img_path = None

    try:
        pattern_text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
        anime = "anime" in pattern_text
        level = pattern_text.split('lvl-')[1] if 'lvl-' in pattern_text else None

        path = await message.reply_to_message.download()
        with open(path, 'rb') as img:
            image_buffer = img.read()

        image_url = await upscale(image_buffer, anime=anime, level=level)

        if image_url and image_url.startswith("http"):
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        img_path = f"upscaled_{message.id}.png"
                        with open(img_path, 'wb') as f:
                            f.write(content)

                        await message.reply_document(
                            img_path,
                            caption=f"✨ Upscaled by {config.BOT_USERNAME}",
                        )
                    else:
                        raise Exception("Failed to download upscaled image.")
        else:
            raise Exception("Upscaling failed or bad response URL.")

    except Exception as e:
        await message.reply(f"❌ <b>Error:</b> <code>{e}</code>", parse_mode=ParseMode.HTML)

    finally:
        if path and os.path.exists(path):
            os.remove(path)
        if img_path and os.path.exists(img_path):
            os.remove(img_path)
        if loading_msg:
            await loading_msg.delete()
        users.pop(user_id, None)
