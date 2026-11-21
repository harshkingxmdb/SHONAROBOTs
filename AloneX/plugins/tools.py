import asyncio
import config
import uuid
import os
import base64
import json
import re
import io
import html
import urllib
import bs4
import aiohttp
import datetime as dt
from aiohttp import ClientSession
from aiohttp import FormData
import AloneX
from AloneX import pbot as bot, aiohttpsession as session, telegraph, app, telegraph_create, font, init_aiohttp_session
from pyrogram import filters, enums, types as pyro_types, Client
from pyrogram.errors import FloodWait
from types import SimpleNamespace
from AloneX import database
from AloneX.helpers.pyro_utils import get_media_from_message
from AloneX.helpers.decorator import Command, send_action, Callbacks
from AloneX.helpers.utils import get_ua, UserId
from AloneX.helpers.scripts import get_pypi_info, google_search, get_trendings, paste, ddg_search
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo, InputMediaPhoto, InputMediaAudio, constants, error, InputMedia
from PIL import Image


__module__ = "𝐓ᴏᴏʟs🛠️"

__help__ = """
*Tools*

*Description:*  
A collection of useful utilities for text, media, URLs, and developer tools.

*Commands:*  
❂ `/paste` – Reply with text or a document to paste on dpaste.org  
❂ `/search <query>` – Search Google  
❂ `/repodl <GitHub repo url>` – Download public repository  
❂ `/repo <query>` – Search GitHub repository  
❂ `/tgm` – Reply to any media (max 1 GB) to get a direct link  
❂ `/bots` – List all bots in this group  
❂ `/txt` – Reply to text to upload to Telegraph  
❂ `/json` – Show message object  
❂ `/iguser` – Instagram user info  
❂ `/trendings <country name>` – Get trending tags  
❂ `/gituser <username>` – GitHub user info  
❂ `/htmltoimg` – Convert HTML/text to image  
❂ `/pypi <package> <version>` – Get PyPI package info  
❂ `/tinyurl <url>` – Convert URL to tinyurl  
❂ `/mu` – Media uploader (reply to media)  
❂ `/fake <country code>` – Generate fake profile  

*Example:*  
`/paste Hello world!`  
`/search Telegram bot`  
`/repodl https://github.com/user/repo`
"""





@bot.on_message(filters.command("fake") & ~filters.forwarded, group=-533)
async def fk_address(_, message):
    m = message
    query = "us"  # Default nationality
    if len(message.command) > 1:
        query = message.text.split(maxsplit=1)[1].strip()

    url = f"https://randomuser.me/api/?nat={query}"

    async with ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                user = data['results'][0]
                text = (
                    f"**👤 Name**: {user['name']['title']} {user['name']['first']} {user['name']['last']}\n"
                    f"**🧬 Gender**: {user['gender']}\n"
                    f"**📍 Location**: {user['location']['street']['number']} {user['location']['street']['name']}, "
                    f"{user['location']['city']}, {user['location']['state']}, {user['location']['country']}, "
                    f"{user['location']['postcode']}\n"
                    f"**🌐 Coordinates**: ({user['location']['coordinates']['latitude']}, "
                    f"{user['location']['coordinates']['longitude']})\n"
                    f"**🕰️ Timezone**: {user['location']['timezone']['offset']} - {user['location']['timezone']['description']}\n"
                    f"**📧 Email**: {user['email']}\n"
                    f"**🆔 Username**: {user['login']['username']}\n"
                    f"**🎂 Date of Birth**: {user['dob']['date']} (Age: {user['dob']['age']})\n"
                    f"**📅 Registered**: {user['registered']['date']} (Age: {user['registered']['age']})\n"
                    f"**☎️ Phone**: {user['phone']}\n"
                    f"**📱 Cell**: {user['cell']}\n"
                    f"**🆔 ID**: {user['id']['name']} - {user['id']['value']}\n"
                    f"**🌏 Nationality**: {user['nat']}\n"
                )
                photo_url = user['picture']['large']
                if len(text) > 1023:
                    await m.reply_text(text)
                else:
                    await message.reply_photo(photo=photo_url, caption=text)
            else:
                await message.reply(font("Failed to fetch data from the API."))
              

