# Auto Broadcast - message + photo isi file me fixed hai.
# Neeche SETTINGS me AB_TEXT / AB_MEDIA badlo, bas. Bot start hone ke baad apne aap chalta hai.
#
# Sudo commands:
#   /abnow     - abhi turant broadcast
#   /abstatus  - settings + agla broadcast kab

import asyncio
import random
import time

from pyrogram import errors, filters, types
from pyrogram.enums import ParseMode

from AloneX.music import app, config, db, logger

# ---------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------
AB_ENABLED = True            # False = auto broadcast band
AB_INTERVAL_MIN = 1440       # 1440 min = 24 ghante -> din me 1 broadcast
AB_TARGET = "both"           # "chats" | "users" | "both"
AB_SEND_ON_RESTART = False   # False = restart ke baad broadcast nahi jayega
AB_MIN_GAP_MIN = AB_INTERVAL_MIN  # itne minute ke andar dobara auto-broadcast nahi

# Photo / video links. Har message pe inme se random ek jayega.
# .mp4 / .mkv / .mov / .webm = video, baaki sab = photo. Sirf text chahiye to [] kar do.
AB_MEDIA = [
    "https://n.uguu.se/bboOEbGd.mp4",
    "https://d.uguu.se/SbCiuvXX.jpg",
]

# Message (HTML: <b>, <blockquote>, <blockquote expandable>)
AB_TEXT = (
    "<blockquote><b>🎧 ʜᴇʏ ᴛʜᴇʀᴇ 👋</b></blockquote>\n"
    "<blockquote expandable><b>"
    f"✨ ᴅɪᴅ ʏᴏᴜ ᴋɴᴏᴡ? {app.name}...\n"
    "ᴅᴇʟɪᴠᴇʀs ᴄʀʏsᴛᴀʟ-ᴄʟᴇᴀʀ, ʜɪ-ʀᴇs ᴍᴜsɪᴄ sᴛʀᴇᴀᴍɪɴɢ ᴡɪᴛʜ ᴢᴇʀᴏ ᴅᴇʟᴀʏ, "
    "ʀɪɢʜᴛ ɪɴsɪᴅᴇ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴍ ɢʀᴏᴜᴘs & ᴄʜᴀɴɴᴇʟs 🎵\n\n"
    "ғʀᴏᴍ 24/7 ɴᴏɴ-sᴛᴏᴘ sᴛʀᴇᴀᴍɪɴɢ ᴛᴏ ᴀ ʙᴜᴛᴛᴇʀ-sᴍᴏᴏᴛʜ ǫᴜᴇᴜᴇ sʏsᴛᴇᴍ, "
    "ᴇᴠᴇʀʏᴛʜɪɴɢ ɪs ʙᴜɪʟᴛ ᴛᴏ ᴋᴇᴇᴘ ʏᴏᴜʀ ᴠɪʙᴇ ᴀʟɪᴠᴇ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ʟᴀɢ 🔥\n\n"
    "▸ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴀɴᴅ ʟᴇᴛ ᴛʜᴇ ᴍᴜsɪᴄ ɴᴇᴠᴇʀ sᴛᴏᴘ 🚀"
    "</b></blockquote>"
)
# ---------------------------------------------------------------

abdb = db.db.autobroadcast
_KEY = {"_id": "state"}
_lock = asyncio.Lock()


async def _last_sent() -> int:
    data = await abdb.find_one(_KEY) or {}
    return int(data.get("last_sent", 0))


async def _claim(force: bool = False) -> bool:
    """Atomic claim - do process ek saath chalein to bhi sirf ek broadcast jayega."""
    now = int(time.time())
    if force:
        await abdb.update_one(_KEY, {"$set": {"last_sent": now}}, upsert=True)
        return True
    gap = max(AB_MIN_GAP_MIN * 60, 1)
    try:
        res = await abdb.update_one(
            {"_id": "state", "$or": [{"last_sent": {"$lte": now - gap}}, {"last_sent": {"$exists": False}}]},
            {"$set": {"last_sent": now}},
            upsert=True,
        )
        return bool(res.modified_count or res.upserted_id)
    except Exception:
        return False  # DuplicateKeyError: kisi aur ne abhi claim kar liya


def _buttons() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        [
            [
                types.InlineKeyboardButton(
                    "➕ ᴀᴅᴅ ᴍᴇ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ",
                    url=f"https://t.me/{app.username}?startgroup=true",
                )
            ],
            [types.InlineKeyboardButton("💌 sᴛᴀʀᴛ ᴍᴇ ʙᴀʙʏ", url=f"https://t.me/{app.username}?start=true")],
        ]
    )


_VIDEO_EXT = (".mp4", ".mkv", ".mov", ".webm")


