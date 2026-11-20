import asyncio
import base64
import io
import os
import random
import re
import time
import urllib.parse

import aiohttp
from telegram import Update, constants, InputMediaPhoto, ReplyParameters
from telegram.ext import CallbackContext

import AloneX
import config
from AloneX import LOGGER, LOGS_CHANNEL, font, init_aiohttp_session
from AloneX.helpers.decorator import Command, send_action, spam_control, only_premium
from AloneX.helpers.utils import get_as_document

__module__ = "𝐀ɪ🆕"

__help__ = """
*AI*

*Description:*
This module provides access to multiple AI tools: ShonaX AI, ChatGPT, Groq AI, Gemini and image generation. You can ask questions, generate images, or get AI-assisted responses directly in your chat.

*Commands:*
❂ `/ShonaX [query]` or `/ask [query]` - Chat with ShonaX AI (you can also reply to a message).
❂ `/gpt [query]` - Get a response from ChatGPT.
❂ `/groq [query]` - Get a response from Groq AI.
❂ `/google` or `/gemini [query]` - Get a response from Gemini AI (reply to a photo to ask about it).
❂ `/draw [query]` - Generate an image from a text description.
❂ `/imagine [query]` - Generate an image from a text description.
❂ `/art [query]` - Generate an anime image from a text description.

*Examples:*
`/ShonaX Hey, what is x^x?`
`/draw A cute anime girl`
`/imagine A cute anime girl`
"""

# ── API settings ─────────────────────────────────────────────────────────────
# Chat API (used by /gpt and as a backup for /ShonaX, /groq, /gemini)
CHAT_API_URL = "https://chatgp-nine.vercel.app/api/chat"
CHAT_API_KEY = "ritesh-8179b3a5da99f300be2d50e1e9789729"

# Models are tried in this order. Old ones were shut down by the providers
# (gemini-1.5-flash, gemini-2.0-flash, llama-3.3-70b-versatile ...), so keep this list current.
GEMINI_MODELS = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash-lite"]
GROQ_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]

# /draw: Cloudflare Workers AI (FLUX.1 schnell, free daily allowance). Needs both Config Vars.
# If they are not set, /draw automatically uses the key-less Pollinations backup.
CF_ACCOUNT_ID = getattr(config, "CF_ACCOUNT_ID", "") or os.getenv("CF_ACCOUNT_ID", "")
CF_API_TOKEN = getattr(config, "CF_API_TOKEN", "") or os.getenv("CF_API_TOKEN", "")
CF_MODEL = "@cf/black-forest-labs/flux-1-schnell"

PERSONA = (
    "You are ShonaX, a friendly, smart and helpful AI assistant made by AloneX Team. "
    "Reply in the same language as the user (Hinglish if they write Hinglish). "
    "Be clear and to the point."
)

UA = {
    "user-agent": (
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Mobile Safari/537.36"
    )
}


# ── helpers ──────────────────────────────────────────────────────────────────
async def get_session() -> aiohttp.ClientSession:
    """Shared aiohttp session.

    `from AloneX import aiohttpsession` copies the value at import time, and at that moment it is
    still None. That is why every request through it crashed. Always read it from the module.
    """
    if AloneX.aiohttpsession is None or AloneX.aiohttpsession.closed:
        await init_aiohttp_session()
    return AloneX.aiohttpsession


def _timeout(seconds: int) -> aiohttp.ClientTimeout:
    return aiohttp.ClientTimeout(total=seconds)


async def safe_edit(msg, text: str):
    """LLM text often breaks Telegram Markdown; try Markdown first, then plain text."""
    md_text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    try:
        return await msg.edit_text(md_text, parse_mode=constants.ParseMode.MARKDOWN)
    except Exception:
        return await msg.edit_text(text)


async def send_answer(m, msg, text: str):
    """Edit the status message with the answer, or send a .txt file if it is too long."""
    text = (text or "").strip() or "😓"
    if len(text) > 4000:
        await m.reply_document(get_as_document(text))
        return await msg.delete()
    return await safe_edit(msg, text)


