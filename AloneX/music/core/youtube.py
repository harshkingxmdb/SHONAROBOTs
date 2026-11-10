# Copyright (c) 2025 @THECDERQUEEN
# Licensed under the MIT License.
# This file is part of @SHONA_BOTS
#SHONA-DECODER

import asyncio
import os
import random
import re
import time
from pathlib import Path
from urllib.parse import urlencode

import aiohttp
from py_yt import Playlist, VideosSearch

from AloneX.music import app, config, logger
from AloneX.music.core._api import FallenApi
from AloneX.music.helpers import Track, utils

DOWNLOAD_DIR = "downloads"

MIN_FILE_SIZE = 100000  # bytes; smaller than this is treated as a failed download

# YouTube innertube (same endpoint the YouTube site itself uses) — used to
# fetch the "mix" (RD<videoId>) for autoplay without going through yt-dlp.
YT_BASE = "https://www.youtube.com"
YT_API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
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


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
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

        self.api_patterns = {
            "apple": re.compile(
                r"(?i)^https?://music\.apple\.com/[a-zA-Z-]+/(?:song/(?:[^/]+/)?\d+|album/[^/]+/\d+(?:\?i=\d+)?|playlist/[^/]+/pl\.[\w.-]+|artist/[^/]+/\d+)(?:\?.*)?$"
            ),
            "spotify": re.compile(
                r"(?i)^(https?://)?([a-z0-9-]+\.)*spotify\.com/(track|playlist|album|artist)/[a-zA-Z0-9]+(\?.*)?$"
            ),
            "jiosaavn": re.compile(
                r"(?i)https?://(?:www\.)?(?:jiosaavn|saavn)\.com/(?:s/)?(song|album|playlist|featured)(?:/[^/]+)*/([A-Za-z0-9_,-]+)(?:/)?(?:\?.*)?$"
            ),
            "deezer": re.compile(
                r"(?i)https?://(?:www\.)?deezer\.com/(?:[a-z]{2}/)?(track|album|playlist)/(\d+)"
            ),
            "soundcloud": re.compile(
                r"(?i)^(https?://)?(www\.)?soundcloud\.com/[a-zA-Z0-9_-]+/(sets/)?[a-zA-Z0-9._-]+(\?.*)?$"
            ),
            "gaana": re.compile(
                r"(?i)https?://(?:www\.)?gaana\.com/(song|album|playlist|artist)/([A-Za-z0-9\-]+)"
            ),
            "tidal": re.compile(
                r"(?i)https?://(?:www\.|listen\.)?tidal\.com/(?:browse/)?(track|album|playlist)/([a-zA-Z0-9-]+)(?:[/?].*)?$"
            ),
            "mxplayer": re.compile(
                r"(?i)https?://(?:www\.)?mxplayer\.in/(?:show|movie)/.*"
            ),
            "twitch": re.compile(
                r"(?i)https?://(?:www\.|m\.)?twitch\.tv/(?:videos|[\w._-]+/video)/\d+"
            ),
            "twitch_clip": re.compile(
                r"(?i)https?://(?:www\.|m\.)?(?:twitch\.tv/clip/[\w-]+|clips\.twitch\.tv/[\w-]+|twitch\.tv/[\w-]+/clip/[\w-]+)"
            ),
            "kick": re.compile(
                r"(?i)https?://(?:www\.)?kick\.com/[\w._-]+/videos/[a-fA-F0-9-]+"
            ),
            "kick_clip": re.compile(
                r"(?i)https?://(?:www\.)?kick\.com/[\w._-]+/clips/[\w-]+"
            ),
        }

        self.fallen = FallenApi(app)
        self.inflex_url = (getattr(config, "INFLEX_API_URL", "") or "https://teaminflex.xyz").rstrip("/")
        self.inflex_key = (getattr(config, "INFLEX_API_KEY", "") or "").strip()
        if not self.inflex_key:
            logger.warning("[Inflex] INFLEX_API_KEY is not set — music fallback API is disabled.")

        self.shruti_url = (getattr(config, "SHRUTI_API_URL", "") or "https://api.shrutibots.in").rstrip("/")
        key = (getattr(config, "SHRUTI_API_KEY", "") or "").strip()
        self.shruti_key = "" if key == "YOUR_API_KEY" else key
        if not self.shruti_key:
            logger.warning("[Shruti] SHRUTI_API_KEY is not set — /vplay is disabled.")
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    def is_platform_url(self, url: str) -> bool:
        return any(pattern.search(url) for pattern in self.api_patterns.values())

    def valid(self, url: str) -> bool:
        if bool(re.match(self.regex, url)):
            return True
        return self.is_platform_url(url)

    def invalid(self, url: str) -> bool:
        if self.valid(url):
            return False
        return bool(re.match(self.iregex, url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | list[Track] | None:
        if self.is_platform_url(query) and config.API_KEY and config.API_URL:
            tracks = await self.fallen.get_info(query)
            if tracks:
                if len(tracks) > 1:
                    res_tracks = []
                    for track_info in tracks[:config.PLAYLIST_LIMIT]:
                        dur_sec = track_info.duration or 0
                        res_tracks.append(
                            Track(
                                id=track_info.id,
                                channel_name=track_info.channel or track_info.platform or "Fallen API",
                                duration=self._format_duration(dur_sec),
                                duration_sec=dur_sec,
                                message_id=m_id,
                                title=(track_info.title or "Unknown Track")[:25],
                                thumbnail=track_info.thumbnail or config.DEFAULT_THUMB,
                                url=track_info.url or query,
                                view_count=track_info.views or "",
                                video=video,
                            )
                        )
                    return res_tracks

                track_info = tracks[0]
                dur_sec = track_info.duration or 0
                return Track(
                    id=track_info.id,
                    channel_name=track_info.channel or track_info.platform or "Fallen API",
                    duration=self._format_duration(dur_sec),
                    duration_sec=dur_sec,
                    message_id=m_id,
                    title=(track_info.title or "Unknown Track")[:25],
                    thumbnail=track_info.thumbnail or config.DEFAULT_THUMB,
                    url=track_info.url or query,
                    view_count=track_info.views or "",
                    video=video,
                )

        try:
            _search = VideosSearch(query, limit=1, with_live=False)
            results = await _search.next()
        except Exception as e:
            logger.error(f"Search error: {e}")
            results = None

        if results and results.get("result"):
            data = results["result"][0]
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")) if data.get("duration") else 0,
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )

        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track]:
        tracks = []
        if self.is_platform_url(url) and config.API_KEY and config.API_URL:
            api_tracks = await self.fallen.get_info(url)
            for data in (api_tracks or [])[:limit]:
                dur_sec = data.duration or 0
                track = Track(
                    id=data.id,
                    channel_name=data.channel or data.platform or "",
                    duration=self._format_duration(dur_sec),
                    duration_sec=dur_sec,
                    title=(data.title or "Unknown Track")[:25],
                    thumbnail=data.thumbnail or config.DEFAULT_THUMB,
                    url=data.url or url,
                    user=user,
                    view_count=data.views or "",
                    video=video,
                )
                tracks.append(track)
            if tracks:
                return tracks

        try:
            plist = await Playlist.get(url)
            for data in plist.get("videos", [])[:limit]:
                track = Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")) if data.get("duration") else 0,
                    title=data.get("title")[:25],
                    thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                    url=data.get("link").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                tracks.append(track)
        except Exception as e:
            logger.error(f"Playlist error: {e}")
        return tracks

    # ---------------- fast path: direct streaming (no download) ----------------

    async def _url_is_playable(self, url: str, timeout: int = 6) -> bool:
        """Quick sanity check that a stream URL actually responds, so we
        never hand the assistant a dead link — a HEAD/range GET is a lot
        cheaper than downloading the whole file just to find out."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Range": "bytes=0-1"}
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    return resp.status in (200, 206)
        except Exception:
            return False

    # ---------------- Inflex API (music fallback, audio only) ----------------

    async def _inflex_download(self, link: str, force_download: bool = False) -> str | None:
        """Audio (.webm) through the Inflex API. Returns a stream URL / local path,
        or None on any failure so the caller can fall through."""
        m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})", link or "")
        if not m or not self.inflex_key:
            return None  # not a YouTube link (e.g. Spotify) — this API can't help
        # Inflex keeps timing out -> stop waiting on it for a while
        if time.monotonic() < getattr(self, "_inflex_skip_until", 0.0):
            return None
        vid = m.group(1)

        file_path = f"{DOWNLOAD_DIR}/{vid}.webm"
        tmp_path = file_path + ".part"
        if Path(file_path).exists():
            if Path(file_path).stat().st_size >= MIN_FILE_SIZE:
                return file_path
            Path(file_path).unlink(missing_ok=True)  # broken leftover

        headers = {"Content-Type": "application/json", "X-API-KEY": self.inflex_key}
        payload = {"url": vid, "type": "audio"}
        timeout = aiohttp.ClientTimeout(total=150, connect=10, sock_read=90)
        post_timeout = aiohttp.ClientTimeout(total=180, connect=10)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.inflex_url}/download", json=payload, headers=headers, timeout=post_timeout
                ) as resp:
                    data = await resp.json(content_type=None)
                    if resp.status != 200 or not isinstance(data, dict):
                        logger.warning(f"[Inflex] HTTP {resp.status} -> {data}")
                        return None
                    self._inflex_fails = 0  # the API answered -> it is up
                    # The API answers with a `stream_url` (newer) or a `download_url` (older).
                    raw_link = data.get("stream_url") or data.get("download_url")
                    if data.get("status") != "success" or not raw_link:
                        logger.warning(f"[Inflex] bad response: {data}")
                        return None
                    raw_link = str(raw_link)
                    download_link = raw_link if raw_link.startswith("http") else f"{self.inflex_url}{raw_link}"

                    # Prefer playing straight from the stream URL (fast VC join).
                    if data.get("stream_url") and not force_download:
                        for _ in range(2):
                            if await self._url_is_playable(download_link, timeout=4):
                                logger.info(f"[Inflex] streaming {vid} directly.")
                                return download_link

                async with session.get(download_link) as file_resp:
                    if file_resp.status != 200:
                        logger.warning(f"[Inflex] file download failed ({file_resp.status}) for {vid}")
                        return None
                    ctype = (file_resp.headers.get("Content-Type") or "").lower()
                    if ctype.startswith("text/") or "json" in ctype:
                        logger.warning(f"[Inflex] got '{ctype}' instead of media for {vid}")
                        return None
                    with open(tmp_path, "wb") as f:
                        async for chunk in file_resp.content.iter_chunked(65536):
                            f.write(chunk)

            if os.path.getsize(tmp_path) < MIN_FILE_SIZE:
                logger.warning(f"[Inflex] file too small for {vid}, discarding.")
                return None

            os.replace(tmp_path, file_path)
            logger.info(f"[Inflex] downloaded {vid}")
            return file_path
        except Exception as e:
            logger.warning(f"[Inflex] exception for {vid}: {e}")
            self._inflex_fails = getattr(self, "_inflex_fails", 0) + 1
            if self._inflex_fails >= 3:
                self._inflex_skip_until = time.monotonic() + 300
                self._inflex_fails = 0
                logger.warning("[Inflex] 3 failures in a row — skipping Inflex for 5 min.")
            return None
        finally:
            Path(tmp_path).unlink(missing_ok=True)  # no-op after a successful os.replace

    # ---------------- Shruti API (/vplay, video only) ----------------

    async def _shruti_download(self, link: str, force_download: bool = False) -> str | None:
        """Video (.mp4) through the Shruti API:
        GET {url}/download?url=<id>&type=video&api_key=<key> answers with the media bytes.
        Returns a local path (or, when config.VIDEO_DOWNLOAD is False, the stream URL)."""
        m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})", link or "")
        if not m or not self.shruti_key:
            return None
        if time.monotonic() < getattr(self, "_shruti_skip_until", 0.0):
            return None
        vid = m.group(1)
        params = {"url": vid, "type": "video", "api_key": self.shruti_key}

        # Fast-join mode: hand the URL straight to the VC (no download).
        if not force_download and not getattr(config, "VIDEO_DOWNLOAD", True):
            logger.info(f"[Shruti] streaming {vid} directly.")
            return f"{self.shruti_url}/download?{urlencode(params)}"

        file_path = f"{DOWNLOAD_DIR}/{vid}.mp4"
        tmp_path = file_path + ".part"
        if Path(file_path).exists():
            if Path(file_path).stat().st_size >= MIN_FILE_SIZE:
                return file_path
            Path(file_path).unlink(missing_ok=True)  # broken leftover

        timeout = aiohttp.ClientTimeout(total=900, connect=10, sock_read=120)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.shruti_url}/download", params=params) as resp:
                    if resp.status != 200:
                        body = (await resp.text())[:150].replace(self.shruti_key, "***")
                        logger.warning(f"[Shruti] HTTP {resp.status} for {vid}: {body}")
                        return None
                    ctype = (resp.headers.get("Content-Type") or "").lower()
                    if ctype.startswith("text/") or "json" in ctype:
                        body = (await resp.text())[:150].replace(self.shruti_key, "***")
                        logger.warning(f"[Shruti] got '{ctype}' instead of media for {vid}: {body}")
                        return None
                    with open(tmp_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(131072):
                            f.write(chunk)

            if os.path.getsize(tmp_path) < MIN_FILE_SIZE:
                logger.warning(f"[Shruti] file too small for {vid}, discarding.")
                return None

            os.replace(tmp_path, file_path)
            self._shruti_fails = 0
            logger.info(f"[Shruti] downloaded {vid}")
            return file_path
        except Exception as e:
            logger.warning(f"[Shruti] exception for {vid}: {str(e).replace(self.shruti_key, '***')}")
            self._shruti_fails = getattr(self, "_shruti_fails", 0) + 1
            if self._shruti_fails >= 3:
                self._shruti_skip_until = time.monotonic() + 300
                self._shruti_fails = 0
                logger.warning("[Shruti] 3 failures in a row — skipping Shruti for 5 min.")
            return None
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @staticmethod
    def _is_youtube(url: str) -> bool:
        """True for YouTube watch/short/youtu.be links or a bare 11-char video id."""
        return bool(re.search(r"youtu(?:\.be|be\.com)|^[A-Za-z0-9_-]{11}$", (url or "").strip()))

    async def download(self, video_id: str, video: bool = False, _url: str | None = "") -> str | None:
        """Resolves something playable for `video_id` — a direct stream URL
        wherever possible, so the assistant can join the VC immediately
        instead of waiting for a full file to download first. Only falls
        back to an actual local download if nothing streamable could be
        resolved at all."""
        if not video_id or len(video_id) < 3:
            return None

        url = _url or self.base + video_id

        # Routing:
        #   audio (/play):  main API -> Inflex (YouTube only; when the main API
        #                   fails / its limit is over)
        #   video (/vplay): Shruti API (YouTube only)
        is_yt = self._is_youtube(url)

        if video:
            if is_yt and self.shruti_key:
                if path := await self._shruti_download(url):
                    return path
        else:
            if config.API_KEY and config.API_URL:
                if path := await self.fallen.download_track(url):
                    return path
            if is_yt and self.inflex_key:
                logger.info(f"[Stream] Main API failed for {video_id} — trying Inflex.")
                if path := await self._inflex_download(url):
                    return path

        logger.warning(f"[Stream] No API could serve {video_id} ({'video' if video else 'audio'}).")
        return None

    async def download_local(self, video_id: str, url: str | None = "", video: bool = False) -> str | None:
        """Used when ffmpeg could not open a direct stream link: get a real
        local file from the APIs instead."""
        url = url or self.base + video_id
        if video:
            return await self._shruti_download(url, force_download=True)
        if self._is_youtube(url) and self.inflex_key:
            if path := await self._inflex_download(url, force_download=True):
                return path
        if config.API_KEY and config.API_URL:
            return await self.fallen.download_track(url)
        return None

    async def close(self):
        await self.fallen.close()

    def _format_duration(self, seconds: int) -> str:
        seconds = max(int(seconds or 0), 0)
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    def _format_views(self, count) -> str:
        if not count:
            return ""
        count = int(count)
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
        # innertube /next (no yt-dlp needed)
        entries = await self._mix_entries_youtubei(video_id)


        # Same idea as the Go bot: take the YouTube mix ("RD"+videoId),
        # drop the current song and everything already played, then pick
        # one of the remaining candidates at random.
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
            thumbnail = thumbs[-1]["url"].split("?")[0] if thumbs else None

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

    async def _related_from_search(
        self, current: Track, played: set[str]
    ) -> Track | None:
        current_channel = (current.channel_name or "").strip().lower()

        queries = []
        if current.channel_name:
            queries.append(f"{current.channel_name}")
        if current.title:
            queries.append(f"{current.title}")

        fallback: Track | None = None

        for query in queries:
            try:
                _search = VideosSearch(query, limit=8)
                results = await _search.next()
            except Exception as e:
                logger.error(f"[Autoplay] Search fallback failed for {query!r}: {e}")
                continue

            for data in (results or {}).get("result", []):
                eid = data.get("id")
                if not eid or eid in played:
                    continue

                title = data.get("title") or "Unknown"
                duration_str = data.get("duration")
                duration_sec = utils.to_seconds(duration_str) if duration_str else 0
                if not duration_sec or duration_sec > config.DURATION_LIMIT:
                    continue

                track = Track(
                    id=eid,
                    channel_name=data.get("channel", {}).get("name") or "YouTube",
                    duration=duration_str,
                    duration_sec=duration_sec,
                    title=title[:25],
                    thumbnail=(data.get("thumbnails", [{}])[-1].get("url") or "").split("?")[0] or None,
                    url=data.get("link"),
                    view_count=data.get("viewCount", {}).get("short"),
                    video=False,
                )

                result_channel = track.channel_name.strip().lower()
                if current_channel and result_channel == current_channel:
                    return track
                if fallback is None:
                    fallback = track

        return fallback

    async def get_related(
        self, current: Track, played: list[str] | None = None
    ) -> Track | None:
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

        logger.info(
            f"[Autoplay] Mix returned nothing for {current.id}, trying search fallback."
        )
        related = await self._related_from_search(current, played)
        if related:
            related.video = want_video
            return related

        logger.warning(f"[Autoplay] No related track found for {current.id}.")
        return None