async def _send(chat_id: int) -> None:
    media = random.choice(AB_MEDIA) if AB_MEDIA else None
    if media:
        try:
            if media.lower().split("?")[0].endswith(_VIDEO_EXT):
                return await app.send_video(
                    chat_id, media, caption=AB_TEXT, parse_mode=ParseMode.HTML,
                    reply_markup=_buttons(), supports_streaming=True,
                )
            return await app.send_photo(
                chat_id, media, caption=AB_TEXT, parse_mode=ParseMode.HTML,
                reply_markup=_buttons(),
            )
        except errors.BadRequest as e:
            # link dead / media invalid / caption too long -> text bhej do, broadcast na ruke
            if not any(k in str(e) for k in ("WEBPAGE", "MEDIA")):
                raise
            logger.warning(f"Auto broadcast: media failed ({media}), sending text only.")
    await app.send_message(
        chat_id, AB_TEXT, parse_mode=ParseMode.HTML,
        disable_web_page_preview=True, reply_markup=_buttons(),
    )


async def _broadcast(force: bool = False) -> tuple:
    if _lock.locked():
        return 0, 0
    async with _lock:
        if not await _claim(force):
            return 0, 0

        targets = []
        if AB_TARGET in ("chats", "both"):
            targets += [c for c in await db.get_chats() if isinstance(c, int) and c not in db.blacklisted]
        if AB_TARGET in ("users", "both"):
            targets += [u for u in await db.get_users() if isinstance(u, int) and u not in app.bl_users]
        targets = list(dict.fromkeys(targets))  # ek chat/user ko ek hi baar

        sent = failed = 0
        for chat_id in targets:
            try:
                await _send(chat_id)
                sent += 1
            except errors.FloodWait as fw:
                if fw.value > 200:
                    failed += 1
                else:
                    await asyncio.sleep(fw.value)
                    try:
                        await _send(chat_id)
                        sent += 1
                    except Exception:
                        failed += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.3)

    try:
        await app.send_message(
            config.LOGGER_ID,
            f"<b>» ᴀᴜᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ ᴅᴏɴᴇ</b>\n\nsᴇɴᴛ : <code>{sent}</code>\nғᴀɪʟᴇᴅ : <code>{failed}</code>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass
    return sent, failed


@app.on_message(filters.command("abnow") & app.sudoers)
async def _ab_now(_, message: types.Message):
    if _lock.locked():
        return await message.reply_text("⏳ ʙʀᴏᴀᴅᴄᴀsᴛ ᴀʟʀᴇᴀᴅʏ ʀᴜɴɴɪɴɢ.")
    m = await message.reply_text("📢 ʙʀᴏᴀᴅᴄᴀsᴛ sᴛᴀʀᴛ...")
    sent, failed = await _broadcast(force=True)
    await m.edit_text(
        f"✅ ᴅᴏɴᴇ\n\nsᴇɴᴛ : <code>{sent}</code>\nғᴀɪʟᴇᴅ : <code>{failed}</code>",
        parse_mode=ParseMode.HTML,
    )


@app.on_message(filters.command("abstatus") & app.sudoers)
async def _ab_status(_, message: types.Message):
    last = await _last_sent()
    left = max(0, int(last + AB_INTERVAL_MIN * 60 - time.time())) if last else 0
    await message.reply_text(
        "<b>» ᴀᴜᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ</b>\n\n"
        f"sᴛᴀᴛᴜs : <code>{'ON' if AB_ENABLED else 'OFF'}</code>\n"
        f"ɪɴᴛᴇʀᴠᴀʟ : <code>{AB_INTERVAL_MIN}</code> ᴍɪɴ\n"
        f"ᴛᴀʀɢᴇᴛ : <code>{AB_TARGET}</code>\n"
        f"ᴍᴇᴅɪᴀ : <code>{len(AB_MEDIA)}</code>\n"
        f"ɴᴇxᴛ ɪɴ : <code>{left // 60}</code> ᴍɪɴ",
        parse_mode=ParseMode.HTML,
    )


async def _scheduler():
    await asyncio.sleep(30)
    if AB_ENABLED and AB_SEND_ON_RESTART:
        try:
            await _broadcast()
        except Exception as e:
            logger.error(f"Auto broadcast (restart) error: {e}")
    if await _last_sent() == 0:
        await _claim(force=True)  # pehli baar: restart pe nahi bhejna, 24h ki ghadi yahin se shuru
    while True:
        try:
            if (
                AB_ENABLED
                and not _lock.locked()
                and time.time() - await _last_sent() >= AB_INTERVAL_MIN * 60
            ):
                await _broadcast()
        except Exception as e:
            logger.error(f"Auto broadcast error: {e}")
        await asyncio.sleep(30)


asyncio.create_task(_scheduler())
