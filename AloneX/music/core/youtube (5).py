# Copyright (c) 2025 @THECDERQUEEN
# Licensed under the MIT License.
# This file is part of @SHONA_BOTS
#
# Single-API YouTube/Platform core (AloneMusic API — https://yt.riteshyt.in/docs)
#   search / details / playlist ..... YouTube, Spotify (track/album/playlist/artist)
#   /play  (audio) .................. /download?dl_type=audio
#   /vplay (video) .................. /download?dl_type=video&quality=...
#   every other platform ............ /api/platform/extract (Instagram, TikTok,
#                                     SoundCloud, JioSaavn, Apple Music, ...)
#   autoplay ........................ YouTube mix (innertube, same as the old yt.py)
#                                     -> fallback: search through the API

import asyncio
import hashlib
import os
import random
import re
from pathlib import Path
from urllib.parse import urlencode

import aiohttp
from py_yt import Playlist, VideosSearch

from AloneX import config, logger
from AloneX.helpers import Track, utils

DOWNLOAD_DIR = "downloads"

MIN_FILE_SIZE = 100000  # bytes; smaller than this is treated as a failed download

_VID_RE = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})")
_BARE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

# Platforms the API's /api/platform/extract endpoint supports (docs list).
# Image-only sites (Unsplash, Pexels, Giphy, ...) are left out on purpose.
PLATFORM_DOMAINS = [
    "spotify.com", "spotify.link", "jiosaavn.com", "saavn.com", "soundcloud.com",
    "music.apple.com", "gaana.com", "deezer.com", "deezer.page.link", "resso.com",
    "resso.me", "tidal.com", "instagram.com", "instagr.am", "tiktok.com",
    "twitter.com", "x.com", "t.co", "pinterest.com", "pin.it", "reddit.com",
    "redd.it", "facebook.com", "fb.watch", "fb.com", "threads.net", "snapchat.com",
    "dailymotion.com", "dai.ly", "vimeo.com", "bandcamp.com", "mixcloud.com",
    "vk.com", "vk.ru", "rumble.com", "streamable.com", "audiomack.com", "ok.ru",
    "coub.com", "douyin.com", "kuaishou.com", "triller.co", "nicovideo.jp",
    "odysee.com", "9gag.com", "likee.video", "newgrounds.com", "izlesene.com",
    "bitchute.com", "veoh.com", "imgur.com", "loom.com", "wistia.com", "trovo.live",
    "weibo.com", "weibo.cn", "rutube.ru", "ted.com", "archive.org", "hearthis.at",
    "jamendo.com", "reverbnation.com", "audius.co", "boomplay.com", "anghami.com",
    "wynk.in", "wynkmusic.co", "hungama.com", "youku.com", "iqiyi.com",
    "xiaohongshu.com", "xhslink.com", "afreecatv.com", "napster.com", "kugou.com",
    "kuwo.cn", "y.qq.com", "music.163.com", "redbull.tv", "iheart.com", "tunein.com",
    "pandora.com", "last.fm", "genius.com", "terabox.com", "1024terabox.com",
    "twitch.tv", "clips.twitch.tv", "kick.com", "bilibili.com", "b23.tv",
    "mxplayer.in", "bsky.app", "linkedin.com", "tumblr.com", "imdb.com",
]

# YouTube innertube (same endpoint the YouTube site itself uses) — used to
# fetch the "mix" (RD<videoId>) for autoplay without going through yt-dlp.
YT_BASE = "https://www.youtube.com"
YT_API_KEY = "e1a859_PFC9-tOJJQ9Y9BG3ecBZixSL2nNs1ln-"
_WEB_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
YT_PROFILES = [
    {"name": "WEB", "version": "2.20250101.01.00", "id": "1", "ua": _WEB_UA, "origin": YT_BASE},
    {
        "name": "ANDROID_MUSIC", "version": "7.03.51", "id": "21",
        "ua": "com.google.android.apps.youtube.music/7.03.51 (Linux; U; Android 14) gzip",
        "extra": {"osName": "Android", "osVersion": "14", "androidSdkVersion": 34},
    },
    {
        "name": "WEB_EMBEDDED_PLAYER", "version": "1.20250101.01.00", "id": "56",
        "ua": _WEB_UA, "origin": YT_BASE, "embed": YT_BASE + "/",
    },
    {
        "name": "TVHTML5_SIMPLY_EMBEDDED_PLAYER", "version": "2.0", "id": "85",
        "ua": "Mozilla/5.0 (SmartHub; SMART-TV; U; Linux/SmartTV) AppleWebKit/537.42 (KHTML, like Gecko) SmartTV Safari/537.42",
        "origin": YT_BASE, "embed": YT_BASE + "/",
    },
]

