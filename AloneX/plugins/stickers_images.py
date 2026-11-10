from AloneX import font
import math
import aiohttp
import moviepy as mp
import config
import html
import os
import csv
from urllib.parse import quote, quote_plus
from bs4 import BeautifulSoup
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from telegram import helpers, error, InputSticker, InlineKeyboardMarkup, InlineKeyboardButton, constants
from telegram.helpers import escape_markdown
from AloneX.helpers.decorator import Command
from AloneX.helpers.utils import get_media_id, get_ua, cookies_json_to_str as get_cookies, convert_to_jpeg, convert_to_webp
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputSticker
from telegram.ext import ContextTypes


__module__ = "𝐒ᴛɪᴄᴋᴇʀ-𝐈ᴍᴀɢᴇ🎨"

__help__ = """
*Sticker/Image🎨*

*Description:*  
Manage, create, and edit stickers or images directly from your chat. Convert images, apply effects, and more.

*Commands:*  
❂ `/stickers <query>` – Search sticker packs  
❂ `/kang` – Create or add a sticker to your pack (reply to a sticker)  
❂ `/delkang` – Remove a sticker from your pack (reply to sticker)  
❂ `/getsticker` – Convert a sticker to an image  
❂ `/tosticker` – Convert a photo or document to a sticker  
❂ `/togif` – Convert an animated sticker into a GIF  
❂ `/emix <emoji1>+<emoji2>` – Mix two emoji expressions  
❂ `/blur <radius>` – Blur a sticker or image (radius 1—100)  
❂ `/watermark <text:50>` – Add a watermark to sticker or image (reply required)  
❂ `/reverse` – Get information about an image or sticker (reply required)

*Example:*  
`/stickers cute cats`  
`/kang` (reply to sticker)  
`/blur 10` (reply to image)
"""


