import asyncio
import os, urllib, uuid, random, base64, re, aiohttp
from telegram.helpers import escape_markdown
import aiohttp
from aiohttp import FormData
from AloneX import aiohttpsession as session, BOT_USERNAME, telegraph, app, LOGGER, LOGS_CHANNEL, font
from AloneX.helpers.decorator import Command, send_action, Callbacks, spam_control, only_premium
from AloneX.helpers.scripts import AiChats, paste, Gemini, GPTGeneration
from AloneX.helpers.utils import get_ua, UserId, get_as_document
from telegram import Update, constants, helpers, error, ReplyParameters
from telegram.ext import CallbackContext
from telegram import InputMediaPhoto, constants, InlineKeyboardMarkup, InlineKeyboardButton
from AloneX.helpers.scripts import get_output
import json
import tempfile
import contextlib
import config

__module__ = "𝐀ɪ🆕"

__help__ = """
*AI*

*Description:*  
This module provides access to multiple AI tools, including ChatGPT, Groq AI, Gemini, and image generation. You can ask questions, generate images, or get AI-assisted responses directly in your chat.

*Commands:*  
❂ `/ShonaX <query>` - Use Makima AI (supports photos and stickers).  
❂ `/gpt <query>` - Get a response from ChatGPT.  
❂ `/groq <query>` - Get a response from Groq AI.  
❂ `/draw <query>` - Generate an image from a text description.  
❂ `/imagine <query>` - Generate an image from a text description.  
❂ `/art <query>` - Generate an image from a text description.  
❂ `/google` or `/gemini <query>` - Get a response from Gemini AI.

*Examples:*  
`/ShonaX Hey, what is x^x?`  
`/draw A cute anime girl`  
`/imagine A cute anime girl`
"""

ai = AiChats()

@contextlib.asynccontextmanager
async def temporary_file(suffix=".jpeg"):
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        filename = tmp.name
    try:
        yield filename
    finally:
        if os.path.exists(filename):
            os.remove(filename)

async def generate_ai_image(prompt, key="Anime"):
    try:
        async with session.post(
            url="https://aiimagegenerator.io/api/model/predict-peach",
            json={
                "prompt": prompt,
                "negativePrompt": "",
                "key": key,
                "width": 512,
                "height": 768,
                "quantity": 1,
                "size": "512x768"
            }
        ) as response:
            if response.status == 200:
                result = await response.json()
                output = result.get('data', {}).get('output', [])
                if output and isinstance(output, list) and output[0].startswith("http"):
                    return output[0]
                return "❌ *ERROR*: No valid image URL found!"
            else:
                return f"❌ *ERROR status*: `{response.status}`"
    except Exception as e:
        return f"❌ *ERROR*: `{str(e)}`"

art_users = {}

@Command('art')
@send_action(constants.ChatAction.UPLOAD_PHOTO)
async def art_Img_func(update, context):
    m = update.effective_message
    user = update.effective_user
    bot = context.bot

    if len(m.text.split()) < 2:
        return await m.reply_text(font("🙋 Where is the prompt? e.g., /art anime Makima"))

    if art_users.get(user.id, None):
        return await m.reply_text(font('😉 *Please wait, an image is already generating!*'), parse_mode=constants.ParseMode.MARKDOWN)
    
    art_users[user.id] = True

    prompt = m.text.split(maxsplit=1)[1]
    msg = await m.reply_text(font("⚡ *Generating Image...*"), parse_mode=constants.ParseMode.MARKDOWN)

    try:
        image_url = await generate_ai_image(prompt)
        if not image_url.startswith('http'):
            return await msg.edit_text(image_url, parse_mode=constants.ParseMode.MARKDOWN)

        async with temporary_file(".jpeg") as image_filename:
            async with session.get(image_url) as image_response:
                if image_response.status == 200:
                    image_data = await image_response.read()
                    
                    with open(image_filename, "wb") as file:
                        file.write(image_data)

                    await m.reply_photo(image_filename)
                    okay = await m.reply_document(image_filename, caption=f"*⚡ By @{bot.username}*", parse_mode=constants.ParseMode.MARKDOWN)
                    if LOGS_CHANNEL:
                        await okay.copy(LOGS_CHANNEL, caption=f"*By* `{user.id}`", parse_mode=constants.ParseMode.MARKDOWN)
                    await msg.delete()
                else:
                    return await msg.edit_text(font('❌ Failed to download the generated image.'))
        
    except Exception as e:
        await msg.edit_text(f'❌ *ERROR*: `{str(e)}`', parse_mode=constants.ParseMode.MARKDOWN)
    finally:
        art_users.pop(user.id, None)

