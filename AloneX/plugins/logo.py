__module__ = "𝐋ᴏɢᴏ⛔"

__help__ = """
❂ *Logo Commands*:

❂ `/logo <text>`  
Generate a custom logo image from your text. Use a semicolon `;` to split upper and lower text.  
Example: `/logo AloneX ; Ackerman`

❂ *Inline Buttons* (after logo is generated):
🎨 **Image 🔂** — Change the background image.  
🔠 **Font 🔂** — Change the font.  
🔁 **Change Logo 🔂** — Randomize both image and font.  

❂ *Notes:📝*  
- Only the user who generated the logo can use the inline buttons.  
- Session expires after some time, so act quickly!  
- Powered by AloneX Bot.
"""
import os
import random
import filecmp
from uuid import uuid4
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from pyrogram.enums import ButtonStyle

from AloneX import pbot, BOT_USERNAME, font

FONT_FOLDER = "./AloneX/helpers/font"
IMG_FOLDER = "./AloneX/helpers/images"

allFonts = [f for f in os.listdir(FONT_FOLDER) if f.lower().endswith((".ttf", ".otf"))]

cooldowns = {}  # For spam prevention
session_cache = {}  # Cache per user/session


def genlogo(text: str, image: str = None, tfont: str = None):
    upper_text, lower_text = (text.split(";", 1) + [""])[:2]
    upper_text, lower_text = upper_text.strip(), lower_text.strip()

    bg_files = [f for f in os.listdir(IMG_FOLDER) if f.endswith(".jpg")]
    font_file = tfont if tfont and tfont in allFonts else random.choice(allFonts)
    bg_file = f"{image}.jpg" if image and f"{image}.jpg" in bg_files else random.choice(bg_files)

    img = Image.open(os.path.join(IMG_FOLDER, bg_file))
    blueimg = img.filter(ImageFilter.BoxBlur(1))
    draw = ImageDraw.Draw(blueimg)
    img_size = blueimg.size
    font_path = os.path.join(FONT_FOLDER, font_file)

    # Upper text
    if upper_text:
        font_size = int(img_size[1] / 5)
        font = ImageFont.truetype(font_path, font_size)
        while font.getbbox(upper_text)[2] > img_size[0] - 100 and font_size > 10:
            font_size -= 1
            font = ImageFont.truetype(font_path, font_size)
        x = (img_size[0] - font.getbbox(upper_text)[2]) / 2
        y = (img_size[1] - font.getbbox(upper_text)[3]) / 1.9
        draw.text((x, y), upper_text, font=font, fill="white", stroke_width=1, stroke_fill="black")

    # Lower text
    if lower_text:
        font_size = int(img_size[1] / 14)
        font = ImageFont.truetype(font_path, font_size)
        while font.getbbox(lower_text)[2] > img_size[0] - 100 and font_size > 10:
            font_size -= 1
            font = ImageFont.truetype(font_path, font_size)
        x = (img_size[0] - font.getbbox(lower_text)[2]) / 2
        y = (img_size[1] - font.getbbox(lower_text)[3]) / 1.4
        draw.text((x, y), lower_text, font=font, fill="white", stroke_width=2, stroke_fill="black")

    out_file = f"temp_logo_{random.randint(1000, 999999)}.png"
    blueimg.save(out_file, "PNG")
    return out_file, bg_file, font_file


