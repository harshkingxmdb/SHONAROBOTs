import io
import os
import re
import time
import base64
import hashlib
import logging
import asyncio
import threading
import html
from collections import OrderedDict
from contextlib import suppress

import aiohttp
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM, Message, CallbackQuery
from pyrogram.enums import ButtonStyle, ChatMemberStatus
from AloneX import pbot, prefix_cmds, font, LOGS_CHANNEL, BOT_USERNAME
from AloneX.db.approval_db import is_user_approved
from AloneX.db.antinsfw_db import get_antinsfw, set_antinsfw, get_antinsfw_admin, set_antinsfw_admin
import config

__module__ = "𝐀ɴᴛɪ-𝐍sғᴡ🛡️"
__help__ = """
*𝐀ɴᴛɪ-𝐍sғᴡ🛡️* — Protect your group from porn content with AI detection

• `/antiporn` — Toggle anti-NSFW settings or check status.
• `/nsfwstatus` — Check detection model status.

*Behavior:*
Automatically scans and deletes NSFW media. User mode covers normal users, while Admin mode includes administrators.
"""

class NSFWDetector:
    """Anti-NSFW engine.

    Engine 1 (default): Gemini vision API. Light, no torch / transformers needed, so it works on Heroku.
                        Uses GEMINI_API_KEY from config.py. Model can be set with NSFW_GEMINI_MODEL (config.py).
    Engine 2 (fallback): local Falconsai model, only if torch + transformers are installed
                        (they are far too big for a Heroku basic dyno).
    """

    GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
    # tried in this order; a model that does not exist (404) or that refuses this key (401/403) is skipped
    # and the next one is tried. The model that worked is remembered.
    GEMINI_MODELS = (
        "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash",
        "gemini-flash-latest", "gemini-2.5-flash",
    )
    PROMPT = (
        "You are a strict content-moderation classifier for a Telegram group. Look at the image. "
        "Does it contain pornography or sexually explicit content: exposed genitals, exposed female "
        "nipples, buttocks in a sexual context, or an explicit sexual act? "
        "Reply with exactly one word: NSFW or SAFE."
    )
    BLOCK_REASONS = ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "IMAGE_SAFETY", "OTHER")

    def __init__(self):
        self.model = None          # local pipeline (optional engine)
        self.engine = None         # "gemini" | "local" | None
        self.loaded = False
        self.loading = False
        self.reason = ""           # why the detector is disabled (shown in /nsfwstatus)
        self.gemini_model = None   # the model name that worked last
        self._cache = OrderedDict()
        self._cooldown_until = 0.0
        self._last_warn = 0.0
        self._retry_at = 0.0
        self._sem = None
        self._ready = threading.Event()

        self.api_key = getattr(config, "GEMINI_API_KEY", None)
        if self.api_key:
            self.engine = "gemini"
            self.loaded = True
            self._ready.set()
        else:
            self.loading = True
            threading.Thread(target=self._load_local_model, daemon=True).start()

    # ---------------- local engine (optional) ----------------
    def _load_local_model(self):
        try:
            import torch
            from transformers import pipeline

            self.model = pipeline(
                "image-classification",
                model="Falconsai/nsfw_image_detection",
                device=0 if torch.cuda.is_available() else -1,
            )
            self.engine = "local"
            self.loaded = True
        except Exception as e:
            self.loaded = False
            self.reason = (
                "No GEMINI_API_KEY set and the local model (torch + transformers) is not installed: "
                f"{type(e).__name__}"
            )
            logging.warning(f"[NSFW] local model not available: {e}")
        finally:
            self.loading = False
            self._ready.set()

    async def wait_ready(self, timeout=45):
        if self.loaded:
            return True
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._ready.wait, timeout)

    # ---------------- helpers ----------------
    def _warn(self, text: str):
        # at most one warning per 60 s so a broken API can not flood the logs
        if time.time() - self._last_warn > 60:
            self._last_warn = time.time()
            logging.warning(text)

    @staticmethod
    def _prepare(image_bytes: bytes):
        """-> (PIL image <=512px, jpeg bytes)"""
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        if img.size[0] > 512 or img.size[1] > 512:
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return img, buf.getvalue()

    @staticmethod
    def _clean_error(body, limit: int = 110) -> str:
        """Google error body (json or text) -> short plain sentence: no quotes, braces or html entities."""
        text = ""
        try:
            import json as _json

            data = body if isinstance(body, dict) else _json.loads(body)
            err = data.get("error") or {}
            text = f"{err.get('message', '')} {err.get('status', '')}".strip()
        except Exception:
            text = str(body)
        text = re.sub(r"[^A-Za-z0-9 .,:()_/-]", " ", text)
        return re.sub(r"\s+", " ", text).strip()[:limit] or "no details"

    def _parse_gemini(self, data: dict):
        """-> True (nsfw) / False (safe) / None (no usable answer)"""
        block = (data.get("promptFeedback") or {}).get("blockReason")
        if block:  # Gemini itself refused the picture for safety reasons -> that is a strong NSFW signal
            return block in self.BLOCK_REASONS
        cands = data.get("candidates") or []
        if not cands:
            return None
        cand = cands[0]
        if cand.get("finishReason") in self.BLOCK_REASONS and not (cand.get("content") or {}).get("parts"):
            return True
        text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", [])).strip().upper()
        if not text:
            return None
        if text.startswith("NSFW"):
            return True
        if text.startswith("SAFE"):
            return False
        return "NSFW" in text and "SAFE" not in text

    async def _gemini(self, jpeg: bytes) -> bool:
        if time.time() < self._cooldown_until:
            return False
        if self._sem is None:
            self._sem = asyncio.Semaphore(3)

        env_model = getattr(config, "NSFW_GEMINI_MODEL", "") or None
        models = [env_model] if env_model else list(self.GEMINI_MODELS)
        if self.gemini_model in models:
            models.remove(self.gemini_model)
            models.insert(0, self.gemini_model)

        payload = {
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": self.PROMPT},
                    {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpeg).decode()}},
                ],
            }],
            "generationConfig": {"temperature": 0},
            "safetySettings": [
                {"category": c, "threshold": "BLOCK_NONE"}
                for c in (
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_HARASSMENT",
                    "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_DANGEROUS_CONTENT",
                )
            ],
        }
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}

        auth_errors = []      # (status, short text) of models that refused the key
        async with self._sem:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as session:
                for model in models:
                    try:
                        async with session.post(
                            f"{self.GEMINI_BASE}/models/{model}:generateContent", headers=headers, json=payload
                        ) as resp:
                            status = resp.status
                            body = await resp.json(content_type=None) if status == 200 else await resp.text()
                    except Exception as e:
                        self._warn(f"[NSFW] Gemini request failed: {type(e).__name__}")
                        return False

                    if status == 200:
                        verdict = self._parse_gemini(body)
                        self.gemini_model = model
                        return bool(verdict)
                    if status == 404:          # this model name does not exist (any more) -> try the next one
                        continue
                    if status in (400, 401, 403):   # key refused (maybe only for THIS model) -> try the next one
                        auth_errors.append((status, self._clean_error(body)))
                        continue
                    if status == 429:          # rate limit -> pause for a minute, do not block the chat
                        self._cooldown_until = time.time() + 60
                        self._warn("[NSFW] Gemini rate limit (HTTP 429) - pausing scans for 60 s.")
                        return False
                    self._warn(f"[NSFW] Gemini HTTP {status}: {self._clean_error(body)}")
                    return False

        if auth_errors:                        # every model that exists refused the key
            code, msg = auth_errors[-1]
            self.loaded = False
            self._retry_at = time.time() + 600
            self.reason = f"Gemini key not accepted (HTTP {code}): {msg}. Set a valid GEMINI_API_KEY in Heroku config vars"
            logging.error(f"[NSFW] {self.reason}")
        else:
            self.reason = "No Gemini model worked (all returned 404). Set NSFW_GEMINI_MODEL in the config vars."
            self._warn(f"[NSFW] {self.reason}")
        return False

    # ---------------- public api ----------------
    async def is_nsfw(self, image_bytes: bytes) -> bool:
        try:
            if not self.loaded and self.engine == "gemini" and self.api_key and time.time() >= self._retry_at:
                self.loaded = True            # key may have been fixed, try again
            if not self.loaded:
                await self.wait_ready()
            if not self.loaded:
                return False

            key = hashlib.md5(image_bytes).hexdigest()
            if key in self._cache:
                return self._cache[key]

            img, jpeg = self._prepare(image_bytes)
            if self.engine == "gemini":
                result = await self._gemini(jpeg)
            elif self.engine == "local" and self.model:
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(None, self.model, img)
                result = any(r["label"].lower() == "nsfw" and r["score"] > 0.65 for r in results)
            else:
                return False

            self._cache[key] = result
            if len(self._cache) > 500:
                self._cache.popitem(last=False)
            return result
        except Exception as e:
            self._warn(f"[NSFW] is_nsfw error: {type(e).__name__}: {e}")
            return False

    async def check_video_frame(self, video_path: str) -> bool:
        try:
            import cv2

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return False
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if total > 8:  # first frame is often a title / black screen, look a quarter in
                cap.set(cv2.CAP_PROP_POS_FRAMES, total // 4)
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                return False

            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            return await self.is_nsfw(buffer.tobytes())
        except Exception:
            return False

    def status_html(self) -> str:
        if self.loaded and self.engine == "gemini":
            return (
                "✅ <b>Model Status: Ready</b>\n\n"
                f"🤖 <b>Engine:</b> Gemini Vision ({html.escape(self.gemini_model or 'auto model')})\n"
                "⚡ <b>Performance:</b> Cloud, no heavy libraries\n"
                "🎯 <b>Accuracy:</b> High Confidence Mode"
            )
        if self.loaded and self.engine == "local":
            return (
                "✅ <b>Model Status: Ready</b>\n\n"
                "🤖 <b>Engine:</b> FalconsAI NSFW Detection (local)\n"
                "📊 <b>Threshold:</b> 65%"
            )
        if self.loading:
            return "🔄 <b>Model Loading...</b>\n\n⏳ Please wait, model will be ready soon"
        return (
            "❌ <b>Model Failed</b>\n\n"
            "🐛 NSFW detection is currently <b>disabled</b>\n"
            f"ℹ️ <b>Reason:</b> {html.escape(self.reason or 'unknown')}"
        )

detector = NSFWDetector()

async def is_user_admin(chat_id: int, user_id: int):
    from AloneX.helpers.decorator import protected_ids, user_admin_cache
    if user_id in protected_ids:
        return True
    k = (chat_id, user_id, 'a')
    res = user_admin_cache.get(k)
    if res is not None:
        return res
    try:
        member = await pbot.get_chat_member(chat_id, user_id)
        res = member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
        user_admin_cache[k] = res
        return res
    except:
        return False

async def get_antiporn_keyboard(chat_id: int):
    user_mode = await get_antinsfw(chat_id)
    admin_mode = await get_antinsfw_admin(chat_id)
    
    u_text = f"🟢 User Mode: ON" if user_mode else "🔴 User Mode: OFF"
    u_style = ButtonStyle.SUCCESS if user_mode else ButtonStyle.DANGER
    
    a_text = f"🟢 Admin Mode: ON" if admin_mode else "🔴 Admin Mode: OFF"
    a_style = ButtonStyle.SUCCESS if admin_mode else ButtonStyle.DANGER
    
    return IKM([
        [IKB(font(u_text), callback_data="ap_toggle_user", style=u_style)],
        [IKB(font(a_text), callback_data="ap_toggle_admin", style=a_style)]
    ])

@pbot.on_message(filters.command(["antiporn", "antipornadmin"], prefixes=prefix_cmds) & filters.group)
async def antiporn_cmd(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))

    if len(message.command) > 1:
        arg = message.command[1].lower()
        if message.command[0].lower() == "antiporn":
            if arg == "on":
                await set_antinsfw(message.chat.id, True)
            elif arg == "off":
                await set_antinsfw(message.chat.id, False)
        else: # antipornadmin
            if arg == "on":
                await set_antinsfw_admin(message.chat.id, True)
            elif arg == "off":
                await set_antinsfw_admin(message.chat.id, False)

    u_mode = await get_antinsfw(message.chat.id)
    a_mode = await get_antinsfw_admin(message.chat.id)

    status_text = (
        f"🛡️ <b>Anti-NSFW Status</b>\n\n"
        f"👥 <b>Users Mode:</b> {'Enabled' if u_mode else 'Disabled'}\n"
        f"👮 <b>Admin Mode:</b> {'Enabled' if a_mode else 'Disabled'}\n\n"
        f"Click the buttons below to toggle."
    )

    await message.reply_text(
        font(status_text),
        reply_markup=await get_antiporn_keyboard(message.chat.id),
        parse_mode=enums.ParseMode.HTML
    )

