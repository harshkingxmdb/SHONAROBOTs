import io
import os
import re
import time
import base64
import hashlib
import logging
import asyncio
import threading
import shutil
import tempfile
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
    "FEMALE_GENITALIA_EXPOSED": 0.35,
    "MALE_GENITALIA_EXPOSED": 0.35,
    "ANUS_EXPOSED": 0.35,
    "FEMALE_BREAST_EXPOSED": 0.40,
    "BUTTOCKS_EXPOSED": 0.45,
}
UNSURE_EXPOSED = 0.20        # explicit part seen but weak score -> ask the cloud model (catches anime / drawings)
COVERED = {"FEMALE_BREAST_COVERED", "BUTTOCKS_COVERED", "FEMALE_GENITALIA_COVERED", "ANUS_COVERED"}
UNSURE_COVERED = 0.50        # lewd / lingerie style picture -> ask the cloud model
CLOUD_ALL = bool(getattr(config, "NSFW_CLOUD_ALL", True))    # config.py: True = every image / video also goes to the cloud model (catches kissing, bra, panty, anime ...)
VIDEO_FRAMES = 4             # frames looked at in a GIF / video (joined into ONE picture = ONE cloud call)
MAX_BYTES = 15 * 1024 * 1024

# Cloudflare Workers AI (free: 10,000 neurons per day). Vision models, tried in this order
# (set NSFW_CF_MODEL to force one). One picture costs only a few neurons.
CF_RUN_URL = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
CF_VISION_MODELS = ("@cf/meta/llama-3.2-11b-vision-instruct", "@cf/meta/llama-4-scout-17b-16e-instruct")
PROMPT = (
    "You are a strict content-moderation classifier for a Telegram group. Look at the picture. It can be a real "
    "photo, an anime, hentai, cartoon or 3D picture, a sticker, or a grid of several video frames (then answer "
    "NSFW if ANY frame is NSFW). Reply NSFW if it shows ANY of these: nudity or exposed genitals, nipples, "
    "buttocks or underboob; a sex act or sexual touching; people kissing on the lips, making out or romantic / "
    "erotic kissing; a person in only underwear or lingerie (bra, panties, thong), see-through clothes; a lewd, "
    "seductive or sexual pose; sexual anime / hentai / ecchi characters. Reply SAFE for normal clothed people, "
    "family affection, swimwear at a beach or pool, medical or educational pictures and non-sexual cartoons. "
    "Reply with exactly one word: NSFW or SAFE."
)


