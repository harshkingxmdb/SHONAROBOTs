import os
import io
import aiohttp
import aiofiles
import asyncio
import shortuuid
import logging
import httpx
from pathlib import Path
from typing import Optional, Dict, Tuple, List
from datetime import datetime, timezone, timedelta
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineQuery, InlineQueryResultArticle, InlineQueryResultPhoto,
    InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, InputMediaVideo, InputMediaPhoto, InputMediaAudio
)
from pyrogram.enums import ButtonStyle
from pyrogram.errors import FloodWait
from AloneX import pbot as app, font
from AloneX.db.whisper import save_whisper, get_whisper, mark_read
from AloneX.helpers.scripts import GPTGeneration

Path("temp").mkdir(exist_ok=True)
Path("downloads").mkdir(exist_ok=True)

pending: Dict[str, Dict] = {}
logging.getLogger("pyrogram").setLevel(logging.WARNING)
_bot_info = None

async def get_bot_username():
    global _bot_info
    if _bot_info:
        return _bot_info
    try:
        me = await app.get_me()
        _bot_info = me.username or "bot"
        return _bot_info
    except Exception:
        return "bot"

class BitflowAPI:
    def __init__(self):
        self.api_url = "https://bitflow.in/api/youtube"
        self.api_key = "alonekey321"
    
    async def search(self, query: str, limit: int = 10):
        try:
            params = {"query": query, "format": "audio", "api_key": self.api_key}
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(self.api_url, params=params)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                if "error" in data:
                    return None
                results = []
                for i in range(min(limit, 10)):
                    results.append({
                        'title': data.get('title', 'Unknown'),
                        'url': data.get('url', ''),
                        'duration': data.get('duration', 'Unknown'),
                        'thumbnail': data.get('thumbnail', ''),
                        'artist': data.get('uploader', 'Unknown'),
                    })
                return results
        except Exception as e:
            logging.error(f"Bitflow search error: {e}")
            return None
    
    async def download_audio(self, query: str) -> Optional[Tuple[str, Dict]]:
        try:
            params = {"api_key": self.api_key, "format": "audio"}
            if query.startswith("http"):
                params["url"] = query
            else:
                params["query"] = query
            
            async with httpx.AsyncClient(timeout=150) as client:
                resp = await client.get(self.api_url, params=params)
                if resp.status_code != 200:
                    logging.error(f"Bitflow download failed: {resp.status_code}")
                    return None, None
                data = resp.json()
                if "error" in data:
                    logging.error(f"Bitflow error: {data.get('error')}")
                    return None, None
                
                download_url = data.get('url')
                if not download_url:
                    logging.error("No download URL in response")
                    return None, None
                
                file_path = f"downloads/{shortuuid.uuid()}.mp3"
                async with httpx.AsyncClient(timeout=150) as dl_client:
                    file_resp = await dl_client.get(download_url)
                    if file_resp.status_code != 200:
                        logging.error(f"File download failed: {file_resp.status_code}")
                        return None, None
                    
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(file_resp.content)
                
                metadata = {
                    'title': data.get('title', 'Unknown'),
                    'artist': data.get('uploader', 'Unknown'),
                    'duration': data.get('duration', 180),
                    'thumbnail': data.get('thumbnail', ''),
                }
                return file_path, metadata
        except Exception as e:
            logging.error(f"Bitflow download exception: {e}")
            return None, None

class MultiPlatformAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://tgmusic.fallenapi.fun"
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    def _normalize_url(self, url: str) -> str:
        url = str(url).strip()
        if not url.startswith("http"):
            url = "https://" + url
        return url.rstrip("/")

    def detect_platform(self, url: str) -> Optional[str]:
        url_lower = url.lower()
        platforms = {
            "instagram": ["instagram.com", "instagr.am"],
            "tiktok": ["tiktok.com", "vt.tiktok.com"],
            "pinterest": ["pinterest.com", "pin.it"],
            "bilibili": ["bilibili.com"],
            "twitter": ["twitter.com", "x.com"],
            "youtube": ["youtube.com", "youtu.be"],
            "spotify": ["spotify.com"],
            "applemusic": ["music.apple.com", "apple.com"],
            "soundcloud": ["soundcloud.com"],
            "facebook": ["facebook.com", "fb.watch"],
            "reddit": ["reddit.com", "redd.it"],
            "twitch": ["twitch.tv"],
            "threads": ["threads.net"]
        }
        
        for platform, domains in platforms.items():
            if any(domain in url_lower for domain in domains):
                return platform
        return None

    def get_platform_emoji(self, platform: str) -> str:
        emojis = {
            "instagram": "📸", "tiktok": "🎵", "pinterest": "📌",
            "bilibili": "📺", "twitter": "🐦", "youtube": "🎥",
            "spotify": "🎧", "applemusic": "🍎", "soundcloud": "☁️",
            "facebook": "📘", "reddit": "🔴", "twitch": "🎮", 
            "threads": "🧵"
        }
        return emojis.get(platform, "📥")

    async def download_file(self, url: str, is_video: bool = False, is_audio: bool = False) -> Optional[str]:
        if not url or not isinstance(url, str):
            return None
        
        if is_audio:
            ext = ".mp3"
        elif is_video:
            ext = ".mp4"
        else:
            ext = ".jpg"
        
        path = f"downloads/{shortuuid.uuid()}{ext}"
        
        try:
            timeout = aiohttp.ClientTimeout(total=600)
            async with aiohttp.ClientSession(headers=self.headers, timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return None
                    
                    async with aiofiles.open(path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(65536):
                            if chunk:
                                await f.write(chunk)
            
            return path
        except Exception:
            return None

    async def fetch_media(self, url: str) -> Tuple[Optional[Dict], Optional[str]]:
        clean_url = self._normalize_url(url)
        platform = self.detect_platform(clean_url)
        
        if not platform:
            return None, "unsupported"

        endpoint_map = {
            "instagram": f"{self.base_url}/snap",
            "tiktok": f"{self.base_url}/snap",
            "twitter": f"{self.base_url}/snap",
            "facebook": f"{self.base_url}/snap",
            "reddit": f"{self.base_url}/snap",
            "twitch": f"{self.base_url}/snap",
            "threads": f"{self.base_url}/snap",
            "pinterest": f"{self.base_url}/pinterest",
            "bilibili": f"{self.base_url}/bilibili"
        }
        
        endpoint = endpoint_map.get(platform, f"{self.base_url}/all")
        params = {"api_key": self.api_key, "url": clean_url}
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(headers=self.headers, timeout=timeout) as session:
                async with session.get(endpoint, params=params) as resp:
                    if resp.status != 200:
                        return None, platform
                    
                    data = await resp.json()

            if isinstance(data, dict):
                if data.get("status") == "error" or data.get("error"):
                    return None, platform
            elif isinstance(data, list):
                data = {"url": data} if data else None

            return data, platform
            
        except Exception:
            return None, platform

API_KEY = os.getenv("FALLEN_API_KEY", "dbc2e5_mDyt7u3ys5DRBs5UmLHoqIq4aXqI7BaT")
api = MultiPlatformAPI(API_KEY)
bitflow = BitflowAPI()

async def safe_edit(c: Client, inline_id: str, text: str, markup=None):
    try:
        await c.edit_inline_text(inline_id, text, reply_markup=markup)
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await safe_edit(c, inline_id, text, markup)
    except Exception:
        pass

def safe_cleanup(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def safe_int(value, default=0):
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.replace(',', ''))
        except:
            return default
    return default

def parse_duration_to_seconds(duration_str) -> Optional[int]:
    if not duration_str or duration_str == "Unknown":
        return None
    try:
        if isinstance(duration_str, int):
            return duration_str
        dur_str = str(duration_str).strip()
        if ":" in dur_str:
            parts = dur_str.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return int(dur_str.replace(',', ''))
    except:
        return None

def extract_media_urls(data: Dict) -> Tuple[Optional[str], Optional[str]]:
    video_url = None
    photo_url = None
    
    try:
        url_field = data.get("url")
        
        if url_field is not None:
            if isinstance(url_field, list) and len(url_field) > 0:
                first_item = url_field[0]
                
                if isinstance(first_item, dict):
                    url_from_dict = first_item.get("url")
                    media_type = first_item.get("type", "").lower()
                    media_ext = first_item.get("ext", "").lower()
                    
                    if isinstance(url_from_dict, list) and len(url_from_dict) > 0:
                        nested_item = url_from_dict[0]
                        
                        if isinstance(nested_item, dict):
                            actual_url = nested_item.get("url")
                            nested_type = nested_item.get("type", "").lower()
                            nested_ext = nested_item.get("ext", "").lower()
                            
                            if isinstance(actual_url, str):
                                if nested_type in ['mp4', 'video', 'mov'] or nested_ext in ['mp4', 'mov']:
                                    video_url = actual_url
                                else:
                                    photo_url = actual_url
                        
                        elif isinstance(nested_item, str):
                            if any(ext in nested_item.lower() for ext in ['.mp4', '.mov', 'video']):
                                video_url = nested_item
                            else:
                                photo_url = nested_item
                    
                    elif isinstance(url_from_dict, str):
                        if media_type in ['mp4', 'video', 'mov'] or media_ext in ['mp4', 'mov']:
                            video_url = url_from_dict
                        else:
                            photo_url = url_from_dict
                
                elif isinstance(first_item, str):
                    if any(ext in first_item.lower() for ext in ['.mp4', '.mov', 'video']):
                        video_url = first_item
                    else:
                        photo_url = first_item
            
            elif isinstance(url_field, str):
                if any(ext in url_field.lower() for ext in ['.mp4', '.mov', 'video']):
                    video_url = url_field
                else:
                    photo_url = url_field

        if not video_url:
            if "video" in data and isinstance(data["video"], list) and len(data["video"]) > 0:
                video_item = data["video"][0]
                
                if isinstance(video_item, dict):
                    video_url = video_item.get("video") or video_item.get("url")
                    if not photo_url:
                        photo_url = video_item.get("thumbnail") or video_item.get("thumb")
                
                elif isinstance(video_item, str):
                    video_url = video_item
            else:
                video_url = (
                    data.get("video") or 
                    data.get("video_url") or 
                    data.get("download_url") or 
                    data.get("hd") or 
                    data.get("sd")
                )

        if not photo_url:
            if "image" in data and isinstance(data["image"], list) and len(data["image"]) > 0:
                image_item = data["image"][0]
                
                if isinstance(image_item, dict):
                    photo_url = image_item.get("url")
                elif isinstance(image_item, str):
                    photo_url = image_item
            else:
                thumb_field = (
                    data.get("thumb") or 
                    data.get("thumbnail") or 
                    data.get("image") or 
                    data.get("cover")
                )
                
                if isinstance(thumb_field, list) and len(thumb_field) > 0:
                    first_thumb = thumb_field[0]
                    photo_url = first_thumb.get("url") if isinstance(first_thumb, dict) else first_thumb
                elif isinstance(thumb_field, str):
                    photo_url = thumb_field
    
    except Exception:
        pass
    
    return video_url, photo_url

def extract_metadata(data: Dict, platform: str) -> Dict:
    metadata = {
        "title": f"{platform.title()} Media",
        "author": platform.title(),
        "likes": 0,
        "comments": 0,
        "views": 0
    }
    
    try:
        if "meta" in data and isinstance(data["meta"], dict):
            meta = data["meta"]
            metadata["title"] = meta.get("title", "") or metadata["title"]
            metadata["author"] = (
                meta.get("username") or 
                meta.get("author") or 
                meta.get("artist") or 
                metadata["author"]
            )
            metadata["likes"] = safe_int(meta.get("like_count") or meta.get("likes"))
            metadata["comments"] = safe_int(meta.get("comment_count") or meta.get("comments"))
            metadata["views"] = safe_int(meta.get("view_count") or meta.get("views"))
        
        metadata["title"] = data.get("title") or data.get("name") or metadata["title"]
        
        if not metadata["author"] or metadata["author"] == platform.title():
            metadata["author"] = (
                data.get("username") or 
                data.get("author") or 
                data.get("artist") or 
                data.get("uploader") or 
                metadata["author"]
            )
        
        if metadata["likes"] == 0:
            metadata["likes"] = safe_int(data.get("like_count") or data.get("likes"))
        
        if metadata["comments"] == 0:
            metadata["comments"] = safe_int(data.get("comment_count") or data.get("comments"))
        
        if metadata["views"] == 0:
            metadata["views"] = safe_int(data.get("view_count") or data.get("views"))
    
    except Exception:
        pass
    
    return metadata

@app.on_inline_query()
async def inline_handler(c: Client, q: InlineQuery):
    text = q.query.strip() if q.query else ""
    bot = await get_bot_username()

    if text.lower().startswith("#gpt"):
        prompt = text[4:].strip()
        if not prompt:
            return await q.answer([
                InlineQueryResultArticle(
                    id="gpt_usage",
                    title="💡 GPT Usage",
                    description="Ask ChatGPT",
                    input_message_content=InputTextMessageContent(
                        f"Usage: `@{bot} #gpt question`"
                    )
                )
            ], cache_time=0)
        
        sid = shortuuid.uuid()[:8]
        pending[f"gpt:{sid}"] = {"type": "gpt", "prompt": prompt}
        
        return await q.answer([
            InlineQueryResultArticle(
                id=shortuuid.uuid(),
                title="🤖 Generate GPT Answer",
                description=f"Prompt: {prompt[:40]}...",
                input_message_content=InputTextMessageContent(
                    f"✨ **Prompt:** {prompt}\n\n👉 Tap below to generate"
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(font("⚡ Generate"), callback_data=f"gpt:{sid}", style=ButtonStyle.SUCCESS)
                ]])
            )
        ], cache_time=0)

    if text.startswith("!yt ") or text.startswith("!youtube "):
        search_query = text.split(" ", 1)[1].strip() if len(text.split()) > 1 else ""
        if not search_query:
            return await q.answer([
                InlineQueryResultArticle(
                    id="yt_usage",
                    title="🎥 YouTube",
                    description="!yt song name",
                    input_message_content=InputTextMessageContent(
                        f"🎥 **YouTube**: `@{bot} !yt song name`"
                    )
                )
            ], cache_time=0)
        
        results = await bitflow.search(search_query, 10)
        if not results:
            return await q.answer([
                InlineQueryResultArticle(
                    id="no_results",
                    title="❌ No Results",
                    description="No songs found",
                    input_message_content=InputTextMessageContent(
                        f"❌ No results found for: {search_query}"
                    )
                )
            ], cache_time=0)
        
        answers = []
        for track in results[:10]:
            track_id = shortuuid.uuid()[:12]
            callback_data = f"music:youtube:{track_id}"
            pending[callback_data] = {
                "type": "youtube",
                "url": track['url'],
                "query": search_query
            }
            
            answers.append(
                InlineQueryResultArticle(
                    id=shortuuid.uuid(),
                    title=f"🎥 {track['title']}",
                    description=f"👤 {track['artist']} | ⏱ {track['duration']}",
                    thumb_url=track['thumbnail'] or "https://files.catbox.moe/dv0wud.jpg",
                    input_message_content=InputTextMessageContent(
                        f"🎥 **{track['title']}**\n👤 {track['artist']}\n\n⏳ Preparing..."
                    ),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(font("⬇️ Download Audio"), callback_data=callback_data, style=ButtonStyle.PRIMARY)
                    ]])
                )
            )
        
        return await q.answer(answers, cache_time=0)

    if text.startswith("!spotify ") or text.startswith("!sp "):
        search_query = text.split(" ", 1)[1].strip() if len(text.split()) > 1 else ""
        if not search_query:
            return await q.answer([
                InlineQueryResultArticle(
                    id="sp_usage",
                    title="🎧 Spotify",
                    description="!spotify song name",
                    input_message_content=InputTextMessageContent(
                        f"🎧 **Spotify**: `@{bot} !spotify song name`"
                    )
                )
            ], cache_time=0)
        
        results = await bitflow.search(search_query, 10)
        if not results:
            return await q.answer([
                InlineQueryResultArticle(
                    id="no_results",
                    title="❌ No Results",
                    description="No songs found",
                    input_message_content=InputTextMessageContent(
                        f"❌ No results found for: {search_query}"
                    )
                )
            ], cache_time=0)
        
        answers = []
        for track in results[:10]:
            track_id = shortuuid.uuid()[:12]
            callback_data = f"music:spotify:{track_id}"
            pending[callback_data] = {
                "type": "spotify",
                "url": track['url'],
                "query": search_query
            }
            
            answers.append(
                InlineQueryResultArticle(
                    id=shortuuid.uuid(),
                    title=f"🎧 {track['title']}",
                    description=f"👤 {track['artist']} | ⏱ {track['duration']}",
                    thumb_url=track['thumbnail'] or "https://files.catbox.moe/dv0wud.jpg",
                    input_message_content=InputTextMessageContent(
                        f"🎧 **{track['title']}**\n👤 {track['artist']}\n\n⏳ Preparing..."
                    ),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(font("⬇️ Download"), callback_data=callback_data, style=ButtonStyle.PRIMARY)
                    ]])
                )
            )
        
        return await q.answer(answers, cache_time=0)

    if text.startswith("!apple ") or text.startswith("!am "):
        search_query = text.split(" ", 1)[1].strip() if len(text.split()) > 1 else ""
        if not search_query:
            return await q.answer([
                InlineQueryResultArticle(
                    id="am_usage",
                    title="🍎 Apple Music",
                    description="!apple song name",
                    input_message_content=InputTextMessageContent(
                        f"🍎 **Apple Music**: `@{bot} !apple song name`"
                    )
                )
            ], cache_time=0)
        
        results = await bitflow.search(search_query, 10)
        if not results:
            return await q.answer([
                InlineQueryResultArticle(
                    id="no_results",
                    title="❌ No Results",
                    description="No songs found",
                    input_message_content=InputTextMessageContent(
                        f"❌ No results found for: {search_query}"
                    )
                )
            ], cache_time=0)
        
        answers = []
        for track in results[:10]:
            track_id = shortuuid.uuid()[:12]
            callback_data = f"music:applemusic:{track_id}"
            pending[callback_data] = {
                "type": "applemusic",
                "url": track['url'],
                "query": search_query
            }
            
            answers.append(
                InlineQueryResultArticle(
                    id=shortuuid.uuid(),
                    title=f"🍎 {track['title']}",
                    description=f"👤 {track['artist']} | ⏱ {track['duration']}",
                    thumb_url=track['thumbnail'] or "https://files.catbox.moe/dv0wud.jpg",
                    input_message_content=InputTextMessageContent(
                        f"🍎 **{track['title']}**\n👤 {track['artist']}\n\n⏳ Preparing..."
                    ),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(font("⬇️ Download"), callback_data=callback_data, style=ButtonStyle.PRIMARY)
                    ]])
                )
            )
        
        return await q.answer(answers, cache_time=0)

    if (text.startswith("!dl ") or text.startswith("!reel ")) and len(text.split()) > 1:
        url = text.split(" ", 1)[1].strip()
        platform = api.detect_platform(url)
        
        if not platform:
            return await q.answer([
                InlineQueryResultArticle(
                    id="dl_bad",
                    title="❌ Unsupported Platform",
                    description="Check supported platforms",
                    input_message_content=InputTextMessageContent(
                        f"❌ Unsupported URL\n\n"
                        f"✅ **Social:** Instagram, TikTok, Pinterest, Twitter, "
                        f"Facebook, Reddit, Twitch, Threads, Bilibili"
                    )
                )
            ], cache_time=0)
        
        emoji = api.get_platform_emoji(platform)
        callback_data = f"dl:{platform}:{shortuuid.uuid()[:12]}"
        pending[callback_data] = {"type": "download", "url": url, "platform": platform}
        
        if platform in ["instagram", "tiktok"]:
            media_type = "Reel/Video"
        else:
            media_type = "Media"
        
        return await q.answer([
            InlineQueryResultPhoto(
                id=shortuuid.uuid(),
                title=f"{emoji} Download {media_type}",
                description=f"From {platform.title()}",
                photo_url="https://files.catbox.moe/dv0wud.jpg",
                caption=f"{emoji} **Download {media_type}**\n📱 {platform.title()}\n🔗 [View]({url})",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(font("⬇️ Download"), callback_data=callback_data, style=ButtonStyle.PRIMARY)
                ]])
            )
        ], cache_time=0)

    if text and (text.startswith("@") or text.split()[0].lstrip("@").isdigit()):
        parts = text.split(" ", 1)
        username = parts[0].lstrip("@")
        msg = parts[1] if len(parts) > 1 else ""
        
        if not username or not msg:
            return await q.answer([
                InlineQueryResultArticle(
                    id="w_help",
                    title="📝 𝐖ʜɪsᴘᴇʀ",
                    description="𝐒ᴇᴄʀᴇᴛ 𝐌ᴀssᴀɢᴇ",
                    input_message_content=InputTextMessageContent(
                        f"Usage: `@{bot} @username message`"
                    )
                )
            ], cache_time=0)
        
        sender_username = q.from_user.username or ""
        sender_id = str(q.from_user.id)
        
        if (username.lower() == sender_username.lower() or 
            username == sender_id or 
            (username.isdigit() and int(username) == q.from_user.id)):
            return await q.answer([
                InlineQueryResultArticle(
                    id="self_whisper",
                    title="❌ Cannot Send to Self",
                    description="Invalid",
                    input_message_content=InputTextMessageContent(
                        "❌ You cannot whisper to yourself"
                    )
                )
            ], cache_time=0)
        
        wid = shortuuid.uuid()
        sid = wid[:8]
        pending[f"w:{sid}"] = wid
        
        target_id = int(username) if username.isdigit() else username
        pending[f"whisper_data:{wid}"] = {
            "from_id": q.from_user.id,
            "to_id": target_id,
            "target_username": username,
            "sender_name": q.from_user.first_name or "Someone",
            "message": msg,
            "read": False
        }
        
        asyncio.create_task(save_whisper(wid, pending[f"whisper_data:{wid}"]))
        
        sender_mention = f"<a href='tg://user?id={q.from_user.id}'>{q.from_user.first_name or 'Someone'}</a>"
        whisper_text = f"<blockquote><b>🔐𝐖ʜɪsᴘᴇʀ 𝐅ʀᴏᴍ {sender_mention} 𝐅ᴏʀ @{username}</b></blockquote>"
        
        return await q.answer([
            InlineQueryResultArticle(
                id=shortuuid.uuid(),
                title=f"Whisper to {username}",
                description="𝐒ᴇᴄʀᴇᴛ 𝐌ᴀssᴀɢᴇ",
                input_message_content=InputTextMessageContent(
                    whisper_text,
                    parse_mode=enums.ParseMode.HTML
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(font("📨 𝐑ᴇᴀᴅ 📨"), callback_data=f"w:{sid}", style=ButtonStyle.SUCCESS)
                ]])
            )
        ], cache_time=0)

    return await q.answer([
        InlineQueryResultArticle(
            id="help_w",
            title="📝 𝐖ʜɪsᴘᴇʀ",
            description="@username message",
            input_message_content=InputTextMessageContent(
                f"📝 **Whisper**: `@{bot} @user message`"
            )
        ),
        InlineQueryResultArticle(
            id="help_g",
            title="💡 GPT",
            description="#gpt question",
            input_message_content=InputTextMessageContent(
                f"💡 **GPT**: `@{bot} #gpt question`"
            )
        )
    ], cache_time=0)

