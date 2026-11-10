import config
import asyncio
from AloneX import pbot, font
from AloneX.helpers.scripts import IMDBScraper
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ButtonStyle
from AloneX.helpers.decorator import disableable

imdb = IMDBScraper()

__help__ = '''
*Commands*:
✪ /imdb
'''

__module__ = '𝐈ᴍᴅʙ👤'


async def search_imdb(name: str):
    result = await imdb.search_by_name(name)
    results = result.get('results')
    if results:
        return [
            {
                'url': f"https://m.imdb.com/title/{m['id']}",
                'title': m.get('titlePosterImageModel', {}).get('caption', 'Not available'),
                'id': m['id'],
                'media': m.get('titlePosterImageModel', {}).get('url', None),
                'year': m.get('titleReleaseText', 'Unknown') if isinstance(m.get('titleReleaseText'), str) else m.get('titleReleaseText', {}).get('text', 'Unknown'),
                'rating': m.get('ratingsSummary', {}).get('aggregateRating', 'N/A'),
                'votes': m.get('ratingsSummary', {}).get('voteCount', 'N/A'),
            }
            for m in results if m.get('id')
        ]
    return []


@pbot.on_message(filters.command('imdb') & ~filters.forwarded, group=-327)
@disableable("imdb")
async def imdb_search(_, message):
    query = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    if not query:
        return await message.reply_text(font('**Movie name ??**'))

    data = await search_imdb(query)
    if not data:
        return await message.reply_text(font('❌ **Movie not found.**'))

    # Limit to top 5 results
    for d in data[:5]:
        caption = (
            f"🎬 **Title:** `{d['title']}`\n"
            f"📅 **Year:** `{d['year']}`\n"
            f"⭐ **Rating:** `{d['rating']} / 10` ({d['votes']} votes)\n"
            f"🆔 **IMDb ID:** `{d['id']}`"
        )

        buttons = [[InlineKeyboardButton(font("🔗 IMDb Link"), url=d['url'], style=ButtonStyle.SUCCESS)]]

        if d['media']:
            await message.reply_photo(
                photo=d['media'],
                caption=caption,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await message.reply_text(
                text=caption,
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        await asyncio.sleep(1.2)
