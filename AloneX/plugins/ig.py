import asyncio
import aiohttp
import shortuuid
from pathlib import Path
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
from AloneX import pbot as app, font

Path("downloads").mkdir(exist_ok=True)

# Global aiohttp session for connection pooling
session = None

async def get_session():
    global session
    if session is None or session.closed:
        timeout = aiohttp.ClientTimeout(total=60, connect=10)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={"User-Agent": "Mozilla/5.0"}
        )
    return session

async def download_media(url: str, is_video: bool = False) -> str:
    ext = ".mp4" if is_video else ".jpg"
    path = f"downloads/{shortuuid.uuid()}{ext}"
    try:
        sess = await get_session()
        async with sess.get(url) as r:
            if r.status == 200:
                with open(path, "wb") as f:
                    async for chunk in r.content.iter_chunked(1024 * 1024):  # 1MB chunks
                        f.write(chunk)
                return path
    except Exception as e:
        print(f"Download error: {e}")
    return None

async def get_media_urls(url: str):
    api = f"https://beta.fallenapi.fun/instagram?api_key=646160_kjo7dJ6d2avOhHttkp87D4h_x2FERXAV&url={url}"
    try:
        sess = await get_session()
        async with sess.get(api) as r:
            data = await r.json()
        
        if isinstance(data, list):
            data = {"url": data}
        
        media_list = []
        url_field = data.get("url")
        
        if url_field:
            if isinstance(url_field, list):
                for item in url_field:
                    if isinstance(item, dict):
                        nested = item.get("url")
                        if isinstance(nested, list):
                            for final in nested:
                                if isinstance(final, dict):
                                    m_url = final.get("url")
                                    is_vid = final.get("type", "jpg").lower() in ['mp4', 'video', 'mov']
                                    if m_url:
                                        media_list.append({"url": m_url, "is_video": is_vid})
                                elif isinstance(final, str):
                                    media_list.append({"url": final, "is_video": '.mp4' in final.lower()})
                        elif isinstance(nested, str):
                            media_list.append({"url": nested, "is_video": '.mp4' in nested.lower()})
                    elif isinstance(item, str):
                        media_list.append({"url": item, "is_video": '.mp4' in item.lower()})
            elif isinstance(url_field, str):
                media_list.append({"url": url_field, "is_video": '.mp4' in url_field.lower()})
        
        if not media_list:
            fallback = data.get("hd") or data.get("sd") or data.get("video")
            if fallback:
                media_list.append({"url": fallback, "is_video": True})
        
        return media_list if media_list else None
    except Exception as e:
        print(f"API error: {e}")
        return None

@app.on_message(filters.regex(r'https?://(?:www\.)?instagram\.com'))
async def auto_download(c: Client, m: Message):
    url = None
    for word in m.text.split():
        if "instagram.com" in word:
            url = word
            break
    
    if not url:
        return
    
    msg = await m.reply(font("🔍 Fetching..."))
    
    # Get media URLs
    media_items = await get_media_urls(url)
    
    if not media_items:
        return await msg.edit("❌ Failed to fetch media")
    
    total = len(media_items)
    await msg.edit(f"⬇️ Downloading {total} file{'s' if total > 1 else ''}...")
    
    # Download all files concurrently
    download_tasks = [download_media(item["url"], item["is_video"]) for item in media_items]
    paths = await asyncio.gather(*download_tasks)
    
    # Filter successful downloads
    downloaded = [
        {"path": p, "is_video": media_items[i]["is_video"]} 
        for i, p in enumerate(paths) if p
    ]
    
    if not downloaded:
        return await msg.edit("❌ Download failed")
    
    await msg.edit(f"📤 Sending {len(downloaded)} file{'s' if len(downloaded) > 1 else ''}...")
    
    try:
        if len(downloaded) == 1:
            f = downloaded[0]
            if f["is_video"]:
                await m.reply_video(f["path"], caption="✅ Downloaded from Instagram")
            else:
                await m.reply_photo(f["path"], caption="✅ Downloaded from Instagram")
        else:
            # Send in batches of 10 (Telegram limit for media groups)
            for i in range(0, len(downloaded), 10):
                batch = downloaded[i:i+10]
                media = []
                for j, f in enumerate(batch):
                    caption = "✅ Downloaded from Instagram" if j == 0 else ""
                    if f["is_video"]:
                        media.append(InputMediaVideo(f["path"], caption=caption))
                    else:
                        media.append(InputMediaPhoto(f["path"], caption=caption))
                
                await m.reply_media_group(media)
                
                # Small delay between batches to avoid rate limits
                if i + 10 < len(downloaded):
                    await asyncio.sleep(0.5)
        
        await msg.delete()
    
    except Exception as e:
        await msg.edit(f"❌ Upload error: {str(e)}")
    
    finally:
        # Cleanup downloaded files
        for f in downloaded:
            try:
                Path(f["path"]).unlink(missing_ok=True)
            except:
                pass

# Cleanup session on bot shutdown
@app.on_disconnect()
async def cleanup_session(client, py_session):
    """
    Pyrogram's disconnect handler calls the registered callback with two positional
    arguments (client, session). The previous implementation defined a zero-arg
    function which caused the TypeError:
      cleanup_session() takes 0 positional arguments but 2 were given

    Accepting (client, py_session) avoids shadowing the module-level `session`
    variable (hence the parameter is named `py_session`) and ensures the global
    aiohttp session is closed cleanly.
    """
    global session
    try:
        if session and not session.closed:
            await session.close()
    except Exception as e:
        print(f"Session cleanup error: {e}")
    finally:
        session = None