@bot.on_message(filters.command(["jsondump", "json"]) & ~filters.forwarded, group=-531)
async def jsondump(c: Client, m: pyro_types.Message):
    params = m.text.split()
    # Remove the command name.
    params.pop(0)

    # Strip all things like _client and bound methods from Message.
    obj = json.loads(str(m))

    force_file = False
    # Remove the -f flag from list if present and set force_file to True.
    if "-f" in params:
        force_file = True
        params.remove("-f")

    for param in params:
        param = int(param) if param.lstrip("-").isdecimal() else param
        try:
            obj = obj[param]
        except (IndexError, KeyError) as e:
            await m.reply_text(f"{e.__class__.__name__}: {e}")
            return
        # There is nothing to get anymore.
        if obj is None:
            break

    obj = json.dumps(obj, indent=4, ensure_ascii=False)

    as_file = force_file or len(obj) > 3000

    if not as_file:
        await m.reply_text(f"<code>{html.escape(obj)}</code>")
        return

    bio = io.BytesIO(obj.encode())
    bio.name = f"dump-{m.chat.id}.json"
    await m.reply_document(bio)
   


@Command('tinyurl')
async def tiny_url(update, context):
   m = update.effective_message
   query = m.text.split(maxsplit=1)[1] if len(m.text.split()) > 1 else None
   if not query:
       return await m.reply_text(font("*😁 Gimme url.*"), parse_mode=constants.ParseMode.MARKDOWN)
   try:
       async with aiohttp.ClientSession() as session:
             async with session.post('https://tinyurl.com/api-create.php', data={'url': query}) as response:
                   text = await response.text()
                   await m.reply_text(text)
   except Exception as e:
       return await m.reply_text(f'❌ ERROR: {e}')


@Command('repo')
async def repository(update, context):
   m = update.effective_message
   query = m.text.split(maxsplit=1)[1] if len(m.text.split()) > 1 else None
   if not query:
       return await m.reply_text(font("*😁 Gimme Query.*"), parse_mode=constants.ParseMode.MARKDOWN)
   msg = await m.reply_text(font("🔎 *Searching repository...*"), parse_mode=constants.ParseMode.MARKDOWN)
   async with aiohttp.ClientSession() as session:
         try:
             url = "https://api.github.com/search/repositories?q={}&sort=stars".format(urllib.parse.quote_plus(query))
             async with session.get(url) as response:
                    data = await response.json() or {}
                    if len(data.get('items', [])) == 0:
                          return await msg.edit_text(font('❌ No results found!'))
                                                     
                    repos = [{"name": item["name"], "url": item["html_url"]} for item in data["items"]]
                    text = "✨ *Repository*:\n\n"
               
                    for idx, repo in enumerate(repos, start=1):
                         text += f"{idx}, [{repo['name']}]({repo['url']})\n"
                      
                    text += f"\n\n*By {config.BOT_USERNAME}*"
                    return await msg.edit_text(text, parse_mode=constants.ParseMode.MARKDOWN)
         except Exception as e:
              return await msg.edit_text(f'❌ *ERROR*: `{str(e)}`', parse_mode=constants.ParseMode.MARKDOWN)

     

@Command('pypi')
async def pypi(update, context):
    m = update.effective_message
    bot = context.bot
    text = m.text
    if not len(text.split()) > 1:
        return await m.reply_text(font('ℹ️ *Pypi name required!*'), parse_mode=constants.ParseMode.MARKDOWN)
    else:
        if len(text.split()) > 2:
            pkg = text.split()[1]
            ver = text.split()[2]
        else:
            pkg = text.split()[1]
            ver = None
    
    msg = await m.reply_text(font('🔎 *Searching package info ...*'), parse_mode=constants.ParseMode.MARKDOWN)
    data = await get_pypi_info(pkg, ver)
    error = data.get('error')
    if error: 
        return await msg.edit_text(f'❌ *ERROR*: `{error}`', parse_mode=constants.ParseMode.MARKDOWN)
    
    results = data['results']
    
    # Construct a detailed formatted message with .get() and fallback to 'N/A'
    text_parts = [
        f"📦 *{results.get('name', 'N/A')}* - Package Information",
        f"📝 *Description*: {results.get('summary', 'N/A')}",
        f"🔢 *Version*: `{results.get('version', 'N/A')}`",
        f"👤 *Author*: {results.get('author', 'N/A')} <{results.get('author_email', 'N/A')}>",
        f"🐍 *Python Requires*: `{results.get('requires_python', 'N/A')}`",
        f"🔑 *Keywords*: `{results.get('keywords', 'N/A')}`",
        "",
        "📦 *Installation*:",
        f"```bash\npip install {results.get('name', 'package_name')}```",
        "",
        "🌐 *Resources*:",
        f"- [Download]({results.get('download_url', 'N/A')})",
        f"- [Homepage](https://pypi.org/project/{results.get('name', 'N/A')}/)"
    ]
    
    text = "\n".join(text_parts)
    
    await msg.edit_text(text, parse_mode=constants.ParseMode.MARKDOWN, disable_web_page_preview=False)