# New API (single API: https://yt.riteshyt.in/docs) — search, /play, /vplay, platforms.
# Key: RITESH_API_KEY (or the old API_KEY var) from Heroku Config Vars.
RITESH_API_URL = (
    getattr(config, "RITESH_API_URL", "") or os.getenv("RITESH_API_URL", "") or "https://api.riteshyt.in"
).rstrip("/")
RITESH_API_KEY = (
    getattr(config, "RITESH_API_KEY", "")
    or os.getenv("RITESH_API_KEY", "")
    or getattr(config, "API_KEY", "")
    or os.getenv("API_KEY", "")
    or ""
).strip()


class YouTube:
    def __init__(self):
        self.base = f"{YT_BASE}/watch?v="
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )
        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
            r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
            r"|playlist\?list=PL[A-Za-z0-9_-]+|[A-Za-z0-9_-]{11}))\S*"
        )
        self.platform_regex = re.compile(
            r"(?i)^https?://(?:[\w-]+\.)*(?:"
            + "|".join(re.escape(d) for d in PLATFORM_DOMAINS)
            + r")(?::\d+)?(?:[/?#]|$)"
        )
        self.spotify_regex = re.compile(
            r"(?i)^https?://(?:[\w-]+\.)*spotify\.com/(?:intl-[a-z]+/)?"
            r"(track|playlist|album|artist)/[A-Za-z0-9]+"
        )

        self.api_url = RITESH_API_URL
        self.api_key = RITESH_API_KEY
        if not self.api_key:
            logger.warning("[API] RITESH_API_KEY / API_KEY is not set — search/play/vplay will not work.")
        else:
            logger.info(f"[YouTube] single-API core loaded ({self.api_url}).")

        self._session: aiohttp.ClientSession | None = None
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # ---------------- small helpers ----------------

    def _mask(self, text) -> str:
        text = str(text)
        return text.replace(self.api_key, "***") if self.api_key else text

    async def _http(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def is_platform_url(self, url: str) -> bool:
        return bool(self.platform_regex.search((url or "").strip()))

    def valid(self, url: str) -> bool:
        if bool(re.match(self.regex, url)):
            return True
        return self.is_platform_url(url)

    def invalid(self, url: str) -> bool:
        if self.valid(url):
            return False
        return bool(re.match(self.iregex, url))

    @staticmethod
    def _vid(text: str) -> str | None:
        """11-char YouTube id from a link or a bare id."""
        text = (text or "").strip()
        if _BARE_ID_RE.match(text):
            return text
        m = _VID_RE.search(text)
        return m.group(1) if m else None

    def _is_youtube(self, text: str) -> bool:
        text = (text or "").strip()
        return bool(re.search(r"youtu(?:\.be|be\.com)", text)) or bool(_BARE_ID_RE.match(text))

    def _quality(self) -> int:
        m = re.search(r"(\d{3,4})", str(getattr(config, "VIDEO_QUALITY", "") or ""))
        return int(m.group(1)) if m else 720

    @staticmethod
    def _dur_to_sec(value) -> int:
        try:
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str) and value.strip():
                if value.strip().isdigit():
                    return int(value.strip())
                return int(utils.to_seconds(value.strip()))
        except Exception:
            pass
        return 0

    def _format_duration(self, seconds: int) -> str:
        seconds = max(int(seconds or 0), 0)
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    def _format_views(self, count) -> str:
        try:
            count = int(count)
        except (TypeError, ValueError):
            return ""
        if not count:
            return ""
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M views"
        if count >= 1_000:
            return f"{count / 1_000:.1f}K views"
        return f"{count} views"

    @staticmethod
    def _yt_time_to_sec(text: str) -> int:
        total = 0
        for part in (text or "").split(":"):
            if not part.strip().isdigit():
                return 0
            total = total * 60 + int(part)
        return total

    @staticmethod
    def _chan(value, default: str) -> str:
        if isinstance(value, dict):
            value = value.get("name")
        return str(value) if value else default

    @staticmethod
    def _yt_thumb(vid: str) -> str:
        return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

    # ---------------- API calls ----------------

    async def _api_json(self, path: str, params: dict, timeout: int = 20) -> dict | None:
        """GET {api}{path}?...&api_key=... -> parsed JSON, or None on any failure."""
        if not self.api_key:
            return None
        q = dict(params)
        q["api_key"] = self.api_key
        try:
            session = await self._http()
            async with session.get(
                f"{self.api_url}{path}", params=q, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 429:
                    logger.warning(f"[API] {path}: daily limit / quota exceeded (HTTP 429)")
                    return None
                if resp.status != 200:
                    body = self._mask((await resp.text())[:150])
                    logger.warning(f"[API] {path}: HTTP {resp.status} {body}")
                    return None
                data = await resp.json(content_type=None)
                return data if isinstance(data, dict) else None
        except Exception as e:
            logger.warning(f"[API] {path} failed: {self._mask(e)}")
            return None

    async def _search_items(self, query: str, limit: int = 1) -> list[dict]:
        """YouTube search through the API (py_yt only as a safety net).
        Items: id, title, duration(str), duration_sec, thumbnail, url, channel, views."""
        items: list[dict] = []
        data = await self._api_json("/search", {"q": query, "limit": limit}, timeout=15)
        for d in (data or {}).get("result") or []:
            if not isinstance(d, dict) or not d.get("id"):
                continue
            if d.get("type", "video") not in ("video", None):
                continue
            items.append(self._norm_item(d))
        if items:
            return items

        try:
            res = await VideosSearch(query, limit=limit, with_live=False).next()
            for d in (res or {}).get("result", []):
                if d.get("id"):
                    items.append(self._norm_item(d))
        except Exception as e:
            logger.error(f"Search error: {e}")
        return items

    def _norm_item(self, d: dict) -> dict:
        vid = d.get("id")
        dur = d.get("duration")
        thumbs = d.get("thumbnails") or [{}]
        thumb = ((thumbs[-1] or {}).get("url") or "").split("?")[0] or self._yt_thumb(vid)
        views = d.get("viewCount") or {}
        return {
            "id": vid,
            "title": d.get("title") or "Unknown Track",
            "duration": dur if isinstance(dur, str) else self._format_duration(self._dur_to_sec(dur)),
            "duration_sec": self._dur_to_sec(dur),
            "thumbnail": thumb,
            "url": d.get("link") or self.base + vid,
            "channel": self._chan(d.get("channel"), "YouTube"),
            "views": views.get("short") if isinstance(views, dict) else (views or ""),
        }

    def _track_from_item(self, it: dict, m_id: int = 0, video: bool = False) -> Track:
        return Track(
            id=it["id"],
            channel_name=it["channel"],
            duration=it["duration"],
            duration_sec=it["duration_sec"],
            message_id=m_id,
            title=str(it["title"])[:25],
            thumbnail=it["thumbnail"],
            url=it["url"],
            view_count=it["views"],
            video=video,
        )

    async def _track_from_details(
        self, link: str, m_id: int, video: bool, channel: str = "YouTube"
    ) -> Track | None:
        d = await self._api_json("/details", {"link": link}, timeout=20)
        if not d or not d.get("vidid"):
            return None
        vid = d["vidid"]
        sec = self._dur_to_sec(d.get("duration_sec") or d.get("duration_min"))
        return Track(
            id=vid,
            channel_name=channel,
            duration=d.get("duration_min") or self._format_duration(sec),
            duration_sec=sec,
            message_id=m_id,
            title=str(d.get("title") or "Unknown Track")[:25],
            thumbnail=d.get("thumbnail") or self._yt_thumb(vid),
            url=d.get("link") or self.base + vid,
            view_count="",
            video=video,
        )

    async def _playlist_tracks(
        self, url: str, limit: int, user: str | None, video: bool, m_id: int = 0, channel: str = "YouTube"
    ) -> list[Track]:
        d = await self._api_json("/playlist", {"link": url, "limit": limit}, timeout=60)
        tracks: list[Track] = []
        for v in ((d or {}).get("videos") or [])[:limit]:
            if not isinstance(v, dict):
                continue
            vid = v.get("vidid") or v.get("id")
            if not vid:
                continue
            sec = self._dur_to_sec(v.get("duration_sec") or v.get("duration_min"))
            tracks.append(
                Track(
                    id=vid,
                    channel_name=self._chan(v.get("channel") or v.get("artist"), channel),
                    duration=v.get("duration_min") or self._format_duration(sec),
                    duration_sec=sec,
                    message_id=m_id,
                    title=str(v.get("title") or "Unknown Track")[:25],
                    thumbnail=v.get("thumbnail") or self._yt_thumb(vid),
                    url=self.base + vid,
                    user=user,
                    view_count="",
                    video=video,
                )
            )
        return tracks

    # ---------------- other platforms (extractor) ----------------

    async def _extract(self, url: str) -> dict | None:
        data = await self._api_json("/api/platform/extract", {"url": url}, timeout=45)
        if not data or data.get("success") is False:
            return None
        return data

    def _platform_track(self, data: dict, url: str, m_id: int, video: bool, user: str | None = None) -> Track:
        plat = str(data.get("platform") or "Media")
        raw_id = str(data.get("id") or hashlib.sha1(url.encode()).hexdigest()[:11])
        sec = self._dur_to_sec(data.get("duration"))
        return Track(
            id=re.sub(r"[^\w.-]", "_", raw_id)[:64],
            channel_name=self._chan(data.get("uploader") or data.get("channel") or data.get("artist"), plat.title()),
            duration=self._format_duration(sec),
            duration_sec=sec,
            message_id=m_id,
            title=str(data.get("title") or f"{plat.title()} media")[:25],
            thumbnail=data.get("thumbnail") or config.DEFAULT_THUMB,
            url=url,
            user=user,
            view_count=self._format_views(data.get("view_count")),
            video=video,
        )

    async def _platform_search(self, url: str, m_id: int, video: bool, user: str | None = None):
        data = await self._extract(url)
        if not data:
            return None
        entries = data.get("entries") or data.get("tracks") or data.get("items")
        if isinstance(entries, list) and entries:
            tracks = []
            for e in entries[: config.PLAYLIST_LIMIT]:
                if not isinstance(e, dict):
                    continue
                link = e.get("url") or e.get("webpage_url") or e.get("link")
                if not link or not str(link).startswith("http"):
                    continue
                tracks.append(self._platform_track(e, str(link), m_id, video, user))
            if tracks:
                return tracks if len(tracks) > 1 else tracks[0]
        return self._platform_track(data, url, m_id, video, user)

    # ---------------- public: search / playlist ----------------

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | list[Track] | None:
        query = (query or "").strip()
        if not query:
            return None

        # Spotify: track -> YouTube id (details); album/playlist/artist -> track list
        sp = self.spotify_regex.match(query)
        if sp:
            if sp.group(1).lower() == "track":
                if t := await self._track_from_details(query, m_id, video, channel="Spotify"):
                    return t
            else:
                tracks = await self._playlist_tracks(
                    query, config.PLAYLIST_LIMIT, None, video, m_id, channel="Spotify"
                )
                if tracks:
                    return tracks if len(tracks) > 1 else tracks[0]
            return await self._platform_search(query, m_id, video)

        # every other platform -> extractor
        if self.is_platform_url(query):
            return await self._platform_search(query, m_id, video)

        # YouTube link / id / plain text
        items = await self._search_items(query, 1)
        if items:
            return self._track_from_item(items[0], m_id, video)
        if self._vid(query):
            return await self._track_from_details(query, m_id, video)
        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track]:
        tracks: list[Track] = []
        if self.is_platform_url(url) and not self.spotify_regex.match(url):
            res = await self._platform_search(url, 0, video, user)
            if isinstance(res, list):
                return res[:limit]
            return [res] if res else []

        sp = bool(self.spotify_regex.match(url))
        tracks = await self._playlist_tracks(
            url, limit, user, video, channel="Spotify" if sp else "YouTube"
        )
        if tracks or sp:
            return tracks

        # safety net for plain YouTube playlists
        try:
            plist = await Playlist.get(url)
            for data in plist.get("videos", [])[:limit]:
                thumbs = data.get("thumbnails") or [{}]
                tracks.append(
                    Track(
                        id=data.get("id"),
                        channel_name=(data.get("channel") or {}).get("name", ""),
                        duration=data.get("duration"),
                        duration_sec=utils.to_seconds(data.get("duration")) if data.get("duration") else 0,
                        title=str(data.get("title") or "Unknown Track")[:25],
                        thumbnail=((thumbs[-1] or {}).get("url") or "").split("?")[0] or None,
                        url=data.get("link").split("&list=")[0],
                        user=user,
                        view_count="",
                        video=video,
                    )
                )
        except Exception as e:
            logger.error(f"Playlist error: {e}")
        return tracks

    # ---------------- media: stream / download ----------------

    async def _url_is_playable(self, url: str, timeout: int = 10, tries: int = 1) -> bool:
        """Range-GET sanity check so the VC is never handed a dead link."""
        for _ in range(tries):
            try:
                session = await self._http()
                async with session.get(
                    url, headers={"Range": "bytes=0-1"}, timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    ctype = (resp.headers.get("Content-Type") or "").lower()
                    if resp.status in (200, 206) and not (ctype.startswith("text/") or "json" in ctype):
                        return True
                    if resp.status == 429:
                        return False
            except Exception:
                pass
        return False

    async def _fetch_file(self, url: str, path: str, params: dict | None = None, big: bool = False) -> str | None:
        """Downloads `url` to `path` (atomic via .part). Returns the path or None."""
        tmp = path + ".part"
        timeout = aiohttp.ClientTimeout(total=900 if big else 300, connect=15, sock_read=120)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as resp:
                    if resp.status not in (200, 206):
                        body = self._mask((await resp.text())[:150])
                        logger.warning(f"[Download] HTTP {resp.status}: {body}")
                        return None
                    ctype = (resp.headers.get("Content-Type") or "").lower()
                    if ctype.startswith("text/") or "json" in ctype:
                        body = self._mask((await resp.text())[:150])
                        logger.warning(f"[Download] got '{ctype}' instead of media: {body}")
                        return None
                    with open(tmp, "wb") as f:
                        async for chunk in resp.content.iter_chunked(131072):
                            f.write(chunk)
            if os.path.getsize(tmp) < MIN_FILE_SIZE:
                logger.warning(f"[Download] file too small, discarding: {Path(path).name}")
                return None
            os.replace(tmp, path)
            logger.info(f"[Download] saved {Path(path).name}")
            return path
        except Exception as e:
            logger.warning(f"[Download] failed for {Path(path).name}: {self._mask(e)}")
            return None
        finally:
            Path(tmp).unlink(missing_ok=True)

    @staticmethod
    def _cached(*paths: str) -> str | None:
        for p in paths:
            f = Path(p)
            if f.exists():
                if f.stat().st_size >= MIN_FILE_SIZE:
                    return p
                f.unlink(missing_ok=True)  # broken leftover
        return None

    async def _yt_media(self, vid: str, video: bool, local: bool) -> str | None:
        """YouTube id -> stream URL (fast) or local file."""
        if not self.api_key:
            logger.warning("[Stream] API key missing.")
            return None
        if video:
            path = f"{DOWNLOAD_DIR}/{vid}.mp4"
            if hit := self._cached(path):
                return hit
        else:
            path = f"{DOWNLOAD_DIR}/{vid}.mp3"
            if hit := self._cached(path, f"{DOWNLOAD_DIR}/{vid}.webm", f"{DOWNLOAD_DIR}/{vid}.ogg"):
                return hit

        params = {"query": vid, "dl_type": "video" if video else "audio", "api_key": self.api_key}
        if video:
            params["quality"] = self._quality()

        # fast join: hand a URL straight to the VC (the API supports Range/206).
        # Audio uses the API's bot-dedicated redirect endpoint.
        if not local and not (video and getattr(config, "VIDEO_DOWNLOAD", True)):
            if video:
                stream_url = f"{self.api_url}/download?{urlencode(params)}"
            else:
                stream_url = f"{self.api_url}/api/musicbot/play/{vid}?{urlencode({'api_key': self.api_key})}"
            if await self._url_is_playable(stream_url):
                logger.info(f"[Stream] streaming {vid} directly ({'video' if video else 'audio'}).")
                return stream_url
            logger.info(f"[Stream] stream check failed for {vid} — downloading a local copy.")

        return await self._fetch_file(f"{self.api_url}/download", path, params=params, big=video)

    def _abs(self, u) -> str | None:
        if not u:
            return None
        u = str(u)
        if u.startswith("/"):
            u = self.api_url + u
        if u.startswith(self.api_url) and "api_key=" not in u:
            u += ("&" if "?" in u else "?") + urlencode({"api_key": self.api_key})
        return u

    def _pick_platform_url(self, data: dict, video: bool) -> tuple[str | None, str]:
        """Best format url from an extractor response -> (url, ext)."""
        fmts = [f for f in (data.get("formats") or []) if isinstance(f, dict) and f.get("url")]

        def height(f):
            m = re.search(r"(\d{3,4})", str(f.get("quality") or ""))
            return int(m.group(1)) if m else 0

        pick = None
        if video:
            vids = [f for f in fmts if f.get("type") == "video" and f.get("has_audio", True)]
            want = self._quality()
            ok = [f for f in vids if 0 < height(f) <= want]
            if ok:
                pick = max(ok, key=height)
            elif vids:
                pick = min(vids, key=height)
        else:
            auds = [f for f in fmts if f.get("type") == "audio"]
            if auds:
                pick = max(auds, key=lambda f: f.get("bitrate") or 0)
            else:  # no audio-only format -> smallest muxed video (VC plays its audio)
                vids = [f for f in fmts if f.get("type") == "video" and f.get("has_audio", True)]
                if vids:
                    pick = min(vids, key=lambda f: height(f) or 9999)

        link = (pick or {}).get("url") or data.get("download_url")
        ext = str((pick or {}).get("ext") or ("mp4" if video else "m4a")).lstrip(".")
        return self._abs(link), ext

    async def _platform_media(self, url: str, video: bool, local: bool) -> str | None:
        data = await self._extract(url)
        if not data:
            return None
        link, ext = self._pick_platform_url(data, video)
        if not link:
            logger.warning(f"[Extract] no media url for {url}")
            return None

        name = hashlib.sha1(url.encode()).hexdigest()[:16] + ("_v" if video else "_a")
        path = f"{DOWNLOAD_DIR}/{name}.{ext}"
        if hit := self._cached(path):
            return hit

        if not local and not (video and getattr(config, "VIDEO_DOWNLOAD", True)):
            if await self._url_is_playable(link):
                logger.info(f"[Extract] streaming {data.get('platform', 'media')} directly.")
                return link
        return await self._fetch_file(link, path, big=video)

    async def _resolve(self, video_id: str, url: str, video: bool, local: bool) -> str | None:
        if self.is_platform_url(url) and not self._is_youtube(url):
            return await self._platform_media(url, video, local)
        vid = self._vid(url) or self._vid(video_id)
        if vid:
            return await self._yt_media(vid, video, local)
        if url.startswith("http"):  # unknown site -> let the extractor try
            return await self._platform_media(url, video, local)
        logger.warning(f"[Stream] cannot resolve {video_id}.")
        return None

    async def download(self, video_id: str, video: bool = False, _url: str | None = "") -> str | None:
        """Playable thing for `video_id`: a direct stream URL when possible
        (fast VC join), otherwise a local file."""
        if not video_id or len(video_id) < 3:
            return None
        url = _url or self.base + video_id
        res = await self._resolve(video_id, url, video, local=False)
        if not res:
            logger.warning(f"[Stream] API could not serve {video_id} ({'video' if video else 'audio'}).")
        return res

    async def download_local(self, video_id: str, url: str | None = "", video: bool = False) -> str | None:
        """Used when ffmpeg could not open a direct stream link: real local file."""
        url = url or self.base + video_id
        return await self._resolve(video_id, url, video, local=True)

    # ---------------- autoplay (same pattern as before) ----------------

    async def _mix_entries_youtubei(self, video_id: str, timeout: int = 10) -> list[dict]:
        """Fetches the YouTube mix (RD<videoId>) straight from the innertube
        `/next` endpoint, trying a few client profiles until one answers.
        Returns entries shaped like yt-dlp's (id/title/duration/channel/...)."""
        url = f"{YT_BASE}/youtubei/v1/next?key={YT_API_KEY}"
        deadline = asyncio.get_event_loop().time() + timeout

        for prof in YT_PROFILES:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break

            client = {
                "clientName": prof["name"],
                "clientVersion": prof["version"],
                "hl": "en",
                "gl": "US",
                **prof.get("extra", {}),
            }
            ctx = {"client": client}
            if prof.get("embed"):
                ctx["thirdParty"] = {"embedUrl": prof["embed"]}

            headers = {
                "Content-Type": "application/json",
                "User-Agent": prof["ua"],
                "Accept-Language": "en-US,en;q=0.9",
                "X-YouTube-Client-Name": prof["id"],
                "X-YouTube-Client-Version": prof["version"],
            }
            if prof.get("origin"):
                headers["Origin"] = prof["origin"]
                headers["Referer"] = prof["origin"] + "/"

            payload = {"context": ctx, "playlistId": f"RD{video_id}"}
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url, json=payload, headers=headers,
                        timeout=aiohttp.ClientTimeout(total=min(remaining, 6)),
                    ) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json(content_type=None)
            except Exception:
                continue

            try:
                contents = (
                    data["contents"]["twoColumnWatchNextResults"]["playlist"]["playlist"]["contents"]
                )
            except (KeyError, TypeError):
                continue

            entries = []
            for item in contents or []:
                r = (item or {}).get("playlistPanelVideoRenderer")
                if not r or not r.get("videoId"):
                    continue
                title = (r.get("title") or {}).get("simpleText") or ""
                if not title:
                    title = "".join(x.get("text", "") for x in (r.get("title") or {}).get("runs", []))
                byline = ((r.get("shortBylineText") or {}).get("runs") or [{}])[0].get("text")
                length = (r.get("lengthText") or {}).get("simpleText") or ""
                entries.append(
                    {
                        "id": r["videoId"],
                        "title": title or "Unknown",
                        "duration": self._yt_time_to_sec(length),
                        "channel": byline,
                        "thumbnails": (r.get("thumbnail") or {}).get("thumbnails") or [],
                    }
                )
            if entries:
                return entries

        return []

    async def _related_from_mix(
        self, video_id: str, played: set[str], channel_name: str | None = None
    ) -> Track | None:
        # the mix only exists for real YouTube ids
        if not _BARE_ID_RE.match(video_id or ""):
            return None

        # innertube /next (no extra API quota used)
        entries = await self._mix_entries_youtubei(video_id)

        # Take the YouTube mix ("RD"+videoId), drop the current song and
        # everything already played, then pick one of the rest at random.
        candidates: list[Track] = []
        seen: set[str] = set()
        for entry in entries:
            if not entry:
                continue

            eid = entry.get("id")
            if not eid or eid in played or eid in seen:
                continue

            title = entry.get("title") or "Unknown"
            if title.lower() in ("[deleted video]", "[private video]"):
                continue

            duration = int(entry.get("duration") or 0)
            if duration <= 0 or duration > config.DURATION_LIMIT:
                continue

            seen.add(eid)
            thumbs = entry.get("thumbnails") or []
            thumbnail = thumbs[-1]["url"].split("?")[0] if thumbs else self._yt_thumb(eid)

            candidates.append(
                Track(
                    id=eid,
                    channel_name=entry.get("channel") or entry.get("uploader") or "YouTube",
                    duration=self._format_duration(duration),
                    duration_sec=duration,
                    title=title[:25],
                    thumbnail=thumbnail,
                    url=f"https://www.youtube.com/watch?v={eid}",
                    view_count=self._format_views(entry.get("view_count")),
                    video=False,
                )
            )

        if not candidates:
            return None
        return random.choice(candidates)

    async def _related_from_search(self, current: Track, played: set[str]) -> Track | None:
        current_channel = (current.channel_name or "").strip().lower()

        queries = []
        if current.channel_name:
            queries.append(f"{current.channel_name}")
        if current.title:
            queries.append(f"{current.title}")

        fallback: Track | None = None

        for query in queries:
            try:
                items = await self._search_items(query, 8)
            except Exception as e:
                logger.error(f"[Autoplay] Search fallback failed for {query!r}: {e}")
                continue

            for it in items:
                if it["id"] in played:
                    continue
                if not it["duration_sec"] or it["duration_sec"] > config.DURATION_LIMIT:
                    continue

                track = self._track_from_item(it, 0, False)
                if current_channel and track.channel_name.strip().lower() == current_channel:
                    return track
                if fallback is None:
                    fallback = track

        return fallback

    async def get_related(self, current: Track, played: list[str] | None = None) -> Track | None:
        if not current or not current.id:
            return None

        played = set(played or [])
        played.add(current.id)

        # keep the session's mode: if the current track is a vplay video,
        # the autoplayed song is played as video too.
        want_video = bool(getattr(current, "video", False)) and config.VIDEO_PLAY

        related = await self._related_from_mix(current.id, played, channel_name=current.channel_name)
        if related:
            related.video = want_video
            return related

        logger.info(f"[Autoplay] Mix returned nothing for {current.id}, trying search fallback.")
        related = await self._related_from_search(current, played)
        if related:
            related.video = want_video
            return related

        logger.warning(f"[Autoplay] No related track found for {current.id}.")
        return None
