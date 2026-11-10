import asyncio
import re
import os
import time
from gtts import gTTS
from groq import AsyncGroq
from pyrogram import filters
from pyrogram.errors import VoiceMessagesForbidden
from pyrogram.enums import ParseMode, ChatAction, ButtonStyle
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from AloneX import pbot, GROQ_API_KEY, prefix_cmds
from AloneX.helpers.decorator import spam_control

__module__ = "𝐀ᴅᴠᴀɴᴄᴇ-𝐆ᴘᴛ⛔"
__help__ = """
*Advance-GPT*

*Description:*  
Generate text, images, or voice using GPT-based models.

*Commands:*  
❂ `/gpt <query>` – Generate text responses  
❂ `/igpt <query>` – Generate images from text  
❂ `/vgpt <query>` – Generate voice/audio from text

*Example:*  
`/gpt india capital`
`/vgpt tell me about India`
"""

groq_client = AsyncGroq(api_key=GROQ_API_KEY)
REGEN_DATA = {}
HINDI_PATTERN = re.compile(r'[\u0900-\u097F]|kya|hai|kaise|kahan|aap|mujhe|hum|kab|mera|tera|bolo|batao')

def is_hindi(text: str) -> bool:
    if not text:
        return False
    return bool(HINDI_PATTERN.search(text[:200].lower()))

def clean_text_for_tts(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\*\*?(.*?)\*\*?', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = ' '.join(text.split())
    if len(text) > 500:
        text = text[:497] + "..."
    return text.strip()

async def gpt_response(query: str, force_lang: str = None) -> str:
    try:
        if not query or not query.strip():
            return None
        if force_lang:
            lang = "Hindi" if force_lang == "hi" else "English"
        else:
            lang = "Hindi" if is_hindi(query) else "English"
        system = (
            f"You are Shonax, a helpful AI assistant. "
            f"Respond ONLY in {lang}. Be conversational, friendly and concise. "
            f"Keep responses under 250 words. Avoid special characters and formatting."
        )
        response = await asyncio.wait_for(
            groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=600,
                top_p=1,
                stream=False
            ),
            timeout=60
        )
        if response and response.choices:
            content = response.choices[0].message.content
            if content:
                return content.strip()
        return None
    except asyncio.TimeoutError:
        return None
    except Exception as e:
        print(f"[GPT Error] {e}")
        raise RuntimeError(f"GPT Error: {e}")

async def generate_voice(prompt: str, force_lang: str = None):
    mp3_path = ogg_path = None
    try:
        full_reply = await gpt_response(prompt, force_lang)
        if not full_reply:
            raise RuntimeError("No response from GPT")
        reply = clean_text_for_tts(full_reply)
        if not reply or len(reply) < 3:
            raise RuntimeError("Generated text too short or empty")
        is_hindi_lang = is_hindi(reply)
        lang_code = "hi" if is_hindi_lang else "en"
        tld = "co.in" if is_hindi_lang else "com"
        print(f"[gTTS] Language: {'Hindi' if is_hindi_lang else 'English'}, Text: {reply[:100]}...")
        timestamp = int(time.time() * 1000)
        mp3_path = f"/tmp/tts_{timestamp}.mp3"
        ogg_path = f"/tmp/tts_{timestamp}.ogg"
        loop = asyncio.get_event_loop()
        tts = gTTS(text=reply, lang=lang_code, tld=tld, slow=False)
        await loop.run_in_executor(None, tts.save, mp3_path)
        if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) == 0:
            raise RuntimeError("gTTS failed to create audio")
        print(f"[gTTS] ✓ MP3 created: {os.path.getsize(mp3_path)} bytes")
        cmd = ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "libopus", "-b:a", "64k", ogg_path]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
        if process.returncode != 0:
            error = stderr.decode('utf-8', errors='ignore')[-300:]
            print(f"[FFmpeg] Error: {error}")
            print("[FFmpeg] Fallback: Using MP3 instead")
            return reply, mp3_path, mp3_path, is_hindi_lang
        if not os.path.exists(ogg_path) or os.path.getsize(ogg_path) == 0:
            print("[FFmpeg] OGG empty, using MP3")
            return reply, mp3_path, mp3_path, is_hindi_lang
        print(f"[FFmpeg] ✓ OGG created: {os.path.getsize(ogg_path)} bytes")
        return reply, ogg_path, mp3_path, is_hindi_lang
    except asyncio.TimeoutError:
        print("[Error] Timeout during conversion")
        raise RuntimeError("Voice generation timed out")
    except Exception as e:
        print(f"[Error] {type(e).__name__}: {e}")
        for f in [mp3_path, ogg_path]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
        raise RuntimeError(f"Voice generation failed: {str(e)}")