@pbot.on_message(filters.command("logo"))
async def logo_handler(client, message: Message):
    if not message.from_user:
        return await message.reply(font("❌ Anonymous admin detected. Please use from a real account."))

    if len(message.command) < 2:
        return await message.reply(
            "❌ Provide some text to generate logo.\n\n**Example:** `/logo AloneX ; Ackerman`",
            parse_mode=ParseMode.MARKDOWN
        )

    name = message.text.split(None, 1)[1]
    loading = await message.reply(font("🎨 Generating your logo..."))

    try:
        path, bg_file, font_file = genlogo(name)
        key = os.path.splitext(bg_file)[0]
        user_id = message.from_user.id
        session_id = uuid4().hex[:10]

        session_cache[session_id] = {
            "name": name,
            "font": font_file,
            "key": key,
            "owner": user_id
        }

        buttons = [
            [
                InlineKeyboardButton(font("🎨 Image 🔂"), callback_data=f"flogo|{session_id}", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(font("🔠 Font 🔂"), callback_data=f"ilogo|{session_id}", style=ButtonStyle.PRIMARY),
            ],
            [InlineKeyboardButton(font("🔁 Change Logo 🔂"), callback_data=f"slogo|{session_id}", style=ButtonStyle.SUCCESS)]
        ]

        await message.reply_photo(
            photo=path,
            caption=f"Powered by {BOT_USERNAME}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        os.remove(path)
        await loading.delete()

    except Exception as e:
        await loading.edit(f"❌ Logo generation failed:\n<code>{e}</code>", parse_mode=ParseMode.HTML)


@pbot.on_callback_query(filters.regex(r"^(flogo|ilogo|slogo)\|"))
async def logo_callback(client, cb: CallbackQuery):
    if not cb.from_user:
        return await cb.answer(font("❌ Anonymous admin not supported."), show_alert=True)

    try:
        action, session_id = cb.data.split("|", 1)
        session = session_cache.get(session_id)

        if not session:
            return await cb.answer(font("❌ Session expired."), show_alert=True)

        if cb.from_user.id != session["owner"]:
            return await cb.answer(font("❌ This session is not yours."), show_alert=True)

        cooldown_key = (cb.message.chat.id, cb.message.id, action)
        now = datetime.now()
        if cooldown_key in cooldowns and cooldowns[cooldown_key] > now:
            wait = int((cooldowns[cooldown_key] - now).total_seconds())
            return await cb.answer(f"⏳ Wait {wait}s before retrying.", show_alert=True)

        cooldowns[cooldown_key] = now + timedelta(seconds=5)

        name = session["name"]
        current_font = session["font"]
        current_key = session["key"]

        bg_files = [f for f in os.listdir(IMG_FOLDER) if f.endswith(".jpg")]

        if action == "flogo":
            key = os.path.splitext(random.choice(bg_files))[0]
            font = current_font
        elif action == "ilogo":
            font = random.choice([f for f in allFonts if f != current_font])
            key = current_key
        else:
            font = random.choice(allFonts)
            key = os.path.splitext(random.choice(bg_files))[0]

        path, bg_file, font_file = genlogo(name, key, font)
        new_key = os.path.splitext(bg_file)[0]

        temp_path = f"oldcb_{random.randint(1000,9999)}.jpg"
        try:
            await cb.message.download(temp_path)
            same = os.path.exists(temp_path) and filecmp.cmp(path, temp_path, shallow=False)
            os.remove(temp_path)
        except:
            same = False

        if same:
            os.remove(path)
            return await cb.answer(font("⚠️ Already showing this logo."), show_alert=True)

        session_cache[session_id] = {
            "name": name,
            "font": font_file,
            "key": new_key,
            "owner": cb.from_user.id
        }

        buttons = [
            [
                InlineKeyboardButton(font("🎨 Image 🔂"), callback_data=f"flogo|{session_id}", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(font("🔠 Font 🔂"), callback_data=f"ilogo|{session_id}", style=ButtonStyle.PRIMARY),
            ],
            [InlineKeyboardButton(font("🔁 Change Logo 🔂"), callback_data=f"slogo|{session_id}", style=ButtonStyle.SUCCESS)]
        ]

        await cb.message.edit_media(
            media=InputMediaPhoto(
                media=path,
                caption=f"Powered by {BOT_USERNAME}",
                parse_mode=ParseMode.HTML
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        os.remove(path)
        await cb.answer(font("✅ Logo updated!"))

    except Exception as e:
        print(f"[LOGO CALLBACK ERROR] {e}")
        await cb.answer(font("❌ Something went wrong."), show_alert=True)