@Command('kang')
async def CreatOrAddSticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message
    bot = context.bot
    args = context.args
    emoji_arg = None
    sticker_format = constants.StickerFormat.STATIC
    
    if args and len(args[0]) <= 2:
        try:
            import unicodedata
            for char in args[0]:
                if unicodedata.category(char).startswith('So'):
                    emoji_arg = args[0]
                    break
        except:
            pass
    
    if not message.reply_to_message:
        return await message.reply_text(font("🤷 Reply to an image/sticker/gif for kang."))
    
    replied = message.reply_to_message
    is_valid = False
    is_animated = False
    is_video = False
    
    if replied.sticker:
        is_valid = True
        if replied.sticker.is_animated:
            is_animated = True
            sticker_format = constants.StickerFormat.ANIMATED
        elif replied.sticker.is_video:
            is_video = True
            sticker_format = constants.StickerFormat.VIDEO
    elif replied.photo:
        is_valid = True
    elif replied.document:
        mime = replied.document.mime_type
        if mime in ('image/png', 'image/jpeg', 'image/jpg', 'image/webp'):
            is_valid = True
        elif mime == 'image/gif' or mime == 'video/mp4':
            is_valid = True
            is_video = True
            sticker_format = constants.StickerFormat.VIDEO
    elif replied.animation:
        is_valid = True
        is_video = True
        sticker_format = constants.StickerFormat.VIDEO
    
    if not is_valid:
        return await message.reply_text(font("🤷 Reply to a valid image/sticker/gif for kang."))
    
    if emoji_arg:
        import unicodedata
        try:
            emoji_name = ''.join([unicodedata.name(char).replace(' ', '_').replace('-', '_').lower() for char in emoji_arg if unicodedata.category(char).startswith('So')])
            pack_name = f"User{user.id}_{emoji_name}_by_{bot.username}"
            pack_title = f"{user.first_name}'s {emoji_arg} Stickers"
        except:
            pack_name = f"User{user.id}_custom_by_{bot.username}"
            pack_title = f"{user.first_name}'s {emoji_arg} Stickers"
    else:
        pack_name = f"User{user.id}_by_{bot.username}"
        pack_title = f"{user.first_name}'s Stickers"
    
    pack_link = f"https://t.me/addstickers/{pack_name}"
    
    sticker_file = None
    file_path = None
    
    try:
        file_id = get_media_id(replied)
        if not file_id[1]:
            return await message.reply_text(font("❌ Cannot get media file."))
        
        file = await bot.get_file(file_id[1])
        
        if is_animated:
            file_path = await file.download_to_drive(f'Sticker_{user.id}_{message.id}.tgs')
        elif is_video:
            file_path = await file.download_to_drive(f'Sticker_{user.id}_{message.id}.webm')
        else:
            file_path = await file.download_to_drive(f'Sticker_{user.id}_{message.id}.png')
            convert_to_webp(file_path)
        
        sticker_file = file_path
    except Exception as e:
        return await message.reply_text(f"❌ Error downloading media: {str(e)}")
    
    if emoji_arg:
        sticker_emoji = emoji_arg
    elif replied.sticker and replied.sticker.emoji:
        sticker_emoji = replied.sticker.emoji
    else:
        import random
        emoji_list = ["😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😆", "😉", "😊", "😋", "😎", "😍", "😘", "🥰", "😗", "😙", "😚", "🙂", "🤗", "🤩", "🤔", "🤨", "😐", "😑", "😶", "🙄", "😏", "😣", "😥", "😮", "🤐", "😯", "😪", "😫", "😴", "😌", "😛", "😜", "😝", "🤤", "😒", "😓", "😔", "😕", "🙃", "🤑", "😲", "☹️", "🙁", "😖", "😞", "😟", "😤", "😢", "😭", "😦", "😧", "😨", "😩", "🤯", "😬", "😰", "😱", "🥵", "🥶", "😳", "🤪", "😵", "😡", "😠", "🤬", "😷", "🤒", "🤕", "🤢", "🤮", "🤧", "😇", "🤠", "🤡", "🥳", "🥴", "🥺", "🤥", "🤫", "🤭", "🧐", "🤓", "😈", "👿", "👹", "👺", "💀", "👻", "👽", "🤖", "💩", "😺", "😸", "😹", "😻", "😼", "😽", "🙀", "😿", "😾"]
        sticker_emoji = random.choice(emoji_list)
    
    msg = await message.reply_text(font("✨ *Kanging the sticker....*"), parse_mode=constants.ParseMode.MARKDOWN)
    
    pack_exists = False
    try:
        sticker_set = await bot.get_sticker_set(pack_name)
        pack_exists = True
    except error.BadRequest as e:
        if "Stickerset_invalid" in str(e):
            pack_exists = False
        else:
            if sticker_file and os.path.exists(sticker_file):
                os.remove(sticker_file)
            return await msg.edit_text(f"❌ Error: {str(e)}")
    except Exception as e:
        if sticker_file and os.path.exists(sticker_file):
            os.remove(sticker_file)
        return await msg.edit_text(f"❌ Error: {str(e)}")
    
    if not pack_exists:
        try:
            with open(sticker_file, 'rb') as sticker_data:
                done = await bot.create_new_sticker_set(
                    user_id=user.id,
                    name=pack_name,
                    title=pack_title,
                    stickers=[
                        InputSticker(
                            sticker=sticker_data,
                            emoji_list=[sticker_emoji],
                            format=sticker_format
                        )
                    ]
                )
            if sticker_file and os.path.exists(sticker_file):
                os.remove(sticker_file)
            if done:
                return await msg.edit_text(
                    text=f"⚡ *Successfully Created New Sticker Pack!*\n\n🎭 Emoji: {sticker_emoji}",
                    parse_mode=constants.ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(font('🧏 Sticker Pack'), url=pack_link)
                    ]])
                )
        except Exception as e:
            if sticker_file and os.path.exists(sticker_file):
                os.remove(sticker_file)
            return await msg.edit_text(text=f"❌ Error while creating new pack: {str(e)}")
    
    try:
        with open(sticker_file, 'rb') as sticker_data:
            done = await bot.add_sticker_to_set(
                user_id=user.id,
                name=pack_name,
                sticker=InputSticker(
                    sticker=sticker_data,
                    emoji_list=[sticker_emoji],
                    format=sticker_format
                )
            )
        if sticker_file and os.path.exists(sticker_file):
            os.remove(sticker_file)
        if done:
            await msg.edit_text(
                text=f"⚡ *Successfully Added Sticker to Pack!*\n\n🎭 Emoji: {sticker_emoji}",
                parse_mode=constants.ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(font('🧏 Sticker Pack'), url=pack_link)
                ]])
            )
    except Exception as e:
        if sticker_file and os.path.exists(sticker_file):
            os.remove(sticker_file)
        return await msg.edit_text(text=f"❌ Error while adding sticker to pack: {str(e)}")


