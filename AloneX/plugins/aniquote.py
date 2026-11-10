import aiohttp
import re
import os
import html
import config

from AloneX import pbot, font
from AloneX.helpers.scripts import anime_quote
from AloneX.helpers.decorator import spam_control
from pyrogram import filters
from pyrogram.enums import ParseMode  # ✅ Needed for parse_mode

__module__ = "𝐀ɴɪ-𝐐ᴜᴏᴛᴇ📝"

__help__ = """
*𝐀ɴɪ-𝐐ᴜᴏᴛᴇ📝*

*Description:*  
Search anime quotes by character or get random quotes, including optional audio playback.

*Commands:*  
❂ `/aniquote` — Get a random anime quote.  
❂ `/aniquote <query>` — Search quotes by keyword.  
❂ `/aniquote <query> page <n>` — Get a specific result page.

*Examples:*  
`/aniquote`  
`/aniquote naruto`  
`/aniquote luffy page 2`
"""


@pbot.on_message(filters.command('aniquote') & ~filters.forwarded, group=-376)
@spam_control
async def AniQuote(_, message):
    m = message
    search = m.text.split(maxsplit=1)[1] if len(m.text.split()) > 1 else None
    random = True if not search else False
    page = 1

    # Extract `page N` from query
    if search:
        page_match = re.search(r'page\s+(\d+)', search, re.IGNORECASE)
        if page_match:
            page = int(page_match.group(1))
            search = re.sub(r'page\s+\d+', '', search, flags=re.IGNORECASE).strip()

    # Fetch quotes
    quote_data = await anime_quote(search=search, random=random, page=page)

    if not quote_data:
        return await m.reply_text(font('❌ **No results found.**'))

    if isinstance(quote_data, dict) and "error" in quote_data:
        return await m.reply_text(f'❌ **ERROR**: `{quote_data["error"]}`')

    msg = await m.reply_text(font('🎧 **Uploading Quotes...**'))

    async with aiohttp.ClientSession() as session:
        for data in quote_data:
            # Safe file name
            safe_quote = re.sub(r'[^a-zA-Z0-9_-]', '_', data["quote"][:20])
            audio_path = f'temp_{safe_quote}.mp3'

            try:
                # Download audio
                async with session.get(data['audio_url']) as response:
                    with open(audio_path, 'wb+') as file:
                        file.write(await response.read())

                # Prepare caption
                caption = f"""
<blockquote><b>Quote:</b><br>{html.escape(data['quote'])}</blockquote>
<b>Character:</b> <code>{html.escape(data['character'])}</code>
<a href="{data['image_url']}">🔗 Character Image</a>
""".strip()

                await m.reply_audio(audio_path, caption=caption, parse_mode=ParseMode.HTML)

            except Exception as e:
                await m.reply_text(f"❌ Error processing quote:\n`{e}`")
            finally:
                if os.path.exists(audio_path):
                    os.remove(audio_path)

    await msg.edit_text(f'✅ **Uploaded by {config.BOT_USERNAME}**')