@pbot.on_callback_query(filters.regex(r"^ap_toggle_"))
async def ap_toggle_cb(_, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(font("❌ This button is for admins only!"), show_alert=True)

    action = query.data.split("_")[-1]

    if action == "user":
        curr = await get_antinsfw(chat_id)
        await set_antinsfw(chat_id, not curr)
    else: # admin
        curr = await get_antinsfw_admin(chat_id)
        await set_antinsfw_admin(chat_id, not curr)

    u_mode = await get_antinsfw(chat_id)
    a_mode = await get_antinsfw_admin(chat_id)

    status_text = (
        f"🛡️ <b>Anti-NSFW Status</b>\n\n"
        f"👥 <b>Users Mode:</b> {'Enabled' if u_mode else 'Disabled'}\n"
        f"👮 <b>Admin Mode:</b> {'Enabled' if a_mode else 'Disabled'}\n\n"
        f"Click the buttons below to toggle."
    )
    
    await query.message.edit_text(
        font(status_text),
        reply_markup=await get_antiporn_keyboard(chat_id),
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer(font("Status Updated"))

@pbot.on_message(filters.command("nsfwstatus", prefixes=prefix_cmds) & filters.group)
async def nsfw_status_cmd(_, message: Message):
    if not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))
    
    status_text = detector.status_html()

    await message.reply_text(font(status_text), parse_mode=enums.ParseMode.HTML)

