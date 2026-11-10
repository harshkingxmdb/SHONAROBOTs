import asyncio
import re
from groq import AsyncGroq
from telethon import events
from telethon.tl.types import Channel
from AloneX import tbot, font
import config

groq_client = None
if config.GROQ_API_KEY:
    groq_client = AsyncGroq(api_key=config.GROQ_API_KEY)

_gpt_handler_registered = False

HINDI_PATTERN = re.compile(r'[\u0900-\u097F]|kya|hai|kaise|kahan|aap|mujhe|hum|kab')

def is_hindi(text: str) -> bool:
    return bool(HINDI_PATTERN.search(text[:200].lower()))

async def gpt(query: str) -> str:
    if not groq_client:
        return "❌ Groq API Key not configured."

    try:
        lang = "Hindi" if is_hindi(query) else "English"
        system = f"You are AloneX, a helpful AI assistant. Respond only in {lang}. Be conversational, friendly and concise."
        
        response = await asyncio.wait_for(
            groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=8000,
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
    except Exception:
        return None

async def handle_gpt(event):
    if isinstance(event.chat, Channel) and not event.is_group:
        return
    if event.fwd_from:
        return
    
    try:
        query = event.text.replace("#gpt", "", 1).strip()
        
        if not query and event.reply_to_msg_id:
            replied = await event.get_reply_message()
            query = (replied.text or replied.message or "").strip()
        
        if not query or len(query) < 2:
            await event.reply(
                "Hi, I am ShonaX, your AI assistant!\n\nUsage: #gpt your question\nOr reply to a message with #gpt"
            )
            return
        
        try:
            async with tbot.action(event.chat_id, 'typing'):
                result = await gpt(query)
        except:
            result = await gpt(query)
        
        if result:
            if len(result) > 4000:
                parts = [result[i:i+3900] for i in range(0, len(result), 3900)]
                for i, part in enumerate(parts[:3]):
                    msg_text = f"{part}\n\n{'[...]' if i < len(parts)-1 else ''}"
                    if i == 0:
                        await event.reply(msg_text)
                    else:
                        await event.respond(msg_text)
                    await asyncio.sleep(0.5)
            else:
                await event.reply(result)
        else:
            await event.reply(font("No response received. Please try again."))
            
    except Exception:
        try:
            await event.reply(font("An error occurred. Please try again later."))
        except:
            pass

if "gpt" not in tbot.handlers_loaded:
    tbot.add_event_handler(handle_gpt, events.NewMessage(pattern=r"^#gpt", incoming=True))
    tbot.handlers_loaded.add("gpt")