class NSFWDetector:
    """Anti-NSFW engine, no Gemini needed.

    Step 1 (local, free, no key): NudeNet ONNX model, bundled inside the `nudenet` pip package.
            Obvious explicit content is deleted right here.
    Step 2 (cloud, free): Cloudflare Workers AI vision model (uses CF_ACCOUNT_ID + CF_API_TOKEN).
            Sees kissing, underwear, lewd anime ... that the local model can not. In strict mode
            (NSFW_CLOUD_ALL in config.py) every picture goes through it.
    """

    def __init__(self):
        self.nude = None
        self.loaded = False
        self.loading = True
        self.reason = ""
        self.cf_account = getattr(config, "CF_ACCOUNT_ID", "") or os.getenv("CF_ACCOUNT_ID", "")
        self.cf_token = getattr(config, "CF_API_TOKEN", "") or os.getenv("CF_API_TOKEN", "")
        self.cf_model = None              # the model that worked last
        self._cf_variant = 0              # the request format that worked last
        self._cf_agreed = set()           # models whose license ("agree") was already sent
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
            self.loaded = bool(self.nude) or self._cloud_configured()
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

    async def _local(self, jpeg: bytes) -> str:
        """NudeNet on one picture -> 'nsfw' | 'maybe' | 'safe'"""
        if self._local_sem is None:
            self._local_sem = asyncio.Semaphore(2)
        loop = asyncio.get_event_loop()
        async with self._local_sem:
            detections = await loop.run_in_executor(None, self._detect, jpeg)
        return self.local_verdict(detections)

    # ---------------- cloud engine (Cloudflare Workers AI vision) ----------------
    def _cloud_configured(self) -> bool:
        return bool(self.cf_account and self.cf_token)

    def _cloud_ready(self) -> bool:
        return self._cloud_configured() and time.time() >= max(self._cloud_off_until, self._cooldown_until)

    @staticmethod
    def _parse_verdict(text):
        """model answer -> True (nsfw) / False (safe) / None (no usable answer)"""
        text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).replace("\u2019", "'").strip().upper()
        if not text:
            return None
        if text.startswith("NSFW"):
            return True
        if text.startswith("SAFE"):
            return False
        if "NOT SAFE" in text or "UNSAFE" in text:
            return True
        if "NOT NSFW" in text or "NON-NSFW" in text:
            return False
        # the model refuses to describe the picture: that only happens for explicit pictures
        if re.match(r"^(I CAN'?T|I CANNOT|I AM UNABLE|I'M UNABLE|I'M NOT ABLE|I'M SORRY|I AM SORRY|SORRY|I WON'?T|UNABLE)", text):
            return True
        if "NSFW" in text and "SAFE" not in text:
            return True
        if "SAFE" in text and "NSFW" not in text:
            return False
        return None

    @staticmethod
    def _cf_text(body) -> str:
        res = body.get("result") if isinstance(body, dict) else None
        if not isinstance(res, dict):
            return ""
        if isinstance(res.get("response"), str):
            return res["response"]
        try:
            return res["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError, AttributeError):
            return ""

    @staticmethod
    def _cf_error(body) -> str:
        errs = body.get("errors") if isinstance(body, dict) else None
        msg = " ".join(str(e.get("message", "")) for e in (errs or []) if isinstance(e, dict))
        return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 .,:()_/'-]", " ", msg)).strip()[:140]

    @staticmethod
    def _secs_to_utc_midnight() -> float:
        now = time.time()
        return 86400 - (now % 86400)

    async def _cf_agree(self, session, url: str, headers: dict):
        """Meta models want a one-time 'agree' to their license before the first use."""
        with suppress(Exception):
            async with session.post(url, json={"prompt": "agree"}, headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=30)) as r:
                await r.read()

    async def _cloud(self, jpeg: bytes):
        """Picture -> True (nsfw) / False (safe) / None (cloud not available or no answer)."""
        if not self._cloud_ready():
            return None
        if AloneX.aiohttpsession is None or AloneX.aiohttpsession.closed:
            await init_aiohttp_session()
        if self._cloud_sem is None:
            self._cloud_sem = asyncio.Semaphore(3)
        session = AloneX.aiohttpsession

        forced = os.getenv("NSFW_CF_MODEL", "")
        models = [forced] if forced else list(CF_VISION_MODELS)
        if self.cf_model in models:
            models.remove(self.cf_model)
            models.insert(0, self.cf_model)

        data_uri = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()
        variants = (
            # 0: the way Cloudflare's own Llama 3.2 vision tutorial sends a picture
            {"messages": [{"role": "user", "content": PROMPT}], "image": data_uri, "max_tokens": 12, "temperature": 0},
            # 1: OpenAI style message parts
            {"messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": data_uri}},
            ]}], "max_tokens": 12, "temperature": 0},
        )
        order = [self._cf_variant] + [i for i in (0, 1) if i != self._cf_variant]
        headers = {"Authorization": f"Bearer {self.cf_token}", "Content-Type": "application/json"}
        last = ""

        async with self._cloud_sem:
            for model in models:
                url = CF_RUN_URL.format(account=self.cf_account, model=model)
                k = 0
                while k < len(order):
                    try:
                        async with session.post(url, json=variants[order[k]], headers=headers,
                                                timeout=aiohttp.ClientTimeout(total=30)) as r:
                            status = r.status
                            body = await r.json(content_type=None)
                    except Exception as e:
                        self._warn(f"[NSFW] Cloudflare request failed: {type(e).__name__}")
                        return None

                    if status == 200 and isinstance(body, dict) and body.get("success", True):
                        verdict = self._parse_verdict(self._cf_text(body))
                        if verdict is None:
                            last = "empty answer"
                            break                                     # try the next model
                        self.cf_model, self._cf_variant = model, order[k]
                        return verdict

                    err = self._cf_error(body)
                    last = f"HTTP {status}: {err}"
                    low = err.lower()
                    if "agree" in low and model not in self._cf_agreed:
                        self._cf_agreed.add(model)
                        await self._cf_agree(session, url, headers)
                        continue                                      # same request again
                    if status == 429 or "neurons" in low or "daily" in low or "allocation" in low:
                        if "neurons" in low or "daily" in low or "allocation" in low:
                            self._cloud_off_until = time.time() + self._secs_to_utc_midnight()
                            self.cloud_reason = "daily free limit (10,000 neurons) used up, comes back at 00:00 UTC"
                            logging.error(f"[NSFW] {self.cloud_reason}")
                        else:
                            self._cooldown_until = time.time() + 60
                            self._warn("[NSFW] Cloudflare rate limit (HTTP 429) - cloud step paused for 60 s.")
                        return None
                    if status in (401, 403):
                        self._cloud_off_until = time.time() + 600
                        self.cloud_reason = (f"Cloudflare token not accepted ({last}). Check CF_ACCOUNT_ID and CF_API_TOKEN "
                                             "(token needs the 'Workers AI' permission)")
                        logging.error(f"[NSFW] {self.cloud_reason}")
                        return None
                    if status == 400:
                        k += 1                                        # try the other request format
                        continue
                    break                                             # 404 / 5xx -> next model
        self.cloud_reason = f"No Cloudflare vision model worked ({last}). Set NSFW_CF_MODEL"
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
                verdict = await self._local(jpeg)
                if verdict == "safe" and CLOUD_ALL:
                    verdict = "maybe"

            if verdict == "nsfw":
                result = True
            elif verdict == "safe":
                result = False
            else:
                answer = await self._cloud(jpeg)
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
    def _grab_frames(video_path: str, count: int = VIDEO_FRAMES):
        import cv2

        frames = []
        cap = cv2.VideoCapture(video_path)
        try:
            if not cap.isOpened():
                return frames
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            spots = (0.05, 0.3, 0.6, 0.9)[:count] if total > 8 else (0,)
            for p in spots:
                if total > 8:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * p))
                ok, frame = cap.read()
                if ok and frame is not None:
                    ok2, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if ok2:
                        frames.append(buf.tobytes())
        finally:
            cap.release()
        return frames

    @staticmethod
    def _collage(jpegs) -> bytes:
        """up to 4 frames -> one 2x2 picture, so a whole video costs ONE cloud call"""
        from PIL import Image

        cell = 360
        cols = 2 if len(jpegs) > 1 else 1
        rows = (len(jpegs) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * cell), (0, 0, 0))
        for i, data in enumerate(jpegs):
            img = Image.open(io.BytesIO(data)).convert("RGB")
            img.thumbnail((cell, cell), Image.Resampling.LANCZOS)
            x = (i % cols) * cell + (cell - img.width) // 2
            y = (i // cols) * cell + (cell - img.height) // 2
            sheet.paste(img, (x, y))
        buf = io.BytesIO()
        sheet.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    async def check_frames(self, frames) -> bool:
        if not self.loaded:
            await self.wait_ready()
        if not self.loaded or not frames:
            return False
        loop = asyncio.get_event_loop()
        jpegs = list(await asyncio.gather(*[loop.run_in_executor(None, self._prepare, f) for f in frames]))

        verdicts = ["maybe"] * len(jpegs)
        if self.nude:
            verdicts = list(await asyncio.gather(*[self._local(j) for j in jpegs]))   # all frames at the same time
            if "nsfw" in verdicts:
                return True                                                            # obvious: no cloud call needed
        if not (CLOUD_ALL or "maybe" in verdicts):
            return False

        sheet = await loop.run_in_executor(None, self._collage, jpegs)
        key = hashlib.md5(sheet).hexdigest()
        if key in self._cache:
            return self._cache[key]
        answer = await self._cloud(sheet)
        if answer is None:                                    # cloud unavailable: fail open, do not cache
            return False
        self._cache[key] = answer
        if len(self._cache) > 500:
            self._cache.popitem(last=False)
        return answer

    async def check_video_frame(self, video_path: str) -> bool:
        """GIF / video / video sticker / video note."""
        try:
            loop = asyncio.get_event_loop()
            frames = await loop.run_in_executor(None, self._grab_frames, video_path)
            return await self.check_frames(frames)
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
                f"ℹ️ <b>Reason:</b> {html.escape(self.reason or 'no engine available. Install nudenet or set CF_ACCOUNT_ID and CF_API_TOKEN')}"
            )
        local = "✅ NudeNet (local, no key)" if self.nude else f"❌ off ({html.escape(self.reason or 'not installed')})"
        if not self._cloud_configured():
            cloud = "❌ off (CF_ACCOUNT_ID / CF_API_TOKEN not set)"
        elif self.cloud_reason and time.time() < self._cloud_off_until:
            cloud = f"❌ {html.escape(self.cloud_reason)}"
        elif time.time() < self._cooldown_until:
            cloud = "⏸ paused (rate limit), back in a minute"
        else:
            cloud = f"✅ Cloudflare Workers AI ({html.escape((self.cf_model or 'auto model').replace('@cf/', ''))})"
        mode = "Strict: every picture / video also checked by the cloud model" if CLOUD_ALL else "Smart: cloud only when the local detector is unsure"
        return (
            "✅ <b>Model Status: Ready</b>\n\n"
            f"🧠 <b>Local engine:</b> {local}\n"
            f"☁️ <b>Cloud engine:</b> {cloud}\n"
            f"🎯 <b>Mode:</b> {mode}\n"
            "🎞 <b>Scans:</b> photos, stickers, GIFs, videos, video notes, edited messages\n🚫 <b>Deletes:</b> nudity, sex, kissing, bra / panty, lewd anime"
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

_perm_warned = {}
_tasks = set()


def _spawn(coro):
    t = asyncio.create_task(coro)           # keep a reference, otherwise Python may drop the task
    _tasks.add(t)
    t.add_done_callback(_tasks.discard)
    return t


def _has_media(message: Message) -> bool:
    if message.photo or message.video or message.animation or message.sticker or message.video_note:
        return True
    if message.document:
        mime = message.document.mime_type or ""
        return mime.startswith(("image", "video"))
    return False


def _is_still_image(message: Message) -> bool:
    if message.photo:
        return True
    if message.sticker:
        return not (message.sticker.is_animated or message.sticker.is_video)
    if message.document:
        return (message.document.mime_type or "").startswith("image")
    return False


async def _scan_thumb(client, media) -> bool:
    """The small preview Telegram already has: a few KB, so it is checked almost at once."""
    thumbs = getattr(media, "thumbs", None) or []
    if not thumbs:
        return False
    data = await client.download_media(thumbs[-1].file_id, in_memory=True)
    return bool(data) and await detector.is_nsfw(data.getvalue())


async def _scan_full(client, message: Message) -> bool:
    tmp = tempfile.mkdtemp(prefix="nsfw_")
    try:
        path = await client.download_media(message, file_name=tmp + os.sep)
        if not path:
            return False
        if _is_still_image(message):
            with open(path, "rb") as fh:
                return await detector.is_nsfw(fh.read())
        return await detector.check_video_frame(str(path))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)            # also removes half downloaded files