@Command('imagine')
@send_action(constants.ChatAction.UPLOAD_PHOTO)
@spam_control
async def DrawImg(update: Update, context: CallbackContext):
    m = update.effective_message
    bot = context.bot

    if len(m.text.split()) < 2:
        return await m.reply_text(font("🙋 where prompt ? e.g /imagine anime AloneX"))

    prompt = urllib.parse.quote(m.text.split(maxsplit=1)[1])
    url = f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true&model=flux-anime"
    msg = await m.reply_text(font("⚡ *Generating Image...*"), parse_mode=constants.ParseMode.MARKDOWN)

    headers = {'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36 OPR/86.0.0.0'}
    image_data = None

    for attempt in range(5):
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    image_data = await response.read()
                    break
                else:
                    await asyncio.sleep(2.5)
        except (aiohttp.ClientConnectionError, aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == 4:
                return await msg.edit_text(f'❌ Failed to generate image after multiple attempts: {str(e)}')
            await asyncio.sleep(4.5)

    if not image_data:
        return await msg.edit_text(font('❌ Failed to generate image. Please try again later.'))

    async with temporary_file(".png") as image:
        with open(image, "wb") as file:
            file.write(image_data)

        try:
            await m.reply_photo(image)
            await m.reply_document(image, caption=f"*⚡ By @{bot.username}*", parse_mode=constants.ParseMode.MARKDOWN)
            await msg.delete()
        except Exception as e:
            return await msg.edit_text(f'❌ Error when uploading: {str(e)}')

MONSTER_API_KEY = config.MONSTER_API_KEY

async def get_output_monster(prompt: str, negprompt: str):
    url = "https://api.monsterapi.ai/v1/generate/txt2img"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": MONSTER_API_KEY
    }

    payload = {
        "safe_filter": False,
        "prompt": prompt,
        "negprompt": negprompt,
        "style": "anime",
        "samples": 2,
        "guidance_scale": 8
    }

    async with session.post(url, headers=headers, json=payload) as response:
        try:
            results = await response.json()
        except Exception:
            results = json.loads(await response.text())

        status_url = results.get("status_url")
        if not status_url:
            return None

    for _ in range(6):
        await asyncio.sleep(5)
        async with session.get(status_url, headers=headers) as response:
            try:
                result = await response.json()
            except Exception:
                result = json.loads(await response.text())

            if isinstance(result, dict):
                result_data = result.get("result")
                if isinstance(result_data, dict):
                    output = result_data.get("output")
                    if output:
                        return output
    return None

@Command(("draw"))
@spam_control
@only_premium
@send_action(constants.ChatAction.UPLOAD_PHOTO)
async def imageDraw(update: Update, context: CallbackContext):
    m = update.effective_message
    bot = context.bot

    if not MONSTER_API_KEY:
        return await m.reply_text(font("❌ Monster API Key not configured."))

    if len(m.text.split()) == 1:
        return await m.reply_text(
            "🙋 Write something to draw.\nExample: `/draw anime girl neg: bad quality`",
            parse_mode=constants.ParseMode.MARKDOWN,
        )

    text = m.text.split(maxsplit=1)[1].strip()
    if "neg:" in text:
        parts = text.split("neg:")
        prompt = parts[0].strip()
        negprompt = parts[1].strip()
    else:
        prompt = text
        negprompt = ""

    msg = await m.reply_text(
        "*✨ Drawing please wait...*", parse_mode=constants.ParseMode.MARKDOWN
    )

    images = await get_output_monster(prompt, negprompt)

    if images:
        media = [InputMediaPhoto(img) for img in images]
        try:
            await bot.send_media_group(
                chat_id=m.chat.id,
                media=media,
                reply_parameters=ReplyParameters(message_id=m.message_id)
            )
            return await msg.delete()
        except Exception as e:
            return await msg.edit_text(f"❌ Error sending image: {e}")
    else:
        return await msg.edit_text(font("❌ No media generated. Try again later."))

gemini = Gemini(api_key=config.GEMINI_API_KEY)

@Command(('google', 'gemini'))
@spam_control
async def _gemini(update, context):
    m = update.effective_message
    user = m.from_user
    bot = context.bot
    r = m.reply_to_message

    if not config.GEMINI_API_KEY:
        return await m.reply_text(font("❌ Gemini API Key not configured."))

    msg = await m.reply_text("🔎")
    
    if r and r.photo:
        file_id = r.photo[-1].file_id
        path = await (await bot.get_file(file_id)).download_to_drive()
        prompt = m.text.split(maxsplit=1)[1] if len(m.text.split()) > 2 else r.caption if r.caption else "describe this picture"
        await msg.edit_text(font("📩 *Image processing ...*"), parse_mode=constants.ParseMode.MARKDOWN)
        
        try:
            file = await gemini.upload_image(path)
            if "error" in file: 
                return await msg.edit_text(f"❌ ERROR: {file['error']}")
            else:
                output = await gemini.ask(prompt, file)
                if "error" in output: 
                    return await msg.edit_text(f"❌ ERROR: {output['error']}")
                text = output.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No response found 😓')
                try:
                    return await msg.edit_text(text, parse_mode=constants.ParseMode.MARKDOWN)
                except Exception as e:
                    return await msg.edit_text(text)
        finally:
            if os.path.exists(path):
                os.remove(path)
    else:
        if r and (r.text or r.caption):
            prompt = "Replied text:" + f"\n{(r.text or r.caption)}"
            if len(m.text.split()) > 2:
                prompt += "\nQuestion:" + m.text.split(maxsplit=1)[1]
        else:
            if len(m.text.split()) < 2:
                return await msg.edit_text(font("*Ask Something !* 😓"), parse_mode=constants.ParseMode.MARKDOWN)
            prompt = m.text.split(maxsplit=1)[1]
        
        output = await gemini.ask(prompt)
        if "error" in output: 
            return await msg.edit_text(f"❌ ERROR: {output['error']}")
        else:
            text = output.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No response found 😓')
            try:
                return await msg.edit_text(text, parse_mode=constants.ParseMode.MARKDOWN)
            except Exception as e:
                return await msg.edit_text(text)