@pbot.on_message(filters.group & ~filters.bot, group=120)
async def auto_nsfw_check_pyro(client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    
    if user_id and await is_user_approved(chat_id, user_id):
        return
    
    admin_mode = await get_antinsfw_admin(chat_id)
    user_mode = await get_antinsfw(chat_id)
    
    if not admin_mode and not user_mode:
        return
    
    if not detector.loaded:
        return
    
    if user_mode and not admin_mode:
        if await is_user_admin(chat_id, user_id):
            return

    media = message.photo or message.video or message.animation or message.sticker
    if not media:
        if message.document:
            mime = message.document.mime_type or ""
            if "image" in mime or "video" in mime:
                media = message.document
            else: return
        else: return

    if hasattr(media, 'file_size') and media.file_size > 15 * 1024 * 1024:
        return

    try:
        if message.photo:
            file_bytes = await client.download_media(message, in_memory=True)
            if not file_bytes: return
            is_nsfw = await detector.is_nsfw(file_bytes.getvalue())
        else:
            path = await client.download_media(message)
            if not path: return
            try:
                ext = os.path.splitext(str(path))[1].lower()
                if ext in (".jpg", ".jpeg", ".png", ".webp"):      # photo-document / static sticker
                    with open(path, "rb") as fh:
                        is_nsfw = await detector.is_nsfw(fh.read())
                elif ext == ".tgs":                                # animated sticker (lottie) - cannot scan
                    return
                else:                                              # video / gif / video sticker
                    is_nsfw = await detector.check_video_frame(path)
            finally:
                with suppress(Exception): os.remove(path)
        
        if is_nsfw:
            with suppress(Exception): await message.delete()
            
            mention = f"<a href='tg://user?id={user_id}'>{html.escape(message.from_user.first_name if message.from_user else 'User')}</a>"
            warning = await message.reply_text(
                f"🔞 <b>NSFW CONTENT DETECTED!</b>\n\n"
                f"👤 <b>User:</b> {mention}\n"
                f"⚠️ <b>Action:</b> Content removed automatically\n"
                f"🛡️ <b>Reason:</b> Inappropriate content",
                parse_mode=enums.ParseMode.HTML
            )
            await asyncio.sleep(5)
            with suppress(Exception): await warning.delete()
                
    except Exception as e:
        logging.error(f"NSFW Check Error: {e}")
        
