import os
import uuid
import random
import string
import asyncio
from gtts import gTTS
from AloneX.helpers.pyro_utils import no_channel
from AloneX.helpers.decorator import disableable
from AloneX import pbot as app, BOT_USERNAME, prefix_cmds, font
from pyrogram import Client, filters
from pyrogram.errors import VoiceMessagesForbidden
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from pyrogram.enums import ParseMode, ButtonStyle

__module__ = "𝐍ᴇᴡ-𝐓ᴏᴏʟs🎛️"

__help__ = """
*New-Tools*

*Description:*    
Useful voice and media commands to convert text to voice or process videos.  

*Commands:*    
❂ `/tts <text>` – Convert text to voice (choose language)    
❂ `/v2a` – Extract audio from a replied video    
❂ `/v2n` – Convert a video to a round video note  

*Example:*    
`/tts Hello, how are you?` (reply or send text)  
"""

# ---------------------- TEXT TO SPEECH ----------------------

VOICE_MAP = {
    "en": {"name": "English", "code": "en", "flag": "🇬🇧"},
    "hi": {"name": "Hindi", "code": "hi", "flag": "🇮🇳"},
    "fr": {"name": "French", "code": "fr", "flag": "🇫🇷"},
    "es": {"name": "Spanish", "code": "es", "flag": "🇪🇸"},
    "de": {"name": "German", "code": "de", "flag": "🇩🇪"},
    "ja": {"name": "Japanese", "code": "ja", "flag": "🇯🇵"},
    "ko": {"name": "Korean", "code": "ko", "flag": "🇰🇷"},
    "pt": {"name": "Portuguese", "code": "pt", "flag": "🇵🇹"},
    "ru": {"name": "Russian", "code": "ru", "flag": "🇷🇺"},
    "ar": {"name": "Arabic", "code": "ar", "flag": "🇸🇦"},
}

tts_cache = {}


async def generate_tts(text: str, lang: str, slow: bool = False) -> str:
    """Generate TTS audio file using gTTS"""
    path = f"/tmp/tts_{uuid.uuid4()}.mp3"
    
    # Run gTTS in executor to avoid blocking
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: gTTS(text=text, lang=lang, slow=slow).save(path)
    )
    
    return path


@app.on_message(filters.command("tts", prefix_cmds) & filters.text, group=93)
@disableable("tts")
@no_channel
async def tts_command(client: Client, message: Message):
    if not message.from_user:
        return await message.reply(font("❌ Anonymous admins not supported."))

    # Check if command is used as reply
    if message.reply_to_message and message.reply_to_message.text:
        text = message.reply_to_message.text
    elif len(message.command) >= 2:
        text = " ".join(message.command[1:])
    else:
        return await message.reply(
            "📝 Usage: Reply to a text with `/tts` or use `/tts your message here`",
            parse_mode=ParseMode.MARKDOWN,
        )

    user_id = message.from_user.id
    chat_id = message.chat.id

    tts_cache[user_id] = {"text": text, "msgs": [message.id], "chat": chat_id}

    lang_buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(font("🇬🇧 English"), callback_data="tts_lang_en", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(font("🇮🇳 Hindi"), callback_data="tts_lang_hi", style=ButtonStyle.PRIMARY),
            ],
            [
                InlineKeyboardButton(font("🇫🇷 French"), callback_data="tts_lang_fr", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(font("🇪🇸 Spanish"), callback_data="tts_lang_es", style=ButtonStyle.PRIMARY),
            ],
            [
                InlineKeyboardButton(font("🇩🇪 German"), callback_data="tts_lang_de", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(font("🇯🇵 Japanese"), callback_data="tts_lang_ja", style=ButtonStyle.PRIMARY),
            ],
            [
                InlineKeyboardButton(font("🇰🇷 Korean"), callback_data="tts_lang_ko", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(font("🇵🇹 Portuguese"), callback_data="tts_lang_pt", style=ButtonStyle.PRIMARY),
            ],
            [
                InlineKeyboardButton(font("🇷🇺 Russian"), callback_data="tts_lang_ru", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(font("🇸🇦 Arabic"), callback_data="tts_lang_ar", style=ButtonStyle.PRIMARY),
            ],
        ]
    )

    lang_msg = await message.reply(
        "🌍 **Choose language:**",
        reply_markup=lang_buttons,
        parse_mode=ParseMode.MARKDOWN,
    )
    tts_cache[user_id]["msgs"].append(lang_msg.id)


@app.on_callback_query(filters.regex("tts_lang_"))
async def tts_choose_speed(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in tts_cache:
        return await query.answer(font("❗ Use /tts command first."))

    lang = query.data.split("_")[-1]
    tts_cache[user_id]["lang"] = lang
    await query.answer()

    try:
        lang_name = VOICE_MAP.get(lang, {}).get("name", "English")
        await query.message.edit(f"✅ Language selected: {lang_name}")
    except:
        pass

    speed_buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(font("⚡ Normal Speed"), callback_data="tts_speed_normal", style=ButtonStyle.SUCCESS),
                InlineKeyboardButton(font("🐢 Slow Speed"), callback_data="tts_speed_slow", style=ButtonStyle.PRIMARY),
            ]
        ]
    )
    speed_msg = await query.message.reply(
        "⚙️ **Select speech speed:**",
        reply_markup=speed_buttons,
        parse_mode=ParseMode.MARKDOWN,
    )
    tts_cache[user_id]["msgs"].append(speed_msg.id)