@app.on_callback_query(filters.regex(r"^gpt:"))
async def gpt_cb(c: Client, cb: CallbackQuery):
    sid = cb.data.split(":", 1)[1]
    data = pending.get(f"gpt:{sid}")
    
    if not data or data.get("type") != "gpt":
        return await cb.answer(font("❌ Expired"), show_alert=True)
    
    prompt = data.get("prompt")
    
    try:
        bot = await get_bot_username()
        
        if cb.inline_message_id:
            await safe_edit(c, cb.inline_message_id, "⏳ Processing...")
        
        ans = await GPTGeneration().create(prompt)
        
        if len(ans) > 3800:
            ans = ans[:3790] + "..."
        
        if cb.inline_message_id:
            response_text = (
                f"✨ <b>GPT</b>\n\n"
                f"<b>Q:</b> <code>{prompt}</code>\n\n"
                f"<b>A:</b> {ans}\n\n"
                f"💡 <code>@{bot} #gpt question</code>"
            )
            await safe_edit(c, cb.inline_message_id, response_text)
        
        pending.pop(f"gpt:{sid}", None)
        
    except Exception as e:
        logging.error(f"GPT error: {e}")
        if cb.inline_message_id:
            await safe_edit(c, cb.inline_message_id, "❌ Error generating response")

