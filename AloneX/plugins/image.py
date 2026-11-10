import os
import uuid
import time
import aiohttp
import aiofiles
from g4f.client import Client as G4FClient
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ButtonStyle
from AloneX import pbot as app, font

__module__ = "𝐈ᴍᴀɢᴇ-𝐆ᴇɴ🎨"
__help__ = """
*Image Generation🎨*

*Description:*  
Generate AI images using multiple models and styles. Create beautiful images from text prompts.

*Commands:*  
❂ `/igpt <prompt>` - Generate image from prompt  
❂ `/img <prompt>` - Alternative image generation command  
❂ `#igpt <prompt>` - Generate using hashtag  
❂ `/imghelp` - Show help message  

*Features:*  
• Multiple AI models (Flux, DALL-E, Midjourney, etc.)
• Various art styles (Realistic, Anime, 3D, Cyberpunk, etc.)
• Regenerate images with one click
• Switch models and styles easily

*Note:* NSFW content is blocked automatically.
"""

MODELS = {
    "flux": "🎨 flux (default)",
    "dalle": "🖼️ dall-e",
    "midjourney": "🎭 midjourney",
    "stable-diffusion": "🌟 stable diffusion",
    "playground": "🎪 playground",
    "lexica": "📚 lexica"
}
STYLES = {
    "realistic": "📸 realistic",
    "anime": "🎌 anime",
    "3d": "🎮 3d render",
    "cyberpunk": "🌆 cyberpunk",
    "pixel": "🕹️ pixel art",
    "oil": "🎨 oil painting",
    "watercolor": "🖌️ watercolor",
    "sketch": "✏️ sketch"
}
style_cooldown = {}
user_cooldown = {}
NSFW_WORDS = {
    "nsfw", "nude", "naked", "sex", "sexy", "boobs", "tits", "pussy", "dick", "penis",
    "vagina", "ass", "butt", "cum", "cumshot", "milf", "hentai", "porno", "porn", "anal",
    "blowjob", "fuck", "fucking", "deepthroat", "suck", "sucking", "bdsm", "fetish",
    "orgy", "threesome", "masturbate", "masturbation", "erotic", "hot girl", "hot boy",
    "nipple", "breast", "strip", "stripper", "escort", "dominatrix", "lingerie", "incest",
    "stepmom", "stepdad", "horny", "clit", "pegging", "spank", "kinky", "lust", "sex toy",
    "dildo", "thong", "crotchless", "panties", "creampie", "titty", "rape", "abuse", "molest"
}
prompt_storage = {}

def is_nsfw(prompt: str) -> bool:
    prompt = prompt.lower()
    return any(word in prompt for word in NSFW_WORDS)
def extract_prompt(message: Message) -> str:
    text = message.text or message.caption or ""
    for tag in ["/igpt", "#igpt", "/img", "#img", "/generate", "#generate"]:
        text = text.replace(tag, "")
    return text.strip()
def store_prompt(prompt: str, user_id: int, model: str = "flux") -> str:
    prompt_id = str(uuid.uuid4())[:8]
    prompt_storage[f"{prompt_id}_{user_id}"] = {"prompt": prompt, "model": model}
    return prompt_id
def get_stored_data(prompt_id: str, user_id: int) -> dict:
    return prompt_storage.get(f"{prompt_id}_{user_id}", {})
def make_two_column_markup(items, callback_prefix, prompt_id, user_id):
    rows = []
    current_row = []
    for key, name in items.items():
        current_row.append(
            InlineKeyboardButton(name, callback_data=f"{callback_prefix}|{key}|{prompt_id}|{user_id}", style=ButtonStyle.SUCCESS)
        )
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    rows.append([InlineKeyboardButton(font("🔙 back"), callback_data=f"back|{prompt_id}|{user_id}", style=ButtonStyle.PRIMARY)])
    return InlineKeyboardMarkup(rows)