async def get_stickers(query: str, limit: int = 15):
    url = "https://api.fstik.app/searchStickerSet"
    data = {
        "query": query,
        "skip": 0,
        "type": "",
        "user_token": "",
    }
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "User-Agent": get_ua(),
        "Referer": "https://fstik.app/?q=vegeta&menu=disabled"
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=data, headers=headers) as response:
                data = await response.json()
                return {'stickers': data['result']['stickerSets']} if data['ok'] == True else {'error': '🤷 Stickers not found'}
        except Exception as e:
            return {'error': str(e)}


@Command('emix')
async def emoji_mix_func(update, context):
    m = update.effective_message
    if len(m.text.split(maxsplit=1)) != 2:
        return await m.reply_text(
            "<b>Incorrect! Example</b>: <code>/emix 😉+😀</code>",
            parse_mode=constants.ParseMode.HTML
        )
    args = m.text.split(maxsplit=1)[1]
    if '+' not in args:
        return await m.reply_text(
            "<b>Incorrect! Example</b>: <code>/emix 😉+😀</code>",
            parse_mode=constants.ParseMode.HTML
        )
    parts = args.split('+', maxsplit=1)
    if len(parts) != 2:
        return await m.reply_text(
            "<b>Incorrect! Example</b>: <code>/emix 😉+😀</code>",
            parse_mode=constants.ParseMode.HTML
        )
    emoji_1, emoji_2 = parts[0].strip(), parts[1].strip()
    api_url = f"https://emojik.vercel.app/s/{emoji_1}_{emoji_2}?size=512"
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            try:
                if response.status != 200:
                    return await m.reply_text(
                        f"*❌ ERROR*: API returned status code {response.status}",
                        parse_mode=constants.ParseMode.MARKDOWN
                    )
                image_content = await response.read()
                path = f"emoji_mixed_{m.id}.png"
                with open(path, "wb") as file:
                    file.write(image_content)
                convert_to_webp(path)
                await m.reply_photo(path)
                await m.reply_document(path, f"*By {config.BOT_USERNAME}*", parse_mode=constants.ParseMode.MARKDOWN)
            except Exception as e:
                return await m.reply_text(
                    f"*❌ ERROR*: `{str(e)}`",
                    parse_mode=constants.ParseMode.MARKDOWN
                )
            finally:
                if os.path.exists(path):
                    os.remove(path)


@Command('reverse')
async def reverse(update, context):
    m = update.effective_message
    r = m.reply_to_message
    bot = context.bot
    valid = (r.sticker or (r.photo[-1] if r.photo else r.photo)) if r and (r.sticker or r.photo) else None
    if not valid:
        return await m.reply_text(
          text='❌ *Reply to sticker or photo ...*',
          parse_mode=constants.ParseMode.MARKDOWN
        )
    elif r and r.sticker:
        return await m.reply_text(
          text="ℹ️ *Convert the sticker to jpeg using our /getsticker then try /reverse.*", 
          parse_mode=constants.ParseMode.MARKDOWN
        )
    media = await bot.get_file(valid.file_id)
    image_url = media['file_path']
    msg = await m.reply_text(font('🔎 *Uploading to Google ...*'), parse_mode=constants.ParseMode.MARKDOWN)
    url = 'https://www.google.com/searchbyimage?sbisrc=4chanx&image_url={}&safe=off'.format(quote_plus(image_url))
    headers = {
         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
         'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
         'sec-ch-ua': '"Not-A.Brand";v="99", "Chromium";v="124"',
         'sec-ch-ua-full-version-list': '"Not-A.Brand";v="99.0.0.0", "Chromium";v="124.0.6327.4"',
         'sec-ch-ua-platform':'"Android"',
         'sec-ch-ua-model': '"Infinix X6816C"',
         'Upgrade-Insecure-Requests': '1',
         'sec-ch-ua-platform-version': '"11.0.0"',
         'cookie': get_cookies('./cookies/www.google.com_cookies.json'),
         'sec-ch-ua-wow64': '?0',
         'sec-ch-ua-mobile': '?1',
    } 
    try:
        async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, allow_redirects=True) as response:
                        content = await response.text()
                        soup = BeautifulSoup(content, 'html.parser')
                        title = soup.find('div', class_='r5a77d')
                        results = soup.find_all('div', class_='v7jaNc')
                        text = f"✨ *Results for image:*\n\n"
                        if title:
                            title_text = escape_markdown(title.text)
                            text += f"🟢 *{title_text}*\n"
                        if results:
                            for idx, src in enumerate(results, start=1):
                                 src_text = escape_markdown(src.text)
                                 text += f"\n{idx}, {src_text}"
                        text += f"\n\n*By {config.BOT_USERNAME}*"
                        button = InlineKeyboardMarkup(
                          [[
                            InlineKeyboardButton(font('🔎 Google Search'), url=str(response.url))
                          ]]
                        )
                        await msg.edit_text(
                          text, 
                          parse_mode=constants.ParseMode.MARKDOWN,
                          reply_markup=button
                        )     
    except Exception as e:
        await msg.edit_text(f'❌ ERROR: {str(e)}')