@Command('htmltoimg')
async def html_to_image(update, context):
      m = update.effective_message
      r = m.reply_to_message
      bot = context.bot
      
      if not r or not (r and (r.text or r.document)):
           return await m.reply_text(font("Reply to the html message!"))
            
      elif r.document and not getattr(r.document, 'file_name', 'dont know').lower().endswith('html'):
           return await m.reply_text(font('File Extension Must end with Html'))
            
      msg = await m.reply_text(font("Generating Image ..."))

      if r.document:
            file = r.document.file_id
            path = await (await bot.get_file(file)).download_to_drive()
            with open(path) as file:
               content = file.read()
      else:
            content = r.text
      try:
            
          url = "https://htmlcsstoimage.com/demo_run"
          data = {
                "html": content,
                "console_mode": "",
                "url": "",
                "css": "",
                "selector": "",
                "ms_delay": "",
                "render_when_ready": "false",
                "viewport_height": "",
                "viewport_width": "",
                "google_fonts": "",
                "device_scale": "",
            }
          headers = {
                "cookie": "_hcti_website_session=SFhp%2FC3qpFOizmifGuqCaeHU5CGGm3fe2AOrGjkgLzK5xmme5U87lIrQvaSAsTh%2BIiWePfEjeRS2mQSemfqXDkca4SBEq0VMfidbgOrve6Ijivp8iPzoyVIxsG4wHncopQ5gdPDe45sYPJUZ%2FWoNhiYfNKg6XpTIBTbu4OQ7VmDQ8mxaNMukgYSB2%2FtNim%2BcRoE%2B9woQBO0unxrNYy0oRf3bKQbqhCDVUJ5iRYm4Dd4yIOkj1nNv39VQrcebkAAp9sPPrbsMGguP%2Bp9eiXGqxQPS5ycYlqK%2B2Zz8FU8%3D--MJPaMU59qWTaoEzF--Wjee8Ftq%2B%2FChRFKnsVi2Ow%3D%3D; _ga_JLLLQJL669=GS1.1.1711473771.1.0.1711473771.0.0.0; _ga=GA1.2.535741333.1711473772; _gid=GA1.2.601778978.1711473772; _gat_gtag_UA_32961413_2=1",
                "x-csrf-token": "pO7JhtS8osD491DfzpbVYXzThWKZjPoXXFBi69aJnlFRHIO9UGP7Gj9Y93xItqiCHzisYobEoWqcFqZqGVJsow",
            }
          async with aiohttp.ClientSession() as session:
                 async with session.post(url, json=data, headers=headers) as response:
                         if response.status != 200:
                             return await msg.edit_text(f"❌ Status code {response.status} & {response.reason}")
                         data = await response.json()
                         url = data.get('url')
                         if not url:
                              return await msg.edit_text(font("Image Url not found"))
                         else:
                              return await msg.edit_media(media=InputMediaPhoto(url, caption=f"*By {config.BOT_USERNAME}*", parse_mode=constants.ParseMode.MARKDOWN))          
      except Exception as e:
            return await msg.edit_text(f"❌ ERROR: {e}")


@Command('repodl')
async def RepoDownloader(update, context):
      m = update.effective_message
      chat = m.chat
      text = m.text
      pattern = r"https:\/\/github\.com\/([^\/]+)\/([^\/]+)"
      info = re.search(pattern, text)
      if not info:
          return await m.reply_text(font("Please send me repo url only."))
      user_name = info.group(1)
      repo_name = info.group(2)
      zip_file = "https://github.com/{}/{}/archive/main.zip".format(user_name, repo_name)
      try:
         await chat.send_document(
            document=zip_file,
            caption=f"*By {config.BOT_USERNAME}*",
            parse_mode=constants.ParseMode.MARKDOWN
      )
      except Exception as e:
               return await m.reply_text(
                     text="*It looks like the repo is private or can't be downloaded* 🤷", 
                     parse_mode=constants.ParseMode.MARKDOWN
               )
                   