def control_buttons(prompt: str, user_id: int, model: str = "flux"):
    prompt_id = store_prompt(prompt, user_id, model)
    return [
        [
            InlineKeyboardButton(font("🔄 regenerate"), callback_data=f"r|{prompt_id}|{user_id}", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(font("🎨 models"), callback_data=f"models|{prompt_id}|{user_id}", style=ButtonStyle.SUCCESS)
        ],
        [InlineKeyboardButton(font("🎭 styles"), callback_data=f"styles|{prompt_id}|{user_id}", style=ButtonStyle.SUCCESS)]
    ]

async def download_image(url: str) -> str:
    name = f"{uuid.uuid4()}.jpg"
    path = f"downloads/{name}"
    os.makedirs("downloads", exist_ok=True)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    if len(content) < 10 * 1024:
                        return None
                    async with aiofiles.open(path, "wb") as f:
                        await f.write(content)
                    return path
    except Exception as e:
        print(f"download error: {e}")
    return None
async def generate_image(prompt: str, model: str = "flux", style: str = None):
    try:
        if style:
            style_prompts = {
                "realistic": "photorealistic, highly detailed, professional photography",
                "anime": "anime style, manga art, japanese animation",
                "3d": "3d rendered, cgi, digital art, blender render",
                "cyberpunk": "cyberpunk style, neon lights, futuristic, dark atmosphere",
                "pixel": "pixel art style, 8-bit, retro gaming aesthetic",
                "oil": "oil painting style, classical art, painterly brushstrokes",
                "watercolor": "watercolor painting, soft colors, artistic medium",
                "sketch": "pencil sketch, hand-drawn, artistic drawing"
            }
            prompt = f"{prompt}, {style_prompts.get(style, style + ' style')}"
        g4f = G4FClient()
        model_mapping = {
            "flux": "flux",
            "dalle": "dall-e-3",
            "midjourney": "midjourney",
            "stable-diffusion": "stable-diffusion-xl",
            "playground": "playground-v2.5",
            "lexica": "lexica-aperture-v3"
        }
        actual_model = model_mapping.get(model, "flux")
        result = await g4f.images.async_generate(
            model=actual_model,
            prompt=prompt,
            response_format="url",
            quality="hd",
            size="1024x1024"
        )
        if result and result.data:
            url = result.data[0].url
            return await download_image(url)
    except Exception as e:
        print(f"generation error with {model}: {e}")
        if model != "flux":
            try:
                result = await g4f.images.async_generate(
                    model="flux",
                    prompt=prompt,
                    response_format="url"
                )
                if result and result.data:
                    url = result.data[0].url
                    return await download_image(url)
            except:
                pass
    return None

@app.on_message(filters.command(["igpt", "img", "generate"], prefixes=["/", "!", "#"]) | 
                filters.regex(r"#(igpt|img|generate)"), group=-800)
async def igpt_handler(_, m: Message):
    prompt = extract_prompt(m)
    if not prompt and m.reply_to_message:
        prompt = extract_prompt(m.reply_to_message)
    if not prompt:
        return await m.reply(
            "❗ please provide a prompt!\n\n"
            "usage:\n"
            "`/igpt beautiful sunset over mountains`\n"
            "`#igpt cute anime girl with blue eyes`\n"
            "`/img cyberpunk city at night`"
        )
    if is_nsfw(prompt):
        return await m.reply(font("🚫 nsfw prompts are not allowed."))
    user_id = m.from_user.id
    now = time.time()
    if now - user_cooldown.get(user_id, 0) < 3:
        return await m.reply(font("⏳ please wait 3 seconds between requests."))
    user_cooldown[user_id] = now
    wait = await m.reply(font("🎨 generating image..."))
    try:
        image_path = await generate_image(prompt)
        if not image_path:
            return await wait.edit("❌ failed to generate image. try again!")
        await m.reply_photo(
            photo=image_path,
            caption=f"🎨 generated image\n\n"
                   f"prompt: `{prompt[:200]}{'...' if len(prompt) > 200 else ''}`\n"
                   f"model: flux\n\n"
                   f"generated by AloneX ai",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                control_buttons(prompt, m.from_user.id, "flux")
            )
        )
        await wait.delete()
        os.remove(image_path)
    except Exception as e:
        await wait.edit(f"❌ error: `{str(e)}`")

@app.on_callback_query(filters.regex(r"^m\|"), group=-801)
async def model_callback(_, query: CallbackQuery):
    try:
        _, model, prompt_id, user_id = query.data.split("|", 3)
        if str(query.from_user.id) != user_id:
            return await query.answer(font("❌ not for you!"), show_alert=True)
        data = get_stored_data(prompt_id, int(user_id))
        if not data:
            return await query.answer(font("❌ session expired!"), show_alert=True)
        prompt = data.get("prompt")
        if is_nsfw(prompt):
            return await query.answer(font("🚫 nsfw content blocked."), show_alert=True)
        await query.answer(f"🎨 generating with {MODELS[model]}...")
        image_path = await generate_image(prompt, model=model)
        if not image_path:
            return await query.message.reply(font("❌ failed to generate image."))
        await query.message.reply_photo(
            photo=image_path,
            caption=f"🎨 generated image\n\n"
                   f"prompt: `{prompt[:200]}{'...' if len(prompt) > 200 else ''}`\n"
                   f"model: {MODELS[model]}\n\n"
                   f"generated by AloneX ai",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                control_buttons(prompt, int(user_id), model)
            )
        )
        os.remove(image_path)
    except Exception as e:
        await query.message.reply(f"❌ model error: `{e}`")