# ── text AI backends: every function returns (text, error) ───────────────────
async def ask_chat_api(prompt: str):
    s = await get_session()
    headers = {"Authorization": f"Bearer {CHAT_API_KEY}", "Content-Type": "application/json"}
    err = "API not responding"
    for attempt in range(3):
        try:
            async with s.post(CHAT_API_URL, json={"prompt": prompt}, headers=headers, timeout=_timeout(30)) as r:
                if r.status == 200:
                    data = await r.json(content_type=None)
                    reply = data.get("response") if isinstance(data, dict) else None
                    if reply and "503" not in reply and "系统通知" not in reply:
                        return reply, None
                    err = "empty reply"
                elif r.status in (401, 403):
                    return None, "chat API key rejected"
                elif r.status in (429, 500, 502, 503):
                    err = f"HTTP {r.status}"
                else:
                    return None, f"HTTP {r.status}"
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            err = type(e).__name__
        if attempt < 2:
            await asyncio.sleep(1)
    return None, err


async def groq_chat(user_prompt: str):
    key = config.GROQ_API_KEY
    if not key:
        return None, "GROQ_API_KEY not set"
    s = await get_session()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    messages = [{"role": "system", "content": PERSONA}, {"role": "user", "content": user_prompt}]
    url = "https://api.groq.com/openai/v1/chat/completions"
    last_err = "no reply"

    for model in GROQ_MODELS:
        # 2nd variant has no optional params, in case a model rejects them
        for extra in ({"reasoning_effort": "low", "max_completion_tokens": 2048}, {}):
            try:
                async with s.post(url, json={"model": model, "messages": messages, **extra},
                                  headers=headers, timeout=_timeout(45)) as r:
                    data = await r.json(content_type=None)
                    if r.status == 200:
                        text = ((data.get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()
                        if text:
                            return text, None
                        last_err = "empty reply"
                        break
                    msg = (data.get("error") or {}).get("message", r.reason) if isinstance(data, dict) else r.reason
                    last_err = f"{r.status}: {msg}"
                    if r.status in (401, 403):
                        return None, last_err          # key problem, other models will fail too
                    if r.status == 400 and extra:
                        continue                       # retry same model without optional params
                    break                              # 404 / 429 / 5xx -> next model
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_err = type(e).__name__
                break
    return None, last_err


async def gemini_ask(prompt: str, image: bytes = None, mime: str = "image/jpeg"):
    key = config.GEMINI_API_KEY
    if not key:
        return None, "GEMINI_API_KEY not set"
    s = await get_session()
    parts = []
    if image:
        parts.append({"inlineData": {"mimeType": mime, "data": base64.b64encode(image).decode()}})
    parts.append({"text": prompt})
    payload = {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"maxOutputTokens": 4096}}
    headers = {"Content-Type": "application/json", "x-goog-api-key": key}
    last_err = "no reply"

    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            async with s.post(url, json=payload, headers=headers, timeout=_timeout(60)) as r:
                data = await r.json(content_type=None)
                if r.status == 200:
                    cands = data.get("candidates") or []
                    if not cands:
                        block = (data.get("promptFeedback") or {}).get("blockReason")
                        return None, f"blocked ({block})" if block else "empty reply"
                    parts_out = (cands[0].get("content") or {}).get("parts") or []
                    text = "".join(p.get("text", "") for p in parts_out if not p.get("thought")).strip()
                    if text:
                        return text, None
                    last_err = "empty reply"
                    continue
                msg = (data.get("error") or {}).get("message", r.reason) if isinstance(data, dict) else r.reason
                last_err = f"{r.status}: {msg}"
                if r.status in (401, 403) or (r.status == 400 and "api key" in msg.lower()):
                    return None, last_err              # key problem, other models will fail too
                # 404 (model gone) / 429 / 5xx -> try next model
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_err = type(e).__name__
    return None, last_err


# ── /ShonaX  /AloneX  /ask ───────────────────────────────────────────────────
@Command(("ShonaX", "AloneX", "ask"))
@send_action(constants.ChatAction.TYPING)
@spam_control
async def AloneXAi(update: Update, context: CallbackContext) -> None:
    m = update.effective_message
    reply = m.reply_to_message
    args = m.text.split(maxsplit=1)
    question = args[1] if len(args) > 1 else ""
    quoted = (reply.text or reply.caption) if reply else None

    if not question and not quoted:
        return await m.reply_text(
            "*Usage:* `/ShonaX <your question>`\n\nExample:\n`/ShonaX recommend anime to watch`",
            parse_mode=constants.ParseMode.MARKDOWN,
        )

    msg = await m.reply_text("✨ *ShonaX is thinking...*", parse_mode=constants.ParseMode.MARKDOWN)

    prompt = question or quoted
    if quoted and question:
        prompt = f"Previous message:\n{quoted}\n\nQuestion:\n{question}"

    text, err = await groq_chat(prompt)
    if not text:
        LOGGER.warning(f"[ai] groq failed ({err}), using chat API")
        text, err = await ask_chat_api(f"System: {PERSONA}\n\nUser: {prompt}\nAssistant:")
    if not text:
        return await msg.edit_text(f"❌ AI is not working right now.\n\nReason: {err}")
    return await send_answer(m, msg, f"👩‍🦰 *ShonaX says:*\n\n{text}")


# ── /gpt ─────────────────────────────────────────────────────────────────────
@Command("gpt")
@send_action(constants.ChatAction.TYPING)
@spam_control
async def ChatGpt(update, context):
    m = update.effective_message
    reply = m.reply_to_message
    args = m.text.split(maxsplit=1)

    if len(args) == 1:
        return await m.reply_text("⚡ Enter some prompt")

    prompt = args[1]
    if reply and (reply.text or reply.caption):
        prompt = f"Old conversation:\n{reply.text or reply.caption}\n\nQuestion:\n{prompt}"

    msg = await m.reply_text("🔍")
    text, err = await ask_chat_api(f"System: {PERSONA}\n\nUser: {prompt}\nAssistant:")
    if not text:
        return await msg.edit_text(f"❌ Unknown Error: {err}")
    return await send_answer(m, msg, text)


# ── /groq ────────────────────────────────────────────────────────────────────
@Command("groq")
@send_action(constants.ChatAction.TYPING)
@only_premium
async def groq(update, context):
    m = update.effective_message
    reply = m.reply_to_message
    args = m.text.split(maxsplit=1)

    if len(args) == 1:
        return await m.reply_text("*Enter some query*. ⚡", parse_mode=constants.ParseMode.MARKDOWN)

    msg = await m.reply_text("⚡")
    prompt = args[1]
    if reply and (reply.text or reply.caption):
        prompt = f"Old conversation:\n{reply.text or reply.caption}\n\nQuestion:\n{prompt}"

    text, err = await groq_chat(prompt)
    if not text:
        LOGGER.warning(f"[ai] groq failed ({err}), using chat API")
        text, err = await ask_chat_api(f"System: {PERSONA}\n\nUser: {prompt}\nAssistant:")
    if not text:
        return await msg.edit_text(f"❌ ERROR: {err}")
    return await send_answer(m, msg, text)


# ── /gemini  /google ─────────────────────────────────────────────────────────
@Command(("google", "gemini"))
@spam_control
async def _gemini(update, context):
    m = update.effective_message
    bot = context.bot
    r = m.reply_to_message
    args = m.text.split(maxsplit=1)
    question = args[1] if len(args) > 1 else ""

    if r and r.photo:
        msg = await m.reply_text(font("📩 *Image processing ...*"), parse_mode=constants.ParseMode.MARKDOWN)
        prompt = question or r.caption or "describe this picture"
        try:
            tg_file = await bot.get_file(r.photo[-1].file_id)
            image = bytes(await tg_file.download_as_bytearray())
        except Exception as e:
            return await msg.edit_text(f"❌ Could not download the photo: {e}")
        text, err = await gemini_ask(prompt, image=image)
        if not text:
            return await msg.edit_text(f"❌ ERROR: {err}")
        return await send_answer(m, msg, text)

    if r and (r.text or r.caption):
        prompt = f"Replied text:\n{r.text or r.caption}"
        if question:
            prompt += f"\nQuestion: {question}"
    elif question:
        prompt = question
    else:
        return await m.reply_text(font("*Ask Something !* 😓"), parse_mode=constants.ParseMode.MARKDOWN)

    msg = await m.reply_text("🔎")
    text, err = await gemini_ask(prompt)
    if not text:
        LOGGER.warning(f"[ai] gemini failed ({err}), using chat API")
        backup, err2 = await ask_chat_api(f"System: {PERSONA}\n\nUser: {prompt}\nAssistant:")
        if not backup:
            return await msg.edit_text(f"❌ ERROR: {err}")
        text = backup
    return await send_answer(m, msg, text)


# ── image generation ─────────────────────────────────────────────────────────
art_users = {}


# Pollinations (anonymous) allows about 1 image per 15 s. Requests wait in one queue instead of failing.
_poll_lock = asyncio.Lock()
_poll_last = 0.0
_poll_waiting = 0
POLL_GAP = 16          # seconds between two Pollinations requests
POLL_MAX_QUEUE = 3     # more people than this waiting -> go straight to the backup


def to_jpeg(data: bytes) -> bytes:
    """Telegram is happiest with JPEG; AI Horde returns webp."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data)).convert("RGB")
        out = io.BytesIO()
        img.save(out, "JPEG", quality=92)
        return out.getvalue()
    except Exception:
        return data


async def fetch_pollinations(prompt: str, width: int = 1024, height: int = 1024):
    """Pollinations free endpoint, queued so that users do not hit its rate limit."""
    global _poll_last, _poll_waiting
    if _poll_waiting >= POLL_MAX_QUEUE:
        return None
    s = await get_session()
    url = (
        f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt[:500])}"
        f"?width={width}&height={height}&nologo=true&model=flux&seed={random.randint(1, 999999)}"
    )
    _poll_waiting += 1
    try:
        async with _poll_lock:
            for attempt in range(2):
                gap = POLL_GAP - (time.monotonic() - _poll_last)
                if gap > 0:
                    await asyncio.sleep(gap)
                try:
                    async with s.get(url, headers=UA, timeout=_timeout(60)) as r:
                        _poll_last = time.monotonic()
                        if r.status == 200 and r.content_type.startswith("image"):
                            return await r.read()
                        LOGGER.warning(f"[ai] pollinations HTTP {r.status}")
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    _poll_last = time.monotonic()
                    LOGGER.warning(f"[ai] pollinations {type(e).__name__}")
    finally:
        _poll_waiting -= 1
    return None


async def fetch_horde(prompt: str, max_wait: int = 180):
    """AI Horde: free, community GPUs, works without an account (key 0000000000). Slow but reliable."""
    s = await get_session()
    base = "https://aihorde.net/api/v2"
    headers = {
        "apikey": os.getenv("HORDE_API_KEY", "0000000000"),
        "Client-Agent": "ShonaXBot:1.0:telegram",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt[:900],
        "params": {"width": 512, "height": 512, "steps": 25, "n": 1},
        "nsfw": False,
        "censor_nsfw": True,
        "r2": True,
    }
    job = None
    try:
        async with s.post(f"{base}/generate/async", json=payload, headers=headers, timeout=_timeout(30)) as r:
            data = await r.json(content_type=None)
            if r.status not in (200, 202) or not isinstance(data, dict) or not data.get("id"):
                LOGGER.warning(f"[ai] horde submit HTTP {r.status}: {str(data)[:200]}")
                return None
            job = data["id"]

        waited = 0
        while waited < max_wait:
            await asyncio.sleep(4)
            waited += 4
            async with s.get(f"{base}/generate/check/{job}", headers=headers, timeout=_timeout(30)) as r:
                st = await r.json(content_type=None)
            if isinstance(st, dict) and (st.get("faulted") or st.get("is_possible") is False):
                return None
            if isinstance(st, dict) and st.get("done"):
                break
        else:
            async with s.delete(f"{base}/generate/status/{job}", headers=headers, timeout=_timeout(15)):
                pass                                   # leave the queue, nobody is waiting any more
            return None

        async with s.get(f"{base}/generate/status/{job}", headers=headers, timeout=_timeout(30)) as r:
            res = await r.json(content_type=None)
        gens = (res.get("generations") or []) if isinstance(res, dict) else []
        if not gens or gens[0].get("censored"):
            return None
        img = gens[0].get("img") or ""
        if img.startswith("http"):
            async with s.get(img, timeout=_timeout(60)) as d:
                if d.status != 200:
                    return None
                return to_jpeg(await d.read())
        return to_jpeg(base64.b64decode(img))
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
        LOGGER.warning(f"[ai] horde {type(e).__name__}")
        return None


async def fetch_free_image(prompt: str, width: int = 1024, height: int = 1024, msg=None):
    """Free image chain: Pollinations (fast) -> AI Horde (slow but always there)."""
    image = await fetch_pollinations(prompt, width, height)
    if image:
        return image
    if msg is not None:
        try:
            await msg.edit_text(font("⏳ Main server busy hai, backup se bana raha hu. 1-2 minute lag sakta hai..."))
        except Exception:
            pass
    return await fetch_horde(prompt)


async def fetch_aiimagegenerator(prompt: str, key: str = "Anime"):
    s = await get_session()
    try:
        async with s.post(
            "https://aiimagegenerator.io/api/model/predict-peach",
            json={"prompt": prompt, "negativePrompt": "", "key": key, "width": 512,
                  "height": 768, "quantity": 1, "size": "512x768"},
            timeout=_timeout(60),
        ) as r:
            if r.status != 200:
                return None
            result = await r.json(content_type=None)
        output = (result.get("data") or {}).get("output") or []
        if not (output and isinstance(output, list) and str(output[0]).startswith("http")):
            return None
        async with s.get(output[0], timeout=_timeout(60)) as img:
            if img.status == 200:
                return await img.read()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, AttributeError) as e:
        LOGGER.warning(f"[ai] aiimagegenerator {type(e).__name__}")
    return None


async def deliver_image(m, bot, msg, image: bytes, log_user=None):
    await m.reply_photo(image)
    sent = await m.reply_document(
        image, filename="image.jpg",
        caption=f"*⚡ By @{bot.username}*", parse_mode=constants.ParseMode.MARKDOWN,
    )
    if log_user and LOGS_CHANNEL:
        try:
            await sent.copy(LOGS_CHANNEL, caption=f"*By* `{log_user}`", parse_mode=constants.ParseMode.MARKDOWN)
        except Exception:
            pass
    await msg.delete()


@Command("art")
@send_action(constants.ChatAction.UPLOAD_PHOTO)
async def art_Img_func(update, context):
    m = update.effective_message
    user = update.effective_user
    bot = context.bot
    args = m.text.split(maxsplit=1)

    if len(args) < 2:
        return await m.reply_text(font("🙋 Where is the prompt? e.g., /art anime Makima"))

    if art_users.get(user.id):
        return await m.reply_text(font("😉 *Please wait, an image is already generating!*"),
                                  parse_mode=constants.ParseMode.MARKDOWN)

    art_users[user.id] = True
    msg = await m.reply_text(font("⚡ *Generating Image...*"), parse_mode=constants.ParseMode.MARKDOWN)
    try:
        prompt = args[1]
        image = await fetch_aiimagegenerator(prompt)
        if not image:      # first service down -> free backups
            image = await fetch_free_image(f"{prompt}, anime style", 768, 1024, msg)
        if not image:
            return await msg.edit_text(font("❌ Failed to generate image. Please try again later."))
        await deliver_image(m, bot, msg, image, log_user=user.id)
    except Exception as e:
        await msg.edit_text(f"❌ ERROR: {e}")
    finally:
        art_users.pop(user.id, None)


@Command("imagine")
@send_action(constants.ChatAction.UPLOAD_PHOTO)
@spam_control
async def DrawImg(update: Update, context: CallbackContext):
    m = update.effective_message
    bot = context.bot
    args = m.text.split(maxsplit=1)

    if len(args) < 2:
        return await m.reply_text(font("🙋 where prompt ? e.g /imagine anime AloneX"))

    msg = await m.reply_text(font("⚡ *Generating Image...*"), parse_mode=constants.ParseMode.MARKDOWN)
    image = await fetch_free_image(args[1], msg=msg)
    if not image:
        return await msg.edit_text(font("❌ Failed to generate image. Please try again later."))
    try:
        await deliver_image(m, bot, msg, image)
    except Exception as e:
        return await msg.edit_text(f"❌ Error when uploading: {e}")


async def fetch_cloudflare(prompt: str):
    """Cloudflare Workers AI, FLUX.1 schnell. Returns image bytes or None."""
    if not (CF_ACCOUNT_ID and CF_API_TOKEN):
        return None
    s = await get_session()
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{CF_MODEL}"
    headers = {"Authorization": f"Bearer {CF_API_TOKEN}"}
    payload = {"prompt": prompt[:2000], "steps": 6, "seed": random.randint(1, 2**31 - 1)}
    try:
        async with s.post(url, json=payload, headers=headers, timeout=_timeout(60)) as r:
            data = await r.json(content_type=None)
            if r.status == 200 and isinstance(data, dict) and data.get("success"):
                b64 = (data.get("result") or {}).get("image")
                if b64:
                    return base64.b64decode(b64)
            LOGGER.warning(f"[ai] cloudflare HTTP {r.status}: {str(data)[:200]}")
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
        LOGGER.warning(f"[ai] cloudflare {type(e).__name__}")
    return None


@Command("draw")
@spam_control
@only_premium
@send_action(constants.ChatAction.UPLOAD_PHOTO)
async def imageDraw(update: Update, context: CallbackContext):
    m = update.effective_message
    bot = context.bot

    args = m.text.split(maxsplit=1)
    if len(args) == 1:
        return await m.reply_text(
            "🙋 Write something to draw.\nExample: `/draw anime girl with blue hair`",
            parse_mode=constants.ParseMode.MARKDOWN,
        )

    prompt = args[1].partition("neg:")[0].strip()      # negative prompts are not supported by FLUX
    prompt = f"{prompt}, anime style, highly detailed"

    msg = await m.reply_text("*✨ Drawing please wait...*", parse_mode=constants.ParseMode.MARKDOWN)

    images = []
    if CF_ACCOUNT_ID and CF_API_TOKEN:
        results = await asyncio.gather(fetch_cloudflare(prompt), fetch_cloudflare(prompt))
        images = [i for i in results if i]
    if not images:                                      # no Cloudflare keys, or it failed
        single = await fetch_free_image(prompt, msg=msg)
        images = [single] if single else []

    if not images:
        return await msg.edit_text(font("❌ No media generated. Try again later."))
    try:
        if len(images) == 1:
            await m.reply_photo(images[0])
        else:
            await bot.send_media_group(
                chat_id=m.chat.id,
                media=[InputMediaPhoto(img) for img in images],
                reply_parameters=ReplyParameters(message_id=m.message_id),
            )
        return await msg.delete()
    except Exception as e:
        return await msg.edit_text(f"❌ Error sending image: {e}")