@Command('watermark')
async def watermark(update, context):
    m = update.effective_message
    r = m.reply_to_message
    bot = context.bot
    cmd = m.text.split()[0]
    mark = m.text.split(':')[0].replace(cmd, '').strip() if ':' in m.text else None
    size = int(m.text.split(':', 1)[1].strip()) if ':' in m.text and m.text.split(':', 1)[1].strip().isdigit() else None
    if not (mark and size):
        return await m.reply_text(font('*❌ Your given pattern is incorrect*.\n\nUsage: `/watermark YourText:50`'), parse_mode=constants.ParseMode.MARKDOWN)
    valid = (r.sticker or (r.photo[-1] if r.photo else r.photo)) if r and (r.sticker or r.photo) else None
    if not valid:
        return await m.reply_text(font('❌ *Reply to sticker or photo ...*'), parse_mode=constants.ParseMode.MARKDOWN)
    media = await bot.get_file(valid.file_id)
    path = await media.download_to_drive(f'ImageWaterMark_{m.id}.jpeg')
    photo = Image.open(path)
    width, height = photo.size
    draw = ImageDraw.Draw(photo)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', size)
    bbox = draw.textbbox((0, 0), mark, font=font)
    textwidth, textheight = bbox[2] - bbox[0], bbox[3] - bbox[1]
    margin = 5
    x = width - textwidth - margin
    y = height - textheight - margin
    draw.text((x, y), mark, font=font, fill="white")
    photo.save(path)
    txt = f"🖼️ *WaterMark Size*: {size}%\n\n" + f"*By {config.BOT_USERNAME}*"
    await m.reply_photo(path, caption=txt, parse_mode=constants.ParseMode.MARKDOWN)
    await m.reply_document(path, caption=txt, parse_mode=constants.ParseMode.MARKDOWN)
    os.remove(path)


@Command(('getgif', 'togif'))
async def aniStickerToGif(update, context):
     user = update.effective_user
     message, reply = update.effective_message, update.effective_message.reply_to_message
     bot = context.bot
     if not reply or (reply and not (reply.sticker and reply.sticker.is_video)):
         return await message.reply_text(font("Reply to a video sticker to convert to gif."))
     file_id = reply.sticker.file_id
     path = str(await (await bot.get_file(file_id)).download_to_drive())
     try:
        clip = mp.VideoFileClip(path)
        requests_path = f"user_{user.full_name}_stg.mp4"
        clip.write_videofile(requests_path, codec="libx264")
        await message.chat.send_animation(
               requests_path, caption=f"⚡* By @{bot.username}*", parse_mode=constants.ParseMode.MARKDOWN
        )
        os.remove(requests_path)
        os.remove(path)
     except Exception as e:
         return await message.reply_text(f"❌ Error: {e}")