@Command('gituser')
async def GitUser(update, context):
      m = update.effective_message
      username = m.text.split()[1] if len(m.text.split()) > 1 else None
      if not username:
          return await m.reply_text(font("Username required for search!"))

      msg = await m.reply_text(font("🔎 Searching ..."))
      async with aiohttp.ClientSession() as session:
            url = f"https://api.github.com/users/{username}"
            try:
               async with session.get(url) as response:
                     result = await response.json()
                     error = result.get('message')
                     if error:
                         return await msg.edit_text(error)
                     else:
                        type = result['type']
                        photo_url = result['avatar_url']
                        name = result['name'] or username
                        company = result.get('company', 'N/A')
                        email = result.get('email', "N/A")
                        bio = result.get('bio', 'N/A')
                        location = result.get('location', 'N/A')
                        repo_count = result['public_repos']
                        gists_count = result['public_gists']
                        following_count = result['following']
                        followers_count = result['followers']
                        acc_date = result['created_at']
                        # Convert date to more readable format
                        created_date = dt.datetime.strptime(acc_date, '%Y-%m-%dT%H:%M:%SZ').strftime('%B %d, %Y')
                        
                        text = f"""
🔍 *GitHub User Information*
━━━━━━━━━━━━━━━━━
👤 *Name:* `{name}`
🔗 *Link:* [ProfileLink](https://github.com/{username})
📝 *Type:* `{type}`
🏢 *Company:* `{company}`
📍 *Location:* `{location}`
📧 *Email:* `{email}`

📊 *Statistics:*
• *Repositories:* `{repo_count}`
• *Gists:* `{gists_count}`
• *Followers:* `{followers_count}`
• *Following:* `{following_count}`

ℹ️ *Bio:* `{bio}`
📅 *Joined:* `{created_date}`

*By {config.BOT_USERNAME}*
"""
                        return await msg.edit_media(
                               media=InputMediaPhoto(media=photo_url, caption=text, parse_mode=constants.ParseMode.MARKDOWN)
                        )
                        
            except Exception as e:
                  return await msg.edit_text(f"❌ ERROR: {str(e)}")


@Command('trendings')
async def getTrendingTags(update, context):
      m = update.effective_message
      country_data = ['algeria', 'argentina', 'australia', 'austria', 'bahrain', 'belarus', 'belgium', 'brazil', 'canada', 'chile', 'colombia', 'denmark', 'dominican-republic', 'ecuador', 'egypt', 'france', 'germany', 'ghana', 'greece', 'guatemala', 'india', 'indonesia', 'ireland', 'israel', 'italy', 'japan', 'jordan', 'kenya', 'korea', 'kuwait', 'latvia', 'lebanon', 'malaysia', 'mexico', 'netherlands', 'new-zealand', 'nigeria', 'norway', 'oman', 'pakistan', 'panama', 'peru', 'philippines', 'poland', 'portugal', 'puerto-rico', 'qatar', 'russia', 'saudi-arabia', 'singapore', 'south-africa', 'spain', 'sweden', 'switzerland', 'thailand', 'turkey', 'ukraine', 'united-arab-emirates', 'united-kingdom', 'united-states', 'venezuela', 'vietnam']


      country = None
      if len(m.text.split()) > 1:
           country = m.text.split()[1].lower()
           if country not in country_data:
                  return await m.reply_text(
                        text='Invalid Country Name!\n```Available\n' + "\n".join(country_data) + '```',
                        parse_mode=constants.ParseMode.MARKDOWN
                  )
            
      msg = await m.reply_text(
            text=f"*Searching trending tags for {country if country else '🌐 World wide'}*",
            parse_mode=constants.ParseMode.MARKDOWN
      )
      results = await get_trendings(country)
      error = results.get('error')
      if error:
            return await msg.edit_text(error['error'])
      text = ""
      text += f"*{results['title']}*\n\n"
      text += f"*🔎 Now trending Tags*:\n" + "\n".join(f"[{data['title']}]({data['url']})" for data in results['now_hashtags'][:5])
      text += f"\n*🔎 Today trending Tags*:\n" + "\n".join(f"[{data['title']}]({data['url']})" for data in results['today_hashtags'][:5])
      text += f"\n*🔎 Top trending Tags*:\n" + "\n".join(f"[{data['title']}]({data['url']})" for data in results['top_hashtags'][:5])
      await msg.edit_text(text, parse_mode=constants.ParseMode.MARKDOWN)