async def _scan_message(client, message: Message) -> bool:
    media = (message.photo or message.video or message.animation or message.sticker
             or message.video_note or message.document)
    size = getattr(media, "file_size", 0) or 0

    if message.photo and size <= MAX_BYTES:
        data = await client.download_media(message, in_memory=True)
        return bool(data) and await detector.is_nsfw(data.getvalue())

    # preview and full file are checked AT THE SAME TIME, the first one that finds NSFW wins
    jobs = {asyncio.create_task(_scan_thumb(client, media))}
    animated = bool(message.sticker and message.sticker.is_animated)      # .tgs can not be decoded, preview only
    if size <= MAX_BYTES and not animated:
        jobs.add(asyncio.create_task(_scan_full(client, message)))
    pending = set(jobs)
    try:
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for t in done:
                try:
                    if t.result():
                        return True
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logging.warning(f"[NSFW] scan part failed: {type(e).__name__}: {e}")
        return False
    finally:
        for t in pending:
            t.cancel()


async def _delete_later(msg: Message, seconds: int = 8):
    await asyncio.sleep(seconds)
    with suppress(Exception):
        await msg.delete()


async def _warn_user(message: Message, user_id: int):
    try:
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
        _spawn(_delete_later(warning))
    except Exception as e:
        logging.warning(f"[NSFW] warning message failed: {type(e).__name__}")


