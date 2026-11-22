# /weather for AloneX (Pyrogram)
# Open-Meteo: free, no API key. City name -> coordinates -> current weather.

import asyncio
import html

import aiohttp
import AloneX
from pyrogram import filters, enums

from AloneX import pbot as app, prefix_cmds, init_aiohttp_session

__module__ = "𝐖ᴇᴀᴛʜᴇʀ🌦️"

__help__ = """
**Weather 🌦️**

❂ `/weather [city]` – Current weather of a city.

Example: `/weather delhi`
"""

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WX_URL = "https://api.open-meteo.com/v1/forecast"

WX_CODES = {
    0: ("Clear sky", "☀️"), 1: ("Mainly clear", "🌤️"), 2: ("Partly cloudy", "⛅"), 3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"), 48: ("Rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"), 53: ("Drizzle", "🌦️"), 55: ("Dense drizzle", "🌧️"),
    56: ("Freezing drizzle", "🌧️"), 57: ("Dense freezing drizzle", "🌧️"),
    61: ("Light rain", "🌦️"), 63: ("Rain", "🌧️"), 65: ("Heavy rain", "🌧️"),
    66: ("Freezing rain", "🌧️"), 67: ("Heavy freezing rain", "🌧️"),
    71: ("Light snow", "🌨️"), 73: ("Snow", "🌨️"), 75: ("Heavy snow", "❄️"), 77: ("Snow grains", "❄️"),
    80: ("Light showers", "🌦️"), 81: ("Showers", "🌧️"), 82: ("Violent showers", "⛈️"),
    85: ("Snow showers", "🌨️"), 86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈️"), 96: ("Thunderstorm with hail", "⛈️"), 99: ("Thunderstorm with heavy hail", "⛈️"),
}


async def _get(url: str, params: dict):
    if AloneX.aiohttpsession is None or AloneX.aiohttpsession.closed:
        await init_aiohttp_session()
    async with AloneX.aiohttpsession.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        return await r.json(content_type=None)


@app.on_message(filters.command(["weather"], prefixes=prefix_cmds))
async def weather_command(client, message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        return await message.reply_text(
            "<b>ᴜsᴀɢᴇ:</b> <code>/weather city</code>\nExample: <code>/weather delhi</code>",
            parse_mode=enums.ParseMode.HTML,
        )
    query = parts[1].strip()[:80]

    try:
        geo = await _get(GEO_URL, {"name": query, "count": 1, "language": "en", "format": "json"})
        places = geo.get("results") or []
        if not places:
            return await message.reply_text(
                "❌ <b>Location not found.</b> Please try a different city.", parse_mode=enums.ParseMode.HTML)
        place = places[0]

        wx = await _get(WX_URL, {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "timezone": "auto",
        })
        cur = wx.get("current") or {}
        if not cur:
            return await message.reply_text(
                "⚠️ <b>Weather data not available</b> at the moment.", parse_mode=enums.ParseMode.HTML)

        label, emoji = WX_CODES.get(cur.get("weather_code"), ("N/A", "🌍"))
        name = ", ".join(x for x in (place.get("name"), place.get("admin1"), place.get("country")) if x)
        text = (
            f"<b>{html.escape(name)}</b> 🌍\n\n"
            f"🌡️ <b>ᴛᴇᴍᴘᴇʀᴀᴛᴜʀᴇ:</b> <code>{cur.get('temperature_2m', 'N/A')} °C</code>\n"
            f"🥵 <b>ғᴇᴇʟs ʟɪᴋᴇ:</b> <code>{cur.get('apparent_temperature', 'N/A')} °C</code>\n"
            f"💧 <b>ʜᴜᴍɪᴅɪᴛʏ:</b> <code>{cur.get('relative_humidity_2m', 'N/A')}%</code>\n"
            f"💨 <b>ᴡɪɴᴅ:</b> <code>{cur.get('wind_speed_10m', 'N/A')} km/h</code>\n"
            f"{emoji} <b>ᴄᴏɴᴅɪᴛɪᴏɴ:</b> <i>{label}</i>"
        )
        await message.reply_text(text, parse_mode=enums.ParseMode.HTML)

    except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError, ValueError, KeyError) as e:
        print(f"Error in /weather: {type(e).__name__}: {e}")
        await message.reply_text(
            "❌ <b>An error occurred</b> while fetching the weather. Please try again later.",
            parse_mode=enums.ParseMode.HTML,
        )