@Command("search")
async def Search(update, context):
    m = update.effective_message
    if len(m.text.split()) < 2:
        return await m.reply_text(font("🙋 Write a query to search."))

    query = m.text.split(maxsplit=1)[1]
    msg = await m.reply_text(font("<b>Searching ... 🔎</b>"), parse_mode=constants.ParseMode.HTML)

    data = await ddg_search(query)  # returns a list of dicts

    # Check if it's a dict with error
    if isinstance(data, dict) and data.get("error"):
        return await msg.edit_text(f"❌ ERROR: {data['error']}")

    if not data:  # empty list
        return await msg.edit_text(font("ℹ️ No Results Found!"))

    text = "<blockquote>\n"
    for idx, res in enumerate(data[:10], start=1):
        # Clean title and snippet
        title = re.sub(r'\s+', ' ', res.get('title', '')).strip()
        snippet = re.sub(r'\s+', ' ', res.get('snippet', '')).strip()
        snippet = snippet[:120]  # limit snippet length

        link = res.get('link', '#')
        text += f"{idx}. <a href='{link}'>{title}</a>\n"
        if snippet:
            text += f"   {snippet}...\n\n"

    text += f"<b>By {config.BOT_USERNAME}</b>\n</blockquote>"

    await msg.edit_text(
        text,
        parse_mode=constants.ParseMode.HTML,
        disable_web_page_preview=True
    )


@Command('paste')
async def pasteText(update, context):
   message = update.effective_message
   user = update.effective_user
  
   bot = context.bot
   reply = message.reply_to_message

   msg = await message.reply_text(
       text="*⚡ Reading contents...*", parse_mode=constants.ParseMode.MARKDOWN
   )
   if reply and reply.document and reply.document.mime_type.startswith('text'):
       file = await (await bot.get_file(reply.document.file_id)).download_to_drive()
       with open(file, 'r') as f:
            content = f.read()
       os.remove(file)
   elif reply and (reply.text or reply.caption):
       content = reply.text or reply.caption
   else:
       return await msg.edit_text(
           text="*Reply to a text or text file document...*",
           parse_mode=constants.ParseMode.MARKDOWN
       )
      
   data = await paste(content)
   if 'error' in data:
        return await msg.edit_text(font("Paste service not available at the movement. try after sometimes."))
   
   button = InlineKeyboardMarkup([[
      InlineKeyboardButton(font("Paste"), url=data["paste_url"], style=constants.ButtonStyle.SUCCESS),
      InlineKeyboardButton(font("Raw"), url=data["raw_url"], style=constants.ButtonStyle.SUCCESS),
]])
   await msg.reply_text(
         text="```py\nClick the below button```",
         reply_markup=button,
         parse_mode=constants.ParseMode.MARKDOWN
   )
   return await msg.delete()
   



YUKI_URL = "https://yukiapi.site/upload"
TGM_MAX_SIZE = 1024 * 1024 * 1024                      # 1 GB
TGM_TIMEOUT = aiohttp.ClientTimeout(total=None, connect=30, sock_read=900)


def _tgm_media_size(m) -> int:
    for kind in ("video", "photo", "document", "animation", "sticker", "video_note", "audio", "voice"):
        obj = getattr(m, kind, None)
        if obj:
            return getattr(obj, "file_size", 0) or 0
    return 0


async def _tgm_upload(file_path: str):
    """File is streamed to YukiAPI (no full copy in RAM). -> (True, link) or (False, reason)"""
    if AloneX.aiohttpsession is None or AloneX.aiohttpsession.closed:
        await init_aiohttp_session()
    try:
        with open(file_path, "rb") as fh:
            form = aiohttp.FormData()
            form.add_field("file", fh, filename=os.path.basename(file_path))
            async with AloneX.aiohttpsession.post(YUKI_URL, data=form, timeout=TGM_TIMEOUT) as r:
                text = await r.text()
                if r.status != 200:
                    return False, f"YukiAPI: HTTP {r.status} - {text[:100]}"
        if not text.strip():
            return False, "YukiAPI: empty response"
        try:
            data = json.loads(text)
        except ValueError:
            return False, "YukiAPI: response is not JSON"
        link = data.get("url", "") if isinstance(data, dict) else ""
        if link.startswith("http"):
            return True, link
        return False, f"YukiAPI: {str(data)[:100]}"
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        return False, f"upload error: {type(e).__name__}"


