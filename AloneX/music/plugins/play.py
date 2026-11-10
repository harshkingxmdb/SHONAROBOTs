# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic
#ALONE-CODER

import asyncio
import hashlib
import json
import shutil
from pathlib import Path
from urllib.parse import unquote

from pyrogram import filters, types

from AloneX.music import anon, app, config, db, queue, tg, yt
from AloneX.music.helpers import Track, buttons, thumb, utils
from AloneX.music.helpers._play import checkUB
from AloneX.music.plugins.playlist import load_playlist_tracks, parse_playlist_id


PLAYLIST_NOTICE_DELETE_AFTER = 3  # seconds


async def send_playlist_notice(chat_id: int, text: str) -> None:
    """Sends the "Added N tracks to queue" message and removes it again after
    a few seconds so it doesn't clutter the group."""
    msg = await app.send_message(chat_id=chat_id, text=text)
    asyncio.create_task(
        anon._delete_later(chat_id, msg.id, delay=PLAYLIST_NOTICE_DELETE_AFTER)
    )


async def _probe_direct(url: str) -> tuple[int, bool] | None:
    """Asks ffprobe about a direct media link.
    Returns (duration_in_seconds [0 = unknown/live], has_video) or None if the
    link is not playable media."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return (0, True)  # can't check — just try to play it
    proc = await asyncio.create_subprocess_exec(
        ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type",
        "-of", "json", url,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=40)
    except asyncio.TimeoutError:
        proc.kill()
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(out or b"{}")
    except ValueError:
        return None
    streams = [s.get("codec_type") for s in data.get("streams", [])]
    if not streams:
        return None
    try:
        duration = int(float((data.get("format") or {}).get("duration") or 0))
    except (TypeError, ValueError):
        duration = 0
    return duration, "video" in streams


async def direct_track(url: str, want_video: bool, mention: str) -> Track | None:
    """Builds a Track for a direct mp4/mkv/m3u8/... link. It is streamed straight
    from the link by ffmpeg — nothing is downloaded, so long movies work."""
    probe = await _probe_direct(url)
    if not probe:
        return None
    duration, has_video = probe
    name = unquote(url.split("?")[0].rstrip("/").split("/")[-1]) or "Direct stream"
    return Track(
        id=hashlib.md5(url.encode()).hexdigest()[:11],
        channel_name="Direct link",
        duration=yt._format_duration(duration) if duration else "LIVE",
        duration_sec=duration,
        title=name[:25],
        url=url,
        file_path=url,
        thumbnail=config.DEFAULT_THUMB,
        user=mention,
        view_count="",
        video=bool(want_video and has_video),
    )


def playlist_to_queue(chat_id: int, tracks: list) -> str:
    text = "<blockquote expandable>"
    for track in tracks:
        pos = queue.add(chat_id, track)
        text += f"<b>{pos}.</b> {track.title}\n"
    text = text[:1948] + "</blockquote>"
    return text

@app.on_message(
    filters.command(["play", "playforce", "vplay", "vplayforce", "cplay", "cplayforce", "cvplay", "cvplayforce"])
    & (filters.group | filters.channel | filters.private)
    & ~app.bl_users
)
@checkUB
async def play_hndlr(
    _,
    m: types.Message,
    force: bool = False,
    m3u8: bool = False,
    video: bool = False,
    url: str = None,
    target_chat_id: int = None,
) -> None:
    chat_id = target_chat_id if target_chat_id is not None else m.chat.id

    sent = await m.reply_text(m.lang["play_searching"])
    file = None
    mention = m.from_user.mention if m.from_user else m.chat.title
    media = tg.get_media(m.reply_to_message) if m.reply_to_message else None
    tracks = []

    if url:
        if m3u8:
            # not a YouTube/Spotify/... link -> treat it as a direct media link
            await sent.edit_text("<blockquote>🔎 Checking the link...</blockquote>")
            file = await direct_track(url, video, mention)
            if not file:
                return await sent.edit_text(
                    "<blockquote>This link is not a playable audio/video stream.</blockquote>"
                )
            file.message_id = sent.id
        elif "playlist" in url:
            await sent.edit_text(m.lang["playlist_fetch"])
            tracks = await yt.playlist(
                config.PLAYLIST_LIMIT, mention, url, video
            )

            if not tracks:
                return await sent.edit_text(m.lang["playlist_error"])

            file = tracks[0]
            tracks.remove(file)
            file.message_id = sent.id
        else:
            file = await yt.search(url, sent.id, video=video)
            # album/playlist link: search() returns a list -> first track plays now, rest are queued
            if isinstance(file, list):
                tracks = file
                file = tracks.pop(0) if tracks else None

        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )

    elif len(m.command) >= 2:
        query = " ".join(m.command[1:])
        pl_id = next(
            (p for p in map(parse_playlist_id, m.command[1:]) if p), None
        )
        if pl_id:
            # /play playlist-<ID>  -> stream the user's saved playlist
            await sent.edit_text("<blockquote>🎶 Loading playlist...</blockquote>")
            pl, tracks = await load_playlist_tracks(pl_id, mention, m.chat.id, video)
            if pl is None:
                return await sent.edit_text("<blockquote>Playlist not found. Please check the playlist ID.</blockquote>")
            if not tracks:
                return await sent.edit_text(
                    "<blockquote>This playlist is empty. Add songs with /addtoplaylist.</blockquote>"
                )
            room = config.QUEUE_LIMIT - len(queue.get_queue(chat_id))
            tracks = tracks[: max(room, 1)]
            file = tracks.pop(0)
            file.message_id = sent.id
        else:
            file = await yt.search(query, sent.id, video=video)
            if isinstance(file, list):
                tracks = file
                file = tracks.pop(0) if tracks else None
            if not file:
                return await sent.edit_text(
                    m.lang["play_not_found"].format(config.SUPPORT_CHAT)
                )

    elif media:
        setattr(sent, "lang", m.lang)
        file = await tg.download(m.reply_to_message, sent)

    if not file:
        return await sent.edit_text(m.lang["play_usage"])

    # The "Now Playing"/status message always lives in the chat where the
    # command was sent (m.chat) — which can differ from `chat_id` (the
    # actual playback target) for /cplay used from a linked group or DM.
    file.message_chat_id = m.chat.id

    if file.duration_sec > config.DURATION_LIMIT:
        return await sent.edit_text(
            m.lang["play_duration_limit"].format(config.DURATION_LIMIT // 60)
        )

    if await db.is_logger():
        await utils.play_log(m, file.title, file.duration)

    file.user = mention
    if force:
        queue.force_add(chat_id, file)
    else:
        position = queue.add(chat_id, file)

        if position != 0 or await db.get_call(chat_id):
            play_type = (
                m.lang.get("play_type_video", "🎥 Video")
                if file.video
                else m.lang.get("play_type_audio", "🎵 Audio")
            )
            _thumb = (
                await thumb.generate(file)
                if isinstance(file, Track)
                else config.DEFAULT_THUMB
            )
            await sent.edit_media(
                media=types.InputMediaPhoto(
                    media=_thumb,
                    caption=m.lang["play_queued"].format(
                        position,
                        file.url,
                        file.title,
                        file.duration,
                        mention,
                        play_type,
                    ),
                ),
                reply_markup=buttons.play_queued(
                    chat_id, file.id, m.lang["play_now"], _lang=m.lang
                ),
            )
            if tracks:
                added = playlist_to_queue(chat_id, tracks)
                await send_playlist_notice(
                    m.chat.id,
                    m.lang["playlist_queued"].format(len(tracks)) + added,
                )
            return

    if not file.file_path:
        fname = f"downloads/{file.id}.{'mp4' if video else 'webm'}"
        if Path(fname).exists():
            file.file_path = fname
        else:
            await sent.edit_text(m.lang["play_downloading"])
            file.file_path = await yt.download(file.id, video=video, _url=file.url)

    await anon.play_media(chat_id=chat_id, message=sent, media=file)
    if not tracks:
        return
    added = playlist_to_queue(chat_id, tracks)
    await send_playlist_notice(
        m.chat.id,
        m.lang["playlist_queued"].format(len(tracks)) + added,
    )

