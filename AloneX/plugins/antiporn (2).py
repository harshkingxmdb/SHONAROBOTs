import io
import os
import re
import time
import base64
import hashlib
import logging
import asyncio
import threading
import glob
import shutil
import subprocess
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

# Cloud engines, same as the old NSFW module: HuggingFace space (no key) + API4AI demo (key).
# Both are checked for every unsure picture; if either one says NSFW the picture is deleted.
HF_NSFW_API = "https://nexacoders-nexa-api.hf.space/scan"
API4AI_URL = "https://demo.api4ai.cloud/nsfw/v1/results"
API4AI_KEY = os.getenv("API4AI_KEY", "a4a-p3htHPSXFeCnvAZ21nLkRtRPGUFFTaJV")
CLOUD_TIMEOUT = 10             # seconds per cloud engine (was 25: one sleeping engine delayed every deletion)
ENGINE_COOLDOWN = 120          # an engine that failed is skipped for this many seconds
NSFW_PERCENT = 60            # same threshold as the old NSFW module


class NSFWDetector:
    """Anti-NSFW engine, no Gemini needed.

    Step 1 (local, free, no key): NudeNet ONNX model, bundled inside the `nudenet` pip package.
            Obvious explicit content is deleted right here.
    Step 2 (cloud): HuggingFace NSFW space + API4AI, both run together. Sees kissing, underwear,
            lewd anime ... that the local model can not. In strict mode (NSFW_CLOUD_ALL in config.py)
            every picture goes through them.
    """

    def __init__(self):
        self.nude = None
        self.loaded = False
        self.loading = True
        self.reason = ""
        self.cloud_reason = ""            # why the cloud step is off (shown in /nsfwstatus)
        self._cloud_off_until = 0.0
        self._cooldown_until = 0.0
        self._engines = {                 # state of each cloud engine, shown in /nsfwstatus
            "HuggingFace": {"off_until": 0.0, "error": ""},
            "API4AI": {"off_until": 0.0, "error": ""},
        }
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
        # NudeNet reads a FILE PATH, not bytes. Passing bytes made the local engine fail on every picture.
        fd, path = tempfile.mkstemp(suffix=".jpg")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(jpeg)
            return self.nude.detect(path)
        finally:
            with suppress(OSError):
                os.remove(path)

    async def _local(self, jpeg: bytes) -> str:
        """NudeNet on one picture -> 'nsfw' | 'maybe' | 'safe'"""
        if self._local_sem is None:
            self._local_sem = asyncio.Semaphore(2)
        loop = asyncio.get_event_loop()
        async with self._local_sem:
            detections = await loop.run_in_executor(None, self._detect, jpeg)
        return self.local_verdict(detections)

    # ---------------- cloud engines: HuggingFace + API4AI ----------------
    def _cloud_configured(self) -> bool:
        return True                               # HuggingFace needs no key, API4AI has one built in

    def _cloud_ready(self) -> bool:
        return True

    async def _hf_nsfw(self, jpeg: bytes):
        """HuggingFace space -> (is_nsfw, scores in %)"""
        if AloneX.aiohttpsession is None or AloneX.aiohttpsession.closed:
            await init_aiohttp_session()
        form = aiohttp.FormData()
        form.add_field("file", jpeg, filename="scan.jpg", content_type="image/jpeg")
        async with AloneX.aiohttpsession.post(
            HF_NSFW_API, data=form, timeout=aiohttp.ClientTimeout(total=CLOUD_TIMEOUT)
        ) as r:
            if r.status != 200:
                raise RuntimeError(f"HTTP {r.status}")
            scores = (await r.json(content_type=None))["scores"]
        porn = scores.get("porn", 0) * 100
        hentai = scores.get("hentai", 0) * 100
        sexy = scores.get("sexy", 0) * 100
        return (porn + hentai + sexy) >= NSFW_PERCENT, {"porn": porn, "hentai": hentai, "sexy": sexy}

    async def _api4ai_nsfw(self, jpeg: bytes):
        """API4AI demo -> (is_nsfw, scores in %)"""
        if AloneX.aiohttpsession is None or AloneX.aiohttpsession.closed:
            await init_aiohttp_session()
        form = aiohttp.FormData()
        form.add_field("image", jpeg, filename="scan.jpg", content_type="image/jpeg")
        async with AloneX.aiohttpsession.post(
            API4AI_URL, data=form, headers={"A4AI-KEY": API4AI_KEY},
            timeout=aiohttp.ClientTimeout(total=CLOUD_TIMEOUT),
        ) as r:
            if r.status != 200:
                raise RuntimeError(f"HTTP {r.status}")
            data = await r.json(content_type=None)
        results = data.get("results") or []
        entities = (results[0].get("entities") or []) if results else []
        classes = (entities[0].get("classes") or {}) if entities else {}
        if not classes:
            raise RuntimeError("empty result")
        scores = {k: round(float(v) * 100, 2) for k, v in classes.items()}
        return scores.get("nsfw", 0) >= NSFW_PERCENT, scores

    def _engine_ok(self, name: str) -> bool:
        return time.time() >= self._engines[name]["off_until"]

    def _engine_fail(self, name: str, err: str):
        st = self._engines[name]
        st["off_until"] = time.time() + ENGINE_COOLDOWN
        st["error"] = err
        self._warn(f"[NSFW] {name} failed: {err} - skipped for {ENGINE_COOLDOWN}s")

    def _engine_good(self, name: str):
        st = self._engines[name]
        st["off_until"] = 0.0
        st["error"] = ""

    async def _cloud(self, jpeg: bytes):
        """-> True (nsfw) / False (safe) / None (no cloud engine answered).

        Both engines run at the same time. The FIRST engine that says NSFW wins at once, so a slow or sleeping
        engine can no longer delay a deletion. An engine that failed is skipped for ENGINE_COOLDOWN seconds."""
        if self._cloud_sem is None:
            self._cloud_sem = asyncio.Semaphore(3)
        runners = {"HuggingFace": self._hf_nsfw, "API4AI": self._api4ai_nsfw}
        names = [n for n in runners if self._engine_ok(n)]
        if not names:
            return None

        async with self._cloud_sem:
            jobs = {asyncio.create_task(runners[n](jpeg)): n for n in names}
            pending = set(jobs)
            answered = False
            try:
                while pending:
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                    for t in done:
                        name = jobs[t]
                        try:
                            nsfw, _scores = t.result()
                        except Exception as e:
                            self._engine_fail(name, f"{type(e).__name__}: {e}"[:120])
                            continue
                        self._engine_good(name)
                        answered = True
                        if nsfw:
                            return True
            finally:
                for t in pending:
                    t.cancel()
        return False if answered else None

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

    @staticmethod
    def _ffmpeg_frames(video_path: str, count: int = VIDEO_FRAMES):
        out_dir = tempfile.mkdtemp(prefix="nsfwf_")
        try:
            subprocess.run(
                ["ffmpeg", "-v", "error", "-i", video_path, "-vf", "fps=1,scale=480:-2",
                 "-frames:v", str(count), "-q:v", "4", os.path.join(out_dir, "f%02d.jpg")],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=40, check=False,
            )
            frames = []
            for path in sorted(glob.glob(os.path.join(out_dir, "f*.jpg"))):
                with open(path, "rb") as fh:
                    frames.append(fh.read())
            return frames
        except Exception:
            return []
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    async def check_video_frame(self, video_path: str) -> bool:
        """GIF / video / video sticker / video note."""
        try:
            loop = asyncio.get_event_loop()
            frames = await loop.run_in_executor(None, self._grab_frames, video_path)
            if not frames:                                   # OpenCV could not decode it -> ffmpeg (is in Aptfile)
                frames = await loop.run_in_executor(None, self._ffmpeg_frames, video_path)
            if not frames:
                self._warn("[NSFW] could not read any frame from a video / GIF, it was NOT scanned")
                return False
            return await self.check_frames(frames)
        except Exception as e:
            self._warn(f"[NSFW] video check error: {type(e).__name__}: {e}")
        return False

    async def diagnose(self, image_bytes: bytes) -> str:
        """Runs every engine on one picture and reports result, time and error of each (for /nsfwtest)."""
        loop = asyncio.get_event_loop()
        lines = []
        try:
            jpeg = await loop.run_in_executor(None, self._prepare, image_bytes)
        except Exception as e:
            return f"❌ <b>Could not read the picture:</b> {html.escape(type(e).__name__)}"

        local_flag = False
        if self.nude:
            t0 = time.time()
            try:
                dets = await loop.run_in_executor(None, self._detect, jpeg)
                verdict = self.local_verdict(dets)
                local_flag = verdict == "nsfw"
                top = sorted(dets or [], key=lambda d: -float(d.get("score", 0)))[:5]
                seen = ", ".join(f"{d['class']} {float(d['score']) * 100:.0f}%" for d in top) or "nothing found"
                lines.append(f"🧠 <b>NudeNet:</b> {verdict.upper()} ({time.time() - t0:.1f}s)\n    <code>{html.escape(seen)}</code>")
            except Exception as e:
                lines.append(f"🧠 <b>NudeNet:</b> ❌ {html.escape(type(e).__name__)}: {html.escape(str(e))[:100]}")
        else:
            lines.append(f"🧠 <b>NudeNet:</b> ❌ off ({html.escape(self.reason or 'not installed')})")

        cloud_flag = False
        for name, fn in (("HuggingFace", self._hf_nsfw), ("API4AI", self._api4ai_nsfw)):
            t0 = time.time()
            try:
                nsfw, scores = await fn(jpeg)
                cloud_flag = cloud_flag or nsfw
                shown = ", ".join(f"{k} {v:.0f}%" for k, v in sorted(scores.items(), key=lambda kv: -kv[1])[:3])
                lines.append(f"☁️ <b>{name}:</b> {'NSFW' if nsfw else 'safe'} ({time.time() - t0:.1f}s)\n    <code>{html.escape(shown)}</code>")
            except Exception as e:
                lines.append(f"☁️ <b>{name}:</b> ❌ {html.escape(type(e).__name__)}: {html.escape(str(e))[:100]} ({time.time() - t0:.1f}s)")

        final = local_flag or cloud_flag
        lines.append(f"\n🎯 <b>Result:</b> {'🔞 NSFW, would be deleted' if final else '✅ safe, would NOT be deleted'}")
        return "\n".join(lines)

    def status_html(self) -> str:
        if not self.loaded:
            if self.loading:
                return "🔄 <b>Model Loading...</b>\n\n⏳ Please wait, model will be ready soon"
            return (
                "❌ <b>Model Failed</b>\n\n"
                "🐛 NSFW detection is currently <b>disabled</b>\n"
                f"ℹ️ <b>Reason:</b> {html.escape(self.reason or 'no engine available. Install nudenet')}"
            )
        local = "✅ NudeNet (local, no key)" if self.nude else f"❌ off ({html.escape(self.reason or 'not installed')})"
        now = time.time()
        parts = []
        for name, st in self._engines.items():
            if now < st["off_until"]:
                parts.append(f"❌ {name}: {html.escape(st['error'] or 'failed')} (retry in {int(st['off_until'] - now)}s)")
            else:
                parts.append(f"✅ {name}")
        cloud = "\n    " + "\n    ".join(parts)
        mode = "Strict: every picture / video also checked by the cloud model" if CLOUD_ALL else "Smart: cloud only when the local detector is unsure"
        return (
            "✅ <b>Model Status: Ready</b>\n\n"
            f"🧠 <b>Local engine:</b> {local}\n"
            f"☁️ <b>Cloud engines:</b> {cloud}\n"
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

@pbot.on_message(filters.command("nsfwtest", prefixes=prefix_cmds) & filters.group)
async def nsfw_test_cmd(client, message: Message):
    """Reply to a picture / GIF / video / sticker: shows what every engine says about it and why."""
    if not message.from_user or not await is_user_admin(message.chat.id, message.from_user.id):
        return await message.reply_text(font("❌ You must be an admin to use this command."))
    target = message.reply_to_message
    if not target or not _has_media(target):
        return await message.reply_text(font("↩️ Reply to a photo, sticker, GIF or video with /nsfwtest"))

    wait = await message.reply_text(font("🔬 Testing..."))
    try:
        media = (target.photo or target.video or target.animation or target.sticker
                 or target.video_note or target.document)
        note = ""
        if _is_still_image(target):
            data = await client.download_media(target, in_memory=True)
        else:                                            # video / gif / animated sticker: Telegram's preview picture
            thumbs = getattr(media, "thumbs", None) or []
            if not thumbs:
                return await wait.edit_text(font("❌ This media has no preview picture to test."))
            data = await client.download_media(thumbs[-1].file_id, in_memory=True)
            note = "\n<i>(preview picture of the video was tested)</i>"
        report = await detector.diagnose(data.getvalue())
        await wait.edit_text(font("🔬 <b>NSFW test</b>\n\n" + report + note), parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        await wait.edit_text(font(f"❌ Test failed: {html.escape(type(e).__name__)}: {html.escape(str(e))[:150]}"),
                             parse_mode=enums.ParseMode.HTML)


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