@bot.on_message(filters.command(['mu', 'tgm', 'tm', 'meow'], prefixes=config.prefix_cmds) & ~filters.forwarded)
async def media_uploader(_, message):
    reply = message.reply_to_message
    if not reply or not reply.media:
        return await message.reply_text("❌ Reply to a media file")

    if _tgm_media_size(reply) > TGM_MAX_SIZE:
        return await message.reply_text("❌ File must be under 1GB")

    msg = await message.reply_text("📥 Downloading...")
    path = None
    try:
        path = await reply.download()
        await msg.edit_text("📤 Uploading to YukiAPI...")
        ok, result = await _tgm_upload(path)
        if ok:
            await msg.edit_text(f"✅ Uploaded Successfully\n\n🔗 {result}", disable_web_page_preview=True)
        else:
            await msg.edit_text(f"❌ Upload failed: {result}")
    except Exception as e:
        await msg.edit_text(f"❌ Error:\n{type(e).__name__}: {e}")
    finally:
        if path and os.path.exists(path):
            os.remove(path)


@Command('txt')
async def telegraphFileUpload(update, context):
   
    m = message = update.effective_message
    bot = context.bot
    reply = message.reply_to_message
    user = update.effective_user
  
    if m.text.split()[0][1:] == 'txt':
         if not reply or reply and not (reply.text or reply.caption):
             return await m.reply_text(font("🙋 Reply to the text"))
         else:
             content = reply.text or reply.caption
             try:
                await telegraph_create()
                post = await telegraph.create_page(
                    title=f"{user.first_name}'s telegraph post", 
                    html_content=content
                )
                return await m.reply_text(post['url'])
             except Exception as e:
                 return await m.reply_text(repr(e))
    
    if not reply:
        return await message.reply_text(
            text="⚡ Reply to the animation (GIF) or a photo to upload in graph.org"
        )
    
    if reply.photo:
        file_name = f"{str(uuid.uuid4())}.jpg"
        media_type = "image/jpg"
        file_id = reply.photo[-1].file_id
      
    elif reply.sticker and not (reply.sticker.is_video or reply.sticker.is_animated):
        file_name = f"{str(uuid.uuid4())}.webp"
        media_type = "image/webp"
        file_id = reply.sticker.file_id
      
    elif reply.animation:
        return await m.reply_text(font('*not available currently.*'), parse_mode=constants.ParseMode.MARKDOWN)
        file_name = reply.animation.file_name
        media_type = reply.animation.mime_type
        file_id = reply.animation.file_id
      
    else:
        return await message.reply_text(
            text="⚡ Reply to the animation (GIF) or a photo to upload in graph.org"
        )
    
    msg = await message.reply_text(font("Downloading..."))
    file = await bot.get_file(file_id)
    file_path = await file.download_to_drive(
           custom_path=file_name
    )
    
    if reply.sticker:
        # Convert WebP sticker to JPG
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            converted_file_name = f"{str(uuid.uuid4())}.jpg"
            converted_file_path = os.path.join(os.path.dirname(file_path), converted_file_name)
            img.save(converted_file_path, "JPEG")
            os.remove(file_path)  # Remove the original WebP file
            file_path = converted_file_path
            media_type = "image/jpg"
  
    try:
    
      # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––>
      url = "https://api.imgbb.com/1/upload"
      data = {'image': open(file_path, 'rb'), 'key': '547d0eeac2bbf28433fb99204c49e215', 'name': file_name}
      # ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––>
      
      response = await session.post(url, data=data)
      results = await response.json()
      await msg.edit_text(results["data"]["url"])
      
    except Exception as error:
          await msg.edit_text(f"❌ ERROR: `{error}`")
       
    finally:
          # remove from memory
          os.remove(file_path)


# ================= /bots ================= #
# Telegram gives the full bot list only to admins. Without admin rights the bot still gets:
#   - the bots that are group admins (admin list is public),
#   - every bot that joined while this bot was in the group (saved in group_bots).
BOTS_DB = database["group_bots"]