@pbot.on_message(filters.command('vgpt', prefixes=prefix_cmds) & ~filters.forwarded, group=-99999)
@spam_control
async def vgpt_voice(_, message: Message):
    if not message.from_user or message.from_user.is_bot:
        return
    mp3_path = ogg_path = None
    try:
        text = message.text
        query = text.split(maxsplit=1)[1] if len(text.split(maxsplit=1)) > 1 else None
        if not query and message.reply_to_message_id:
            replied = await pbot.get_messages(message.chat.id, message.reply_to_message_id)
            query = (replied.text or replied.caption or "").strip()
        if not query or len(query) < 2:
            await message.reply_text("❌ **Usage:** `/vgpt your question`\n\n**Example:** `/vgpt tell me about India`")
            return
        msg = await message.reply_text("🎧 **Generating voice...**")
        await pbot.send_chat_action(message.chat.id, ChatAction.RECORD_AUDIO)
        reply, voice_path, mp3_path, is_hindi_lang = await generate_voice(query)
        REGEN_DATA[message.id] = (query, message.chat.id, is_hindi_lang)
        caption = f"🎧 **AloneX Voice** (`{'Hindi' if is_hindi_lang else 'English'}`)\n\n🗨️ {reply[:300]}"
        is_ogg = voice_path.endswith('.ogg')
        try:
            if is_ogg:
                await pbot.send_voice(chat_id=message.chat.id, voice=voice_path, caption=caption, parse_mode=ParseMode.MARKDOWN, reply_to_message_id=message.id, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Translate", callback_data=f"regen_{message.id}", style=ButtonStyle.PRIMARY)]]))
            else:
                await pbot.send_audio(chat_id=message.chat.id, audio=voice_path, caption=caption, title="AloneX Voice", performer="AloneX AI", parse_mode=ParseMode.MARKDOWN, reply_to_message_id=message.id, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Translate", callback_data=f"regen_{message.id}", style=ButtonStyle.PRIMARY)]]))
        except VoiceMessagesForbidden:
            await pbot.send_audio(chat_id=message.chat.id, audio=voice_path, caption=caption, title="AloneX Voice", performer="AloneX AI", parse_mode=ParseMode.MARKDOWN, reply_to_message_id=message.id, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Translate", callback_data=f"regen_{message.id}", style=ButtonStyle.PRIMARY)]]))
        await msg.delete()
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{str(e)[:200]}`", parse_mode=ParseMode.MARKDOWN)
        print(f"[VGPT] Error: {e}")
    finally:
        for f in [mp3_path, ogg_path]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                    print(f"[Cleanup] Deleted: {f}")
                except Exception as e:
                    print(f"[Cleanup] Failed: {e}")

@pbot.on_callback_query(filters.regex(r"regen_(\d+)"))
async def regen_voice(_, query: CallbackQuery):
    msg_id = int(query.data.split("_")[1])
    if msg_id not in REGEN_DATA:
        return await query.answer("⚠️ Session expired", show_alert=True)
    prompt, chat_id, was_hindi = REGEN_DATA[msg_id]
    force_lang = "en" if was_hindi else "hi"
    await query.answer("🔁 Translating...")
    mp3_path = ogg_path = None
    try:
        await pbot.send_chat_action(chat_id, ChatAction.RECORD_AUDIO)
        reply, voice_path, mp3_path, is_hindi_lang = await generate_voice(prompt, force_lang=force_lang)
        caption = f"🔁 **Translated** (`{'Hindi' if is_hindi_lang else 'English'}`)\n\n🗨️ {reply[:300]}"
        is_ogg = voice_path.endswith('.ogg')
        try:
            if is_ogg:
                await pbot.send_voice(chat_id=chat_id, voice=voice_path, caption=caption, parse_mode=ParseMode.MARKDOWN)
            else:
                await pbot.send_audio(chat_id=chat_id, audio=voice_path, caption=caption, title="AloneX Voice", parse_mode=ParseMode.MARKDOWN)
        except VoiceMessagesForbidden:
            await pbot.send_audio(chat_id=chat_id, audio=voice_path, caption=caption, title="AloneX Voice", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await query.message.reply_text(f"❌ **Translation failed:** `{str(e)[:150]}`", parse_mode=ParseMode.MARKDOWN)
        print(f"[Regen] Error: {e}")
    finally:
        for f in [mp3_path, ogg_path]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