@app.on_callback_query(filters.regex(r"^w:"))
async def whisper_cb(c: Client, cb: CallbackQuery):
    sid = cb.data.split(":", 1)[1]
    wid = pending.get(f"w:{sid}", sid)
    
    data = await get_whisper(wid)
    if not data:
        data = pending.get(f"whisper_data:{wid}")
        if not data:
            return await cb.answer(font("❌ Not found"), show_alert=True)
    
    user_id = cb.from_user.id
    username = cb.from_user.username or ""
    sender_id = data.get("from_id")
    
    is_sender = (user_id == sender_id)
    is_authorized = False
    target_username = data.get("target_username", "")
    
    if isinstance(data["to_id"], int):
        if user_id == data["to_id"]:
            is_authorized = True
    elif isinstance(data["to_id"], str):
        if (data["to_id"].lower() == username.lower() or 
            (data["to_id"].isdigit() and user_id == int(data["to_id"]))):
            is_authorized = True
    
    if target_username:
        if ((target_username.isdigit() and user_id == int(target_username)) or 
            target_username.lower() == username.lower()):
            is_authorized = True
    
    if not (is_sender or is_authorized):
        return await cb.answer(font("🚫 Not for you"), show_alert=True)
    
    if data.get("read") and is_authorized and not is_sender:
        if cb.inline_message_id:
            reader_mention = f"<a href='tg://user?id={cb.from_user.id}'>{data.get('reader','Someone')}</a>"
            await safe_edit(c, cb.inline_message_id, f"✅ {reader_mention} already read this whisper")
        return await cb.answer(font("⏳ Already read!"), show_alert=True)
    
    reader_name = cb.from_user.first_name or "Someone"
    
    if is_sender:
        await cb.answer(f"📝𝐘ᴏᴜʀ 𝐌ᴀssᴀɢᴇ ➛ {data['message']}", show_alert=True)
    else:
        await mark_read(wid, reader_name)
        
        if cb.inline_message_id:
            reader_mention = f"<a href='tg://user?id={user_id}'>{reader_name}</a>"
            await safe_edit(c, cb.inline_message_id, f"✅ {reader_mention} 𝐑ᴇᴀᴅ 𝐓ʜᴇ 𝐖ʜɪsᴘᴇʀ.")
        
        await cb.answer(f"🔐 {data['message']}", show_alert=True)
        
        pending.pop(f"w:{sid}", None)
        pending.pop(f"whisper_data:{wid}", None)