@bot.on_message(filters.new_chat_members & filters.group, group=-540)
async def remember_joined_bots(client, message):
    for user in message.new_chat_members or []:
        if user.is_bot:
            await BOTS_DB.update_one(
                {"chat_id": message.chat.id, "bot_id": user.id},
                {"$set": {"username": user.username, "name": user.first_name}},
                upsert=True,
            )


@bot.on_message(filters.left_chat_member & filters.group, group=-541)
async def forget_left_bot(client, message):
    user = message.left_chat_member
    if user and user.is_bot:
        await BOTS_DB.delete_one({"chat_id": message.chat.id, "bot_id": user.id})


async def _collect_bots(client, chat_id: int):
    """-> (dict of bot_id -> user-like object, 'full' | 'partial')"""
    found = {}
    try:
        async for member in client.get_chat_members(chat_id, filter=enums.ChatMembersFilter.BOTS):
            found[member.user.id] = member.user
        return found, "full"
    except FloodWait:
        raise
    except Exception:
        found.clear()                                   # not admin -> the full list is not allowed

    try:
        async for member in client.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
            if member.user and member.user.is_bot:
                found[member.user.id] = member.user
    except FloodWait:
        raise
    except Exception:
        pass

    async for doc in BOTS_DB.find({"chat_id": chat_id}):
        if doc["bot_id"] not in found:
            found[doc["bot_id"]] = SimpleNamespace(
                id=doc["bot_id"], username=doc.get("username"), first_name=doc.get("name"))
    return found, "partial"


@bot.on_message(filters.command(["bots"], prefixes=config.prefix_cmds) & filters.group)
async def bots_list(client, message):
    try:
        found, mode = await _collect_bots(client, message.chat.id)
        if not found:
            return await message.reply_text("No bots found in this group.")

        bot_users = list(found.values())
        total = len(bot_users)
        text = f"**ʙᴏᴛ ʟɪsᴛ - {message.chat.title}**\n\n🤖 ʙᴏᴛs\n"
        for i, user in enumerate(bot_users):
            symbol = "└" if i == total - 1 else "├"
            name = f"@{user.username}" if user.username else (user.first_name or str(user.id))
            text += f"{symbol} {name}\n"
        text += f"\n**ᴛᴏᴛᴀʟ ɴᴜᴍʙᴇʀ ᴏғ ʙᴏᴛs**: {total}"
        if mode == "partial":
            text += ("\n\n⚠️ Partial list: bot is not admin here, so only admin bots and bots that joined "
                     "while I was in this group are shown.")
        await message.reply_text(text)
    except FloodWait as e:
        await asyncio.sleep(e.value)


# ================= /admins , /staff ================= #
# /adminlist is already handled in admins.py, so only these two aliases are added here.
def _staff_tag(user) -> str:
    if user.username:
        return f"@{user.username}"
    return f'<a href="tg://user?id={user.id}">{html.escape(user.first_name or "User")}</a>'


@bot.on_message(filters.command(["admins", "staff"], prefixes=config.prefix_cmds) & filters.group)
async def staff_list(client, message):
    try:
        owner, admin_users = None, []
        async for member in client.get_chat_members(message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
            user = member.user
            if not user or user.is_bot:
                continue
            privileges = getattr(member, "privileges", None)
            if privileges and getattr(privileges, "is_anonymous", False):
                continue                                # anonymous admins are hidden, as before
            if member.status == enums.ChatMemberStatus.OWNER:
                owner = user
            else:
                admin_users.append(user)

        total = len(admin_users) + (1 if owner else 0)
        text = f"<b>ɢʀᴏᴜᴘ sᴛᴀғғ - {html.escape(message.chat.title or '')}</b>\n\n"
        text += f"👑 ᴏᴡɴᴇʀ\n└ {_staff_tag(owner) if owner else '<i>Hidden</i>'}\n\n👮🏻 ᴀᴅᴍɪɴs\n"
        if not admin_users:
            text += "└ <i>ᴀᴅᴍɪɴs ᴀʀᴇ ʜɪᴅᴅᴇɴ</i>"
        else:
            for i, user in enumerate(admin_users):
                symbol = "└" if i == len(admin_users) - 1 else "├"
                text += f"{symbol} {_staff_tag(user)}\n"
        text += f"\n✅ | <b>ᴛᴏᴛᴀʟ ɴᴜᴍʙᴇʀ ᴏғ ᴀᴅᴍɪɴs</b>: {total}"
        await message.reply_text(text, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)
    except FloodWait as e:
        await asyncio.sleep(e.value)