async def _no_user_approved():
    return False


async def _process(client, message: Message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id if message.from_user else 0
        if not detector.loaded:
            return

        approved, admin_mode, user_mode = await asyncio.gather(
            is_user_approved(chat_id, user_id) if user_id else _no_user_approved(),
            get_antinsfw_admin(chat_id),
            get_antinsfw(chat_id),
        )
        if approved or not (admin_mode or user_mode):
            return
        if user_mode and not admin_mode and await is_user_admin(chat_id, user_id):
            return

        if not await _scan_message(client, message):
            return

        try:
            await message.delete()                       # delete FIRST, talk afterwards
        except Exception as e:
            # no "Delete messages" right: tell the admins once in a while instead of spamming
            if time.time() - _perm_warned.get(chat_id, 0) > 600:
                _perm_warned[chat_id] = time.time()
                with suppress(Exception):
                    await message.reply_text(font("⚠️ NSFW content found but I can't delete it. Please give me the 'Delete messages' right."))
            logging.warning(f"[NSFW] delete failed in {chat_id}: {type(e).__name__}")
            return
        _spawn(_warn_user(message, user_id))

    except Exception as e:
        logging.error(f"NSFW Check Error: {type(e).__name__}: {e}")


# group=-500: runs BEFORE the other plugins and returns at once, the scan itself runs in the background,
# so a slow handler in another plugin can no longer delay the deletion.
@pbot.on_message(filters.group & ~filters.bot, group=-500)
@pbot.on_edited_message(filters.group & ~filters.bot, group=-500)
async def auto_nsfw_check_pyro(client, message: Message):
    if _has_media(message):
        _spawn(_process(client, message))