@app.on_callback_query(filters.regex(r"^music:"))
async def music_cb(c: Client, cb: CallbackQuery):
    file_path = None
    thumb_path = None
    
    try:
        _, platform, track_id = cb.data.split(":", 2)
        data = pending.get(cb.data)
        
        if not data or data.get("type") not in ["youtube", "spotify", "applemusic"]:
            return await cb.answer(font("❌ Expired"), show_alert=True)
        
        await cb.answer(font("⏳ Processing..."))
        
        bot = await get_bot_username()
        emoji = "🎥" if platform == "youtube" else ("🎧" if platform == "spotify" else "🍎")
        
        await safe_edit(c, cb.inline_message_id, f"{emoji} <b>Fetching track info...</b>")
        
        query = data.get("query") or data.get("url")
        
        await safe_edit(c, cb.inline_message_id, f"{emoji} <b>Downloading...</b>")
        
        file_path, metadata = await bitflow.download_audio(query)
        
        if not file_path or not metadata:
            await safe_edit(c, cb.inline_message_id, "❌ Download failed. Please try again.")
            return
        
        title = metadata['title']
        artist = metadata['artist']
        duration = metadata['duration']
        thumb_url = metadata['thumbnail']
        
        duration_seconds = parse_duration_to_seconds(duration) or 180
        
        if thumb_url and isinstance(thumb_url, str):
            thumb_path = await api.download_file(thumb_url, is_audio=False)
        
        await safe_edit(c, cb.inline_message_id, f"{emoji} <b>Uploading audio...</b>")
        
        ist = timezone(timedelta(hours=5, minutes=30))
        ist_time = datetime.now(ist)
        
        platform_name = "YouTube" if platform == "youtube" else ("Spotify" if platform == "spotify" else "Apple Music")
        
        caption = (
            f"{emoji} <b>{title}</b>\n\n"
            f"👤 {artist}\n"
            f"⏱ {duration}\n"
            f"🎵 {platform_name}\n\n"
            f"📅 {ist_time.strftime('%d %b %Y')}\n"
            f"🕐 {ist_time.strftime('%I:%M %p IST')}\n\n"
            f"💡 <code>@{bot} !{platform} song</code>"
        )
        
        await c.edit_inline_media(
            cb.inline_message_id,
            InputMediaAudio(
                media=file_path,
                caption=caption,
                parse_mode=enums.ParseMode.HTML,
                thumb=thumb_path if thumb_path else None,
                title=title,
                performer=artist,
                duration=duration_seconds
            )
        )
        
        safe_cleanup(file_path)
        if thumb_path:
            safe_cleanup(thumb_path)
        
        pending.pop(cb.data, None)
        
    except Exception as e:
        logging.error(f"Music callback error: {e}")
        if file_path:
            safe_cleanup(file_path)
        if thumb_path:
            safe_cleanup(thumb_path)
        
        if cb.inline_message_id:
            await safe_edit(c, cb.inline_message_id, "❌ Upload error")