@Command(('AloneX', 'ask'))
@send_action(constants.ChatAction.TYPING)
@spam_control
async def AloneXAi(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    bot = context.bot
    reply = message.reply_to_message

    msg = await message.reply_text(
        "✨ *AloneX is thinking...*",
        parse_mode=constants.ParseMode.MARKDOWN
    )

    if len(message.text.split()) == 1:
        return await msg.edit_text(
            "*Usage:* `/AloneX <your question>`\n\n"
            "Example:\n`/AloneX recommend anime to watch`",
            parse_mode=constants.ParseMode.MARKDOWN
        )

    prompt = message.text.split(maxsplit=1)[1]
    messages = []

    if reply and (reply.text or reply.caption):
        prompt = f"Previous:\n{reply.text or reply.caption}\n\nQuestion:\n{prompt}"
    messages.append({"role": "user", "content": prompt})

    data = await ai.groq(messages, api_key=config.GROQ_API_KEY)
    reply_text = data.get('reply', "I'm AloneX Ackerman.")

    if len(reply_text) > 4000:
        paste_src = await paste(reply_text)
        return await msg.edit_text(
            f"📑 [Full Reply Here]({paste_src['paste_url']})",
            disable_web_page_preview=False,
            parse_mode=constants.ParseMode.MARKDOWN
        )

    try:
        return await msg.edit_text(
            f"👩‍🦰 *AloneX says:*\n\n{reply_text}",
            parse_mode=constants.ParseMode.MARKDOWN
        )
    except Exception:
        return await msg.edit_text(reply_text)


@Command('gpt')
@send_action(constants.ChatAction.TYPING)
@spam_control
async def ChatGpt(update, context):
    m = update.effective_message
    reply = m.reply_to_message
    
    if len(m.text.split()) == 1: 
        return await m.reply_text(
            text="⚡ Enter some prompt", 
            parse_mode=constants.ParseMode.MARKDOWN
        )

    prompt = m.text.split(maxsplit=1)[1]   
    if reply and reply.text:
        prompt = f"Old conversation:\n{reply.text}\n\nQuestion:\n{prompt}"
         
    msg = await m.reply_text('🔍')
    gpt = GPTGeneration()
    
    try:
        gptReply = await gpt.create(prompt)
        if len(gptReply) > 4000:
            document = get_as_document(gptReply)
            await m.reply_document(document)
            await msg.delete()
        else:
            await msg.edit_text(text=gptReply, parse_mode=constants.ParseMode.MARKDOWN)
    except Exception as e:
        return await msg.edit_text(font("*❌ Unknown Error*\n") + str(e), parse_mode=constants.ParseMode.MARKDOWN)

@Command('groq')
@send_action(constants.ChatAction.TYPING)
@only_premium
async def groq(update, context):
    message = update.effective_message
    reply = message.reply_to_message
    
    if not config.GROQ_API_KEY:
        return await message.reply_text(font("❌ Groq API Key not configured."))

    if len(message.text.split()) == 1:
        return await message.reply_text(
            "*Enter some query*. ⚡",
            parse_mode=constants.ParseMode.MARKDOWN
        )
      
    msg = await message.reply_text("⚡")
    
    user_prompt = message.text.split(maxsplit=1)[1]
    if reply and reply.text:
        user_prompt = f"Old conversation:\n{reply.text}\n\nQuestion:\n{user_prompt}"
        
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": user_prompt}
        ]
    }
  
    try:
        async with session.post(api_url, headers=headers, json=data) as response:
            if response.status == 200:
                response_json = await response.json()
                botReply = response_json.get("choices", [])[0].get("message", {}).get("content", "*Sorry i can't answer that question!*")
                if len(botReply) > 3500:
                    document = get_as_document(botReply)
                    await message.reply_document(document)
                    await msg.delete()
                else:
                    await msg.edit_text(
                        text=botReply, 
                        parse_mode=constants.ParseMode.MARKDOWN
                    )
            else:
                return await msg.edit_text(
                    text=f"❌ *Request failed*: `{response.status} - {response.reason}`",
                    parse_mode=constants.ParseMode.MARKDOWN
                )
    except Exception as e:
        return await msg.edit_text(
            text=f"❌ *ERROR*: `{str(e)}`",
            parse_mode=constants.ParseMode.MARKDOWN
        )
