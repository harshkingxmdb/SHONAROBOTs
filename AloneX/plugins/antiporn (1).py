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
import AloneX
from AloneX import pbot, prefix_cmds, font, LOGS_CHANNEL, BOT_USERNAME, init_aiohttp_session
from AloneX.db.approval_db import is_user_approved
from AloneX.db.antinsfw_db import get_antinsfw, set_antinsfw, get_antinsfw_admin, set_antinsfw_admin
import config

__module__ = "𝐀ɴᴛɪ-𝐍sғᴡ🛡️"
__help__ = """
*𝐀ɴᴛɪ-𝐍sғᴡ🛡️* — Protect your group from porn content with AI detection

• `/antiporn` — Toggle anti-NSFW settings or check status.
• `/nsfwstatus` — Check detection model status.

*Behavior:*
Automatically scans photos, stickers, GIFs, videos and video notes (also when a message is edited) and deletes sexual content, including anime / hentai. User mode covers normal users, while Admin mode includes administrators.
"""

# ── detection settings ───────────────────────────────────────────────────────
# NudeNet gives a score for every body part it sees. Explicit parts above their score = delete at once.
EXPLICIT = {
    "FEMALE_GENITALIA_EXPOSED": 0.40,
    "MALE_GENITALIA_EXPOSED": 0.40,
    "ANUS_EXPOSED": 0.40,
    "FEMALE_BREAST_EXPOSED": 0.50,
    "BUTTOCKS_EXPOSED": 0.50,
}
UNSURE_EXPOSED = 0.20        # explicit part seen but weak score -> ask the cloud model (catches anime / drawings)
COVERED = {"FEMALE_BREAST_COVERED", "BUTTOCKS_COVERED", "FEMALE_GENITALIA_COVERED", "ANUS_COVERED"}
UNSURE_COVERED = 0.50        # lewd / lingerie style picture -> ask the cloud model
CLOUD_ALL = os.getenv("NSFW_CLOUD_ALL", "0") == "1"    # 1 = send EVERY image to the cloud model (strictest, uses more API calls)
MAX_BYTES = 15 * 1024 * 1024

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# vision models on Groq, tried in this order (set NSFW_GROQ_MODEL to force one)
GROQ_VISION_MODELS = ("qwen/qwen3.8-27b", "qwen/qwen3.6-27b")
PROMPT = (
    "You are a content-moderation classifier for a Telegram group. Look at the image. It can be a real photo, "
    "an anime, hentai, cartoon or 3D picture, or a sticker. Reply NSFW if it shows nudity (exposed genitals, "
    "nipples or buttocks), a sexual act, or a clearly sexual / lewd pose or outfit meant to arouse "
    "(this includes anime and hentai characters). Normal clothing, swimwear at the beach, medical or "
    "art-class content and non-sexual cartoons are SAFE. Reply with exactly one word: NSFW or SAFE."
)