@app.on_callback_query(filters.regex(r"^dl:"))
async def download_cb(c: Client, cb: CallbackQuery):
    file_path = None
    thumb_path = None
    
    try:
        _, platform, sid = cb.data.split(":", 2)
        data = pending.get(cb.data)
        
        if not data or data.get("type") != "download":
            return await cb.answer(font("❌ Expired"), show_alert=True)
        
        url = data.get("url")
        await cb.answer(font("⏳ Processing..."))
        
        bot = await get_bot_username()
        emoji = api.get_platform_emoji(platform)
        
        await safe_edit(c, cb.inline_message_id, f"{emoji} <b>Fetching media...</b>")
        
        media_data, detected_platform = await api.fetch_media(url)
        
        if not media_data:
            return await safe_edit(
                c, cb.inline_message_id,
                f"❌ Failed to fetch media\n\nCheck URL or try again"
            )
        
        video_url, photo_url = extract_media_urls(media_data)
        
        if not (video_url or photo_url):
            return await safe_edit(c, cb.inline_message_id, "❌ No media found")
        
        metadata = extract_metadata(media_data, platform)
        
        await safe_edit(
            c, cb.inline_message_id,
            f"{emoji} <b>Downloading from @{metadata['author']}...</b>"
        )
        
        is_video = bool(video_url)
        download_url = video_url if is_video else photo_url
        
        file_path = await api.download_file(download_url, is_video)
        
        if not file_path:
            return await safe_edit(c, cb.inline_message_id, "❌ Download failed")
        
        await safe_edit(c, cb.inline_message_id, f"{emoji} <b>Uploading...</b>")
        
        ist = timezone(timedelta(hours=5, minutes=30))
        ist_time = datetime.now(ist)
        
        caption = f"{emoji} <b>{platform.title()}</b> {'Video' if is_video else 'Photo'}\n\n"
        
        if metadata['author'] and metadata['author'] != platform.title():
            platform_links = {
                "instagram": f"https://instagram.com/{metadata['author']}",
                "twitter": f"https://twitter.com/{metadata['author']}",
                "tiktok": f"https://tiktok.com/@{metadata['author']}"
            }
            
            if platform in platform_links:
                caption += f"👤 <a href='{platform_links[platform]}'>@{metadata['author']}</a>\n"
            else:
                caption += f"👤 @{metadata['author']}\n"
        
        if metadata['likes'] > 0:
            caption += f"❤️ {metadata['likes']:,}\n"
        if metadata['comments'] > 0:
            caption += f"💬 {metadata['comments']:,}\n"
        if metadata['views'] > 0:
            caption += f"👁 {metadata['views']:,}\n"
        
        caption += (
            f"\n📅 {ist_time.strftime('%d %b %Y')}\n"
            f"🕐 {ist_time.strftime('%I:%M %p IST')}\n\n"
            f"💡 <code>@{bot} !dl [url]</code>"
        )
        
        if is_video:
            await c.edit_inline_media(
                cb.inline_message_id,
                InputMediaVideo(
                    media=file_path,
                    caption=caption,
                    parse_mode=enums.ParseMode.HTML
                )
            )
        else:
            with open(file_path, "rb") as f:
                photo_data = io.BytesIO(f.read())
            photo_data.name = "photo.jpg"
            
            await c.edit_inline_media(
                cb.inline_message_id,
                InputMediaPhoto(
                    media=photo_data,
                    caption=caption,
                    parse_mode=enums.ParseMode.HTML
                )
            )
        
        safe_cleanup(file_path)
        pending.pop(cb.data, None)
        
    except Exception as e:
        logging.error(f"Download error: {e}")
        if file_path:
            safe_cleanup(file_path)
        if thumb_path:
            safe_cleanup(thumb_path)
        
        if cb.inline_message_id:
            await safe_edit(c, cb.inline_message_id, "❌ Download error")