@app.on_callback_query(filters.regex("tts_speed_"))
async def tts_generate_voice(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in tts_cache:
        return await query.answer(font("❗ Use /tts command first."))

    speed = query.data.split("_")[-1]
    slow = speed == "slow"
    
    await query.answer(font("🎙 Generating voice..."))

    lang = tts_cache[user_id]["lang"]
    text = tts_cache[user_id]["text"]
    lang_code = VOICE_MAP.get(lang, VOICE_MAP["en"])["code"]

    mp3_path = None
    try:
        mp3_path = await generate_tts(text, lang_code, slow)

        # Delete all previous messages
        for mid in tts_cache[user_id]["msgs"]:
            try:
                await client.delete_messages(tts_cache[user_id]["chat"], mid)
            except:
                pass
        try:
            await query.message.delete()
        except:
            pass

        lang_name = VOICE_MAP.get(lang, {}).get("name", "English")
        speed_text = "Slow" if slow else "Normal"
        
        try:
            await client.send_voice(
                chat_id=tts_cache[user_id]["chat"],
                voice=mp3_path,
                caption=f"🎧 **Generated by AloneX**\n🗣 Language: `{lang_name}` | Speed: `{speed_text}`",
                parse_mode=ParseMode.MARKDOWN,
            )
        except VoiceMessagesForbidden:
            await client.send_audio(
                chat_id=tts_cache[user_id]["chat"],
                audio=mp3_path,
                caption=f"🎧 **Generated by AloneX**\n🗣 Language: `{lang_name}` | Speed: `{speed_text}`",
                parse_mode=ParseMode.MARKDOWN,
            )
    except Exception as e:
        await query.message.reply(f"❌ TTS Failed:\n`{e}`", parse_mode=ParseMode.MARKDOWN)
    finally:
        tts_cache.pop(user_id, None)
        if mp3_path and os.path.exists(mp3_path):
            os.remove(mp3_path)


# ---------------------- VIDEO TO AUDIO ----------------------

def random_filename(suffix=""):
    return "".join(random.choices(string.ascii_letters + string.digits, k=8)) + suffix


@app.on_message(filters.command("v2a", prefix_cmds) & filters.reply, group=94)
@disableable("v2a")
async def video_to_audio(client: Client, message: Message):
    reply = message.reply_to_message
    if not reply or not reply.video:
        return await message.reply(font("❌ Reply to a video to extract audio."))

    status = await message.reply(font("📥 Downloading video..."))
    input_path = output_path = None

    try:
        input_path = await reply.download()
        output_path = f"/tmp/{random_filename('.mp3')}"

        await status.edit("🎧 Extracting audio...")
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i",
            input_path,
            "-vn",
            "-acodec",
            "libmp3lame",
            "-y",
            output_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.wait()

        await client.send_audio(
            chat_id=message.chat.id,
            audio=output_path,
            caption=f"🎧 Converted by {BOT_USERNAME}",
            reply_to_message_id=reply.id,
        )

        await status.delete()
        await message.delete()

    except Exception as e:
        await status.edit(f"❌ Error: `{e}`")
    finally:
        for path in [input_path, output_path]:
            if path and os.path.exists(path):
                os.remove(path)


# ---------------------- VIDEO TO ROUND NOTE ----------------------

@app.on_message(filters.command("v2n", prefix_cmds) & filters.reply, group=96)
@disableable("v2n")
async def video_to_note(client: Client, message: Message):
    reply = message.reply_to_message
    if not reply or not reply.video:
        return await message.reply(font("❌ Reply to a video to convert to round video."))

    status = await message.reply(font("📥 Downloading video..."))
    input_path = output_path = None

    try:
        input_path = await reply.download()
        output_path = f"/tmp/{random_filename('.mp4')}"

        await status.edit("🔄 Converting to round format...")

        scale_filter = (
            "scale='if(gt(a,1),480,-1)':'if(gt(a,1),-1,480)',"
            "pad=480:480:(ow-iw)/2:(oh-ih)/2"
        )

        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i",
            input_path,
            "-vf",
            scale_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-y",
            output_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.wait()

        await client.send_video_note(
            chat_id=message.chat.id,
            video_note=output_path,
            duration=10,
            length=480,
            reply_to_message_id=reply.id,
        )

        await status.delete()
        await message.delete()

    except Exception as e:
        await status.edit(f"❌ Error: `{e}`")
    finally:
        for path in [input_path, output_path]:
            if path and os.path.exists(path):
                os.remove(path)