class NSFWDetector:
    """Anti-NSFW engine, no Gemini needed.

    Step 1 (local, free, no key): NudeNet ONNX model, bundled inside the `nudenet` pip package.
            Obvious explicit content is deleted right here.
    Step 2 (cloud, free): Groq vision model (uses GROQ_API_KEY). Only asked when step 1 is unsure,
            so anime / hentai / lewd pictures are caught without spending API calls on every image.
    """

    def __init__(self):
        self.nude = None
        self.loaded = False
        self.loading = True
        self.reason = ""
        self.groq_key = getattr(config, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY", "")
        self.groq_model = None            # the model that worked last
        self.cloud_reason = ""            # why the cloud step is off (shown in /nsfwstatus)
        self._cloud_off_until = 0.0
        self._cooldown_until = 0.0
        self._cache = OrderedDict()
        self._last_warn = 0.0
        self._local_sem = None
        self._cloud_sem = None
        self._ready = threading.Event()
        threading.Thread(target=self._load_local, daemon=True).start()

    # ---------------- local engine ----------------
    def _load_local(self):
        try:
            from nudenet import NudeDetector

            self.nude = NudeDetector()
        except Exception as e:
            self.reason = f"nudenet not installed ({type(e).__name__}). Add `nudenet` to requirements.txt"
            logging.warning(f"[NSFW] local engine not available: {e}")
        finally:
            self.loaded = bool(self.nude) or bool(self.groq_key)
            self.loading = False
            self._ready.set()

    async def wait_ready(self, timeout=45):
        if self.loaded:
            return True
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._ready.wait, timeout)

    # ---------------- helpers ----------------
    def _warn(self, text: str):
        if time.time() - self._last_warn > 60:      # one warning a minute, a broken API can not flood the logs
            self._last_warn = time.time()
            logging.warning(text)

    @staticmethod
    def _prepare(image_bytes: bytes) -> bytes:
        """any image -> JPEG bytes, longest side <= 640 px"""
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        if max(img.size) > 640:
            img.thumbnail((640, 640), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    @staticmethod
    def local_verdict(detections) -> str:
        """NudeNet detections -> 'nsfw' | 'maybe' | 'safe'"""
        maybe = False
        for d in detections or []:
            label, score = d.get("class"), float(d.get("score", 0))
            if label in EXPLICIT:
                if score >= EXPLICIT[label]:
                    return "nsfw"
                if score >= UNSURE_EXPOSED:
                    maybe = True
            elif label in COVERED and score >= UNSURE_COVERED:
                maybe = True
        return "maybe" if maybe else "safe"

    def _detect(self, jpeg: bytes):
        return self.nude.detect(jpeg)

    # ---------------- cloud engine (Groq vision) ----------------
    def _cloud_ready(self) -> bool:
        return bool(self.groq_key) and time.time() >= max(self._cloud_off_until, self._cooldown_until)

    @staticmethod
    def _parse_groq(data: dict):
        """-> True (nsfw) / False (safe) / None (no usable answer)"""
        try:
            text = data["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError, AttributeError):
            return None
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip().upper()
        if not text:
            return None
        if text.startswith("NSFW"):
            return True
        if text.startswith("SAFE"):
            return False
        return True if ("NSFW" in text and "SAFE" not in text) else (False if "SAFE" in text else None)

    async def _groq(self, jpeg: bytes):
        if not self._cloud_ready():
            return None
        if AloneX.aiohttpsession is None or AloneX.aiohttpsession.closed:
            await init_aiohttp_session()
        if self._cloud_sem is None:
            self._cloud_sem = asyncio.Semaphore(3)

        forced = os.getenv("NSFW_GROQ_MODEL", "")
        models = [forced] if forced else list(GROQ_VISION_MODELS)
        if self.groq_model in models:
            models.remove(self.groq_model)
            models.insert(0, self.groq_model)

        image_url = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()
        messages = [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]}]
        headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
        last = ""

        async with self._cloud_sem:
            for model in models:
                for extra in ({"reasoning_effort": "none"}, {}):       # 2nd try without optional params
                    payload = {"model": model, "messages": messages, "temperature": 0,
                               "max_completion_tokens": 300, **extra}
                    try:
                        async with AloneX.aiohttpsession.post(
                            GROQ_URL, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
                        ) as r:
                            status = r.status
                            body = await r.json(content_type=None)
                    except Exception as e:
                        self._warn(f"[NSFW] Groq request failed: {type(e).__name__}")
                        return None

                    if status == 200:
                        self.groq_model = model
                        return self._parse_groq(body)
                    msg = ((body.get("error") or {}).get("message", "")) if isinstance(body, dict) else ""
                    last = f"HTTP {status}: {re.sub(r'[^A-Za-z0-9 .,:()_/-]', ' ', msg)[:90]}"
                    if status == 429:
                        self._cooldown_until = time.time() + 60
                        self._warn("[NSFW] Groq rate limit (HTTP 429) - cloud step paused for 60 s.")
                        return None
                    if status in (401, 403):
                        self._cloud_off_until = time.time() + 600
                        self.cloud_reason = f"Groq key not accepted ({last}). Set a valid GROQ_API_KEY"
                        logging.error(f"[NSFW] {self.cloud_reason}")
                        return None
                    if status == 400 and extra:
                        continue                  # retry this model without optional params
                    break                         # 404 / 5xx -> next model
        self.cloud_reason = f"No Groq vision model worked ({last}). Set NSFW_GROQ_MODEL"
        self._warn(f"[NSFW] {self.cloud_reason}")
        return None

    # ---------------- public api ----------------
    async def is_nsfw(self, image_bytes: bytes) -> bool:
        try:
            if not self.loaded:
                await self.wait_ready()
            if not self.loaded:
                return False

            key = hashlib.md5(image_bytes).hexdigest()
            if key in self._cache:
                return self._cache[key]

            loop = asyncio.get_event_loop()
            jpeg = await loop.run_in_executor(None, self._prepare, image_bytes)

            verdict = "maybe"                        # no local engine -> let the cloud model decide
            if self.nude:
                if self._local_sem is None:
                    self._local_sem = asyncio.Semaphore(2)
                async with self._local_sem:
                    detections = await loop.run_in_executor(None, self._detect, jpeg)
                verdict = self.local_verdict(detections)
                if verdict == "safe" and CLOUD_ALL:
                    verdict = "maybe"

            if verdict == "nsfw":
                result = True
            elif verdict == "safe":
                result = False
            else:
                answer = await self._groq(jpeg)
                if answer is None:                   # cloud unavailable: do not cache, fail open
                    return False
                result = answer

            self._cache[key] = result
            if len(self._cache) > 500:
                self._cache.popitem(last=False)
            return result
        except Exception as e:
            self._warn(f"[NSFW] is_nsfw error: {type(e).__name__}: {e}")
            return False

    @staticmethod
    def _grab_frames(video_path: str, count: int = 3):
        import cv2

        frames = []
        cap = cv2.VideoCapture(video_path)
        try:
            if not cap.isOpened():
                return frames
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            positions = (0.1, 0.5, 0.85)[:count] if total > 6 else (0,)
            for p in positions:
                if total > 6:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * p))
                ok, frame = cap.read()
                if ok and frame is not None:
                    ok2, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if ok2:
                        frames.append(buf.tobytes())
        finally:
            cap.release()
        return frames

    async def check_video_frame(self, video_path: str) -> bool:
        """GIF / video / video sticker / video note: look at 3 frames (start, middle, end)."""
        try:
            loop = asyncio.get_event_loop()
            frames = await loop.run_in_executor(None, self._grab_frames, video_path)
            for frame in frames:
                if await self.is_nsfw(frame):
                    return True
        except Exception as e:
            self._warn(f"[NSFW] video check error: {type(e).__name__}: {e}")
        return False

    def status_html(self) -> str:
        if not self.loaded:
            if self.loading:
                return "🔄 <b>Model Loading...</b>\n\n⏳ Please wait, model will be ready soon"
            return (
                "❌ <b>Model Failed</b>\n\n"
                "🐛 NSFW detection is currently <b>disabled</b>\n"
                f"ℹ️ <b>Reason:</b> {html.escape(self.reason or 'no engine available. Install nudenet or set GROQ_API_KEY')}"
            )
        local = "✅ NudeNet (local, no key)" if self.nude else f"❌ off ({html.escape(self.reason or 'not installed')})"
        if not self.groq_key:
            cloud = "❌ off (GROQ_API_KEY not set)"
        elif self.cloud_reason and time.time() < self._cloud_off_until:
            cloud = f"❌ {html.escape(self.cloud_reason)}"
        elif time.time() < self._cooldown_until:
            cloud = "⏸ paused (rate limit), back in a minute"
        else:
            cloud = f"✅ Groq vision ({html.escape(self.groq_model or 'auto model')})"
        mode = "Strict (every image checked by cloud)" if CLOUD_ALL else "Smart (cloud only when unsure)"
        return (
            "✅ <b>Model Status: Ready</b>\n\n"
            f"🧠 <b>Local engine:</b> {local}\n"
            f"☁️ <b>Cloud engine:</b> {cloud}\n"
            f"🎯 <b>Mode:</b> {mode}\n"
            "🎞 <b>Scans:</b> photos, stickers, GIFs, videos, video notes, edited messages"
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

_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
_perm_warned = {}


def _has_media(message: Message) -> bool:
    if message.photo or message.video or message.animation or message.sticker or message.video_note:
        return True
    if message.document:
        mime = message.document.mime_type or ""
        return mime.startswith(("image", "video"))
    return False


async def _scan_thumb(client, media) -> bool:
    """Preview picture of a big file / animated sticker (.tgs can not be decoded)."""
    thumbs = getattr(media, "thumbs", None) or []
    if not thumbs:
        return False
    data = await client.download_media(thumbs[-1].file_id, in_memory=True)
    return bool(data) and await detector.is_nsfw(data.getvalue())


async def _scan_message(client, message: Message) -> bool:
    media = (message.photo or message.video or message.animation or message.sticker
             or message.video_note or message.document)
    size = getattr(media, "file_size", 0) or 0

    if message.photo and size <= MAX_BYTES:
        data = await client.download_media(message, in_memory=True)
        return bool(data) and await detector.is_nsfw(data.getvalue())

    if size > MAX_BYTES or (message.sticker and message.sticker.is_animated):
        return await _scan_thumb(client, media)

    path = await client.download_media(message)
    if not path:
        return False
    try:
        ext = os.path.splitext(str(path))[1].lower()
        if ext in _IMAGE_EXT:                      # photo-document / static sticker
            with open(path, "rb") as fh:
                return await detector.is_nsfw(fh.read())
        if ext == ".tgs":                          # animated sticker
            return await _scan_thumb(client, media)
        return await detector.check_video_frame(path)   # video / gif / video sticker / video note
    finally:
        with suppress(Exception):
            os.remove(path)


async def _delete_later(msg: Message, seconds: int = 8):
    await asyncio.sleep(seconds)
    with suppress(Exception):
        await msg.delete()


@pbot.on_message(filters.group & ~filters.bot, group=120)
@pbot.on_edited_message(filters.group & ~filters.bot, group=120)
async def auto_nsfw_check_pyro(client, message: Message):
    if not _has_media(message):                    # cheap check first: no DB calls for plain text
        return

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

    try:
        if not await _scan_message(client, message):
            return

        try:
            await message.delete()
        except Exception as e:
            # no "Delete messages" right: tell the admins once in a while instead of spamming
            if time.time() - _perm_warned.get(chat_id, 0) > 600:
                _perm_warned[chat_id] = time.time()
                with suppress(Exception):
                    await message.reply_text(font("⚠️ NSFW content found but I can't delete it. Please give me the 'Delete messages' right."))
            logging.warning(f"[NSFW] delete failed in {chat_id}: {type(e).__name__}")
            return

        name = html.escape(message.from_user.first_name) if message.from_user else "User"
        mention = f"<a href='tg://user?id={user_id}'>{name}</a>" if user_id else name
        warning = await message.reply_text(
            f"🔞 <b>NSFW CONTENT DETECTED!</b>\n\n"
            f"👤 <b>User:</b> {mention}\n"
            f"⚠️ <b>Action:</b> Content removed automatically\n"
            f"🛡️ <b>Reason:</b> Inappropriate content",
            parse_mode=enums.ParseMode.HTML,
            quote=False,
        )
        asyncio.create_task(_delete_later(warning))

    except Exception as e:
        logging.error(f"NSFW Check Error: {type(e).__name__}: {e}")