@app.on_callback_query(filters.regex(r"^s\|"), group=-802)
async def style_callback(_, query: CallbackQuery):
    try:
        _, style, prompt_id, user_id = query.data.split("|", 3)
        if str(query.from_user.id) != user_id:
            return await query.answer(font("❌ not for you!"), show_alert=True)
        data = get_stored_data(prompt_id, int(user_id))
        if not data:
            return await query.answer(font("❌ session expired!"), show_alert=True)
        prompt = data.get("prompt")
        model = data.get("model", "flux")
        if is_nsfw(prompt):
            return await query.answer(font("🚫 nsfw content blocked."), show_alert=True)
        now = time.time()
        if now - style_cooldown.get(query.from_user.id, 0) < 5:
            return await query.answer(font("⏳ wait 5 seconds between style changes."), show_alert=True)
        style_cooldown[query.from_user.id] = now
        await query.answer(f"🎭 applying {STYLES[style]} style...")
        image_path = await generate_image(prompt, model=model, style=style)
        if not image_path:
            return await query.message.reply(font("❌ failed to generate image."))
        await query.message.reply_photo(
            photo=image_path,
            caption=f"🎨 generated image\n\n"
                   f"prompt: `{prompt[:150]}{'...' if len(prompt) > 150 else ''}`\n"
                   f"model: {MODELS[model]}\n"
                   f"style: {STYLES[style]}\n\n"
                   f"generated by AloneX ai",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                control_buttons(prompt, int(user_id), model)
            )
        )
        os.remove(image_path)
    except Exception as e:
        await query.message.reply(f"❌ style error: `{e}`")

@app.on_callback_query(filters.regex(r"^r\|"), group=-803)
async def regenerate_callback(_, query: CallbackQuery):
    try:
        _, prompt_id, user_id = query.data.split("|", 2)
        if str(query.from_user.id) != user_id:
            return await query.answer(font("❌ not for you!"), show_alert=True)
        data = get_stored_data(prompt_id, int(user_id))
        if not data:
            return await query.answer(font("❌ session expired!"), show_alert=True)
        prompt = data.get("prompt")
        model = data.get("model", "flux")
        if is_nsfw(prompt):
            return await query.answer(font("🚫 nsfw content blocked."), show_alert=True)
        await query.answer(font("🔄 regenerating..."))
        image_path = await generate_image(prompt, model=model)
        if not image_path:
            return await query.message.reply(font("❌ failed to regenerate image."))
        await query.message.reply_photo(
            photo=image_path,
            caption=f"🔄 regenerated image\n\n"
                   f"prompt: `{prompt[:200]}{'...' if len(prompt) > 200 else ''}`\n"
                   f"model: {MODELS[model]}\n\n"
                   f"generated by AloneX ai",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                control_buttons(prompt, int(user_id), model)
            )
        )
        os.remove(image_path)
    except Exception as e:
        await query.message.reply(f"❌ regenerate error: `{e}`")

@app.on_callback_query(filters.regex(r"^models\|"), group=-804)
async def models_menu(_, query: CallbackQuery):
    try:
        _, prompt_id, user_id = query.data.split("|", 2)
        if str(query.from_user.id) != user_id:
            return await query.answer(font("❌ not for you!"), show_alert=True)
        data = get_stored_data(prompt_id, int(user_id))
        if not data:
            return await query.answer(font("❌ session expired!"), show_alert=True)
        prompt = data.get("prompt")
        await query.edit_message_text(
            f"🎨 choose ai model\n\n"
            f"prompt: `{prompt[:100]}{'...' if len(prompt) > 100 else ''}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_two_column_markup(MODELS, "m", prompt_id, user_id)
        )
    except Exception as e:
        await query.answer(f"error: {e}", show_alert=True)

@app.on_callback_query(filters.regex(r"^styles\|"), group=-805)
async def styles_menu(_, query: CallbackQuery):
    try:
        _, prompt_id, user_id = query.data.split("|", 2)
        if str(query.from_user.id) != user_id:
            return await query.answer(font("❌ not for you!"), show_alert=True)
        data = get_stored_data(prompt_id, int(user_id))
        if not data:
            return await query.answer(font("❌ session expired!"), show_alert=True)
        prompt = data.get("prompt")
        model = data.get("model", "flux")
        await query.edit_message_text(
            f"🎭 choose style\n\n"
            f"prompt: `{prompt[:100]}{'...' if len(prompt) > 100 else ''}`\n"
            f"model: {MODELS[model]}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_two_column_markup(STYLES, "s", prompt_id, user_id)
        )
    except Exception as e:
        await query.answer(f"error: {e}", show_alert=True)

@app.on_callback_query(filters.regex(r"^back\|"), group=-806)
async def back_handler(_, query: CallbackQuery):
    try:
        _, prompt_id, user_id = query.data.split("|", 2)
        if str(query.from_user.id) != user_id:
            return await query.answer(font("❌ not for you!"), show_alert=True)
        data = get_stored_data(prompt_id, int(user_id))
        if not data:
            return await query.answer(font("❌ session expired!"), show_alert=True)
        prompt = data.get("prompt")
        model = data.get("model", "flux")
        await query.edit_message_text(
            f"🎨 generated image\n\n"
            f"prompt: `{prompt[:100]}{'...' if len(prompt) > 100 else ''}`\n"
            f"model: {MODELS[model]}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(control_buttons(prompt, int(user_id), model))
        )
    except Exception as e:
        await query.answer(f"error: {e}", show_alert=True)

@app.on_message(filters.command(["imghelp", "genhelp"], prefixes=["/", "!"]), group=-807)
async def help_handler(_, m: Message):
    help_text = """
🎨 Alone ai image generator

command: `#igpt [prompt]`

example: `#igpt beautiful sunset`

made with ❤️ by Alone Ai
"""
    await m.reply(help_text, parse_mode=ParseMode.MARKDOWN)
