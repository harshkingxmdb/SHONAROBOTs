

import aiohttp
import asyncio
import config
from pyrogram import filters
from AloneX import pbot as app, font

__help__ = """
*Commands*:

```
- /ip <address>: information for ip address.
```

*Example*:
`/ip 162.243.19.47`
"""

__module__ = '𝐈ᴘ✨'


async def lookup(ip: str):
    url = f"http://ip-api.com/json/{ip}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status != 200:
                    return f"Error: HTTP {response.status}"
                
                ip_info = await response.json()
                
                if ip_info['status'] == 'fail':
                    return f"Error: {ip_info['message']}"
                
                info = (
                    f"\n**ℹ️ IP Information Lookup Result**:\n\n"
                    f"**IP Address**: {ip_info.get('query', 'N/A')}\n"
                    f"**Country**: {ip_info.get('country', 'N/A')} ({ip_info.get('countryCode', 'N/A')})\n"
                    f"**Region**: {ip_info.get('regionName', 'N/A')} ({ip_info.get('region', 'N/A')})\n"
                    f"**City**: {ip_info.get('city', 'N/A')}\n"
                    f"**ZIP Code**: {ip_info.get('zip', 'N/A')}\n"
                    f"**Latitude**: {ip_info.get('lat', 'N/A')}\n"
                    f"**Longitude**: {ip_info.get('lon', 'N/A')}\n"
                    f"**ISP**: {ip_info.get('isp', 'N/A')}\n"
                    f"**Organization**: {ip_info.get('org', 'N/A')}\n"
                    f"**AS**: {ip_info.get('as', 'N/A')}\n\n"
                    f"**By {config.BOT_USERNAME}**"
                )
                return info
    except aiohttp.ClientError as e:
        return f"An error occurred: {e}"
    except asyncio.TimeoutError:
        return "Error: The request timed out. The server might be busy. Please try again later."
    except Exception as e:
        return f"An unexpected error occurred: {e}"

@app.on_message(filters.command('ip') & ~filters.forwarded)
async def ip_lookup(_, message):
    m = message
    query = m.text.split(maxsplit=1)[1] if len(m.text.split()) > 1 else None
    if not query:
        return await m.reply_text(font('**IP address ??**'))
    
    result = await lookup(query)
    await m.reply_text(result)
