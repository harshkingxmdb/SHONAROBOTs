import io
import asyncio
import threading
import html
from contextlib import suppress
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
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self.model = None
        self.processor = None
        self.loaded = False
        self.loading = False
        self._initialized = True
        self._ready = threading.Event()
        threading.Thread(target=self._load_model, daemon=True).start()
    
    def _load_model(self):
        self.loading = True
        try:
            import torch
            from transformers import pipeline
            self.model = pipeline(
                "image-classification", 
                model="Falconsai/nsfw_image_detection", 
                device=0 if torch.cuda.is_available() else -1
            )
            self.loaded = True
            self.loading = False
            self._ready.set()
        except Exception:
            self.loading = False
            self.loaded = False
            self._ready.set()
    
    async def wait_ready(self, timeout=45):
        if self.loaded:
            return True
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._ready.wait, timeout)
    
    async def is_nsfw(self, image_bytes: bytes) -> bool:
        try:
            if not self.loaded:
                await self.wait_ready()
            if not self.loaded or not self.model:
                return False
            
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            
            if img.size[0] > 512 or img.size[1] > 512:
                img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, self.model, img)
            
            for result in results:
                if result['label'].lower() == 'nsfw' and result['score'] > 0.65:
                    return True
            return False
        except Exception:
            return False
    
    async def check_video_frame(self, video_path: str) -> bool:
        try:
            import cv2
            import os
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return False

            ret, frame = cap.read()
            cap.release()
            
            if not ret or frame is None:
                return False

            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            frame_bytes = buffer.tobytes()
            return await self.is_nsfw(frame_bytes)
        except Exception:
            return False

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
    
    if detector.loaded:
        status_text = (
            "✅ <b>Model Status: Ready</b>\n\n"
            "🤖 <b>Engine:</b> FalconsAI NSFW Detection\n"
            "⚡ <b>Performance:</b> Optimized & Fast\n"
            "🎯 <b>Accuracy:</b> High Confidence Mode\n"
            "📊 <b>Threshold:</b> 65%"
        )
    elif detector.loading:
        status_text = (
            "🔄 <b>Model Loading...</b>\n\n"
            "⏳ Please wait, model will be ready soon"
        )
    else:
        status_text = (
            "❌ <b>Model Failed</b>\n\n"
            "🐛 NSFW detection is currently <b>disabled</b>"
        )
    
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
            is_nsfw = await detector.is_nsfw(file_bytes.getvalue())
        else:
            path = await client.download_media(message)
            if not path: return
            is_nsfw = await detector.check_video_frame(path)
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