@Command('blur')
async def blur(update, context):
     bot = context.bot
     m = update.effective_message
     r = m.reply_to_message
     args = context.args
     blur_radious = int(args[0]) if args and args[0].isdigit() and (int(args[0]) <= 100 and int(args[0]) >= 1) else 60
     valid = (r.sticker or (r.photo[-1] if r.photo else r.photo)) if r and (r.sticker or r.photo) else None
     if not valid: return await m.reply_text(font('❌ *Reply to sticker or photo ...*'), parse_mode=constants.ParseMode.MARKDOWN)
     media = await bot.get_file(valid.file_id)
     path = await media.download_to_drive(f'imageblur_{m.id}.jpeg')
     Photo = Image.open(path)
     photo = Photo.filter(ImageFilter.GaussianBlur(radius=blur_radious))
     photo.save(path)
     txt = f"🖼️ *Blur radious*: {blur_radious}%\n\n" + f"*By {config.BOT_USERNAME}*"
     await m.reply_photo(path, caption=txt, parse_mode=constants.ParseMode.MARKDOWN)
     await m.reply_document(path, caption=txt, parse_mode=constants.ParseMode.MARKDOWN)
     os.remove(path)


@Command('tosticker')
async def JpegToSticker(update, context):
     user = update.effective_user
     message = update.effective_message
     bot = context.bot
     if (
          not message.reply_to_message or message.reply_to_message and not any(
    [
    message.reply_to_message.photo,
    message.reply_to_message.document and message.reply_to_message.document.mime_type in ('image/png', 'image/jpeg', 'image/jpg'),
    ]
          )
     ):
         return await message.reply_text(font("🤷 Reply to the photo for convert photo/docu to sticker."))
     photo = message.reply_to_message.photo
     file = await bot.get_file(photo[-1].file_id)
     media = await file.download_to_drive('sticker.png')
     convert_to_webp(media)
     await message.reply_sticker(media)
     os.remove(media)


@Command('getsticker')
async def StickerToJpeg(update, context):
     user = update.effective_user
     message = update.effective_message
     bot = context.bot
     if (
          not message.reply_to_message or message.reply_to_message
          and not message.reply_to_message.sticker 
          or message.reply_to_message.sticker.is_animated
     ):
         return await message.reply_text(font("🤷 Reply to the sticker for convert to jpeg."))
     sticker= message.reply_to_message.sticker
     file = await bot.get_file(sticker.file_id)
     media = await file.download_to_drive('photo.png')
     await message.reply_photo(media)
     await message.reply_document(media)
     os.remove(media)


@Command('delkang')
async def DeleteStickerFromPack(update, context):
     user = update.effective_user
     message = update.effective_message
     bot = context.bot
     if (
          not message.reply_to_message or message.reply_to_message
          and not message.reply_to_message.sticker 
     ):
         return await message.reply_text(font("🤷 Reply to the sticker for delete from pack."))
     sticker = message.reply_to_message.sticker
     try:
         if await bot.delete_sticker_from_set(sticker.file_id):
              return await message.reply_text(font("⚡ *Sticker Removed from Pack!*"), parse_mode=constants.ParseMode.MARKDOWN)
     except Exception as e:
          return await message.reply_text(text=f"❌ Error while deleting sticker from pack: {str(e)}")


@Command('stickers')
async def search_stickers(update, context):
    message = update.effective_message
    try:
        query = message.text.split(maxsplit=1)[1]
    except IndexError:
        return await message.reply_text(font("❌ Please provide a search query!"))
    if not query.strip():
        return await message.reply_text(font("❌ Search query cannot be empty!"))
    msg = await message.chat.send_message(
      text="🔎 *Searching Stickers ...*",
      parse_mode=constants.ParseMode.MARKDOWN
    )
    try:
        data = await get_stickers(query)
        error = data.get('error')
        stickers = data.get('stickers', [])
        if error or len(stickers) == 0:
            return await msg.edit_text(f"🔍 No sticker packs found for '{query}'")     
        response_lines = [f"<b>Stickers found for {query}</b>:\n"]
        for idx, sticker in enumerate(stickers, start=1):
            safety_icon = '✅' if sticker.get('safe', False) else '❌'
            sticker_title = sticker.get('title', 'Unnamed Sticker Pack')
            sticker_link = f"https://t.me/addstickers/{sticker['name']}"
            response_lines.append(
                f"({idx}) <b><a href='{sticker_link}'>{html.escape(sticker_title)}</a> | Safety: {safety_icon}</b>"
            )
        response_text = "\n".join(response_lines)
        response_text += f"\n\n<b>By @{context.bot.username}</b>"
        await msg.edit_text(
            response_text, 
            parse_mode=constants.ParseMode.HTML,
            disable_web_page_preview=True
        )
    except Exception as e:
        await msg.edit_text(f"❌ An error occurred: {str(e)}")
