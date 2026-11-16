# Copyright (c) 2025 @THECDERQUEEN
# Licensed under the MIT License.
# This file is part of @SHONA_BOTS
#SHONA-DECODER

import asyncio
import os
from collections import defaultdict

from ntgcalls import (ConnectionNotFound, TelegramServerError,
                      RTMPStreamingUnsupported, ConnectionError,
                      TransportParseException)
from pyrogram.errors import (ChatSendMediaForbidden, ChatSendPhotosForbidden,
                             MessageIdInvalid)
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

from AloneX.music import app, config, db, lang, logger, queue, userbot, yt
from AloneX.music.helpers import Media, Track, buttons, thumb, vclogger

import json
import shutil
import subprocess


def _patch_pytgcalls_probe() -> None:
    """pytgcalls runs `ffprobe` on every stream before playing it and crashes with JSONDecodeError /
    ProcessLookupError when ffprobe prints nothing (seen on Heroku, even for local files). That check
    only validates the stream (its result is not used), so when it breaks we skip it and let ffmpeg
    try to play the file anyway."""
    safe_errors = (json.JSONDecodeError, ProcessLookupError, asyncio.TimeoutError, OSError)
    patched = []
    for mod_name in ("pytgcalls.types.stream.media_stream", "pytgcalls.ffmpeg"):
        try:
            module = __import__(mod_name, fromlist=["check_stream"])
            original = getattr(module, "check_stream", None)
            if original is None or getattr(original, "_music_safe", False):
                continue

            async def _safe_check(*args, __orig=original, **kwargs):
                try:
                    return await __orig(*args, **kwargs)
                except safe_errors as e:
                    # if the probed thing is a local file, record why ffprobe could not read it
                    cand = next(
                        (v for v in [*args, *kwargs.values()] if isinstance(v, str) and os.path.exists(v)),
                        None,
                    )
                    extra = f" || DIAG: {await _diagnose_media(cand)}" if cand else ""
                    logger.warning(f"[Probe] ffprobe check skipped ({type(e).__name__}: {e}).{extra}")
                    return None

            _safe_check._music_safe = True
            setattr(module, "check_stream", _safe_check)
            patched.append(mod_name.rsplit(".", 1)[-1])
        except Exception as e:  # never break startup because of this
            logger.warning(f"[Probe] could not patch {mod_name}: {type(e).__name__}: {e}")
    if patched:
        logger.info(f"[Probe] tolerant ffprobe check enabled ({', '.join(patched)}).")


def _log_ffmpeg_health() -> None:
    """One line at startup that tells whether ffmpeg / ffprobe really run on this server."""
    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        if not path:
            logger.error(f"[FFmpeg] {tool} NOT FOUND in PATH - music cannot play without it.")
            continue
        try:
            r = subprocess.run([tool, "-version"], capture_output=True, text=True, timeout=10)
            first = (r.stdout or r.stderr).splitlines()[0] if (r.stdout or r.stderr) else ""
            if r.returncode == 0:
                logger.info(f"[FFmpeg] {tool} OK: {first[:90]}")
            else:
                logger.error(f"[FFmpeg] {tool} FAILED (code {r.returncode}): {(r.stderr or r.stdout)[:200]}")
        except Exception as e:
            logger.error(f"[FFmpeg] {tool} could not run: {type(e).__name__}: {e}")


async def _diagnose_media(path: str) -> str:
    """Why can't this file be played? size, first bytes and what ffprobe itself says."""
    info = []
    try:
        if os.path.exists(path):
            with open(path, "rb") as f:
                head = f.read(16)
            info.append(f"size={os.path.getsize(path)} head={head!r}")
        else:
            info.append("file does not exist")
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-show_entries", "format=format_name,duration",
            "-of", "default=nw=1", path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=15)
        except asyncio.TimeoutError:
            proc.kill()
            info.append("ffprobe=timeout")
        else:
            info.append(
                f"ffprobe rc={proc.returncode} out={out.decode(errors='ignore').strip()[:100]!r} "
                f"err={err.decode(errors='ignore').strip()[:200]!r}"
            )
    except Exception as e:
        info.append(f"diagnose failed: {type(e).__name__}: {e}")
    return " | ".join(info)


_patch_pytgcalls_probe()
_log_ffmpeg_health()


class TgCall(PyTgCalls):
    def __init__(self):
        self.clients = []
        self.history: dict[int, list[str]] = defaultdict(list)
        self.pending_autoplay: dict[int, Track] = {}
        self.autoplay_prefetching: set[int] = set()
        # chat_id -> was the stream we last started a video (True) or audio (False)?
        self.call_video: dict[int, bool] = {}

    async def pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=True)
        try:
            return await client.pause(chat_id)
        except (ConnectionNotFound, exceptions.NotInCallError):
            await self.stop(chat_id)

    async def resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=False)
        try:
            return await client.resume(chat_id)
        except (ConnectionNotFound, exceptions.NotInCallError):
            await self.stop(chat_id)

    async def stop(self, chat_id: int) -> None:
        client = await db.get_assistant(chat_id)
        try:
            queue.clear(chat_id)
            await db.remove_call(chat_id)
            await db.set_loop(chat_id, 0)
        except:
            pass

        self.history.pop(chat_id, None)
        self.pending_autoplay.pop(chat_id, None)
        self.autoplay_prefetching.discard(chat_id)
        self.call_video.pop(chat_id, None)
        vclogger.clear_chat(chat_id)

        try:
            await client.leave_call(chat_id, close=False)
        except Exception as e:
            logger.warning(f"[Stop] leave_call failed for {chat_id}: {e}")


    async def play_media(
        self,
        chat_id: int,
        message: Message,
        media: Media | Track,
        seek_time: int = 0,
    ) -> None:
        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang(chat_id)
        show_thumb = await db.get_thumb(chat_id)

        if not media.file_path:
            # The background prefetch may not have finished (or failed) by the
            # time this song starts. Try ONE direct fetch now instead of skipping
            # the song silently — that skip is what made queued songs "not play".
            try:
                await message.edit_text(_lang["play_downloading"])
            except Exception:
                pass
            try:
                media.file_path = await yt.download(
                    media.id, video=media.video, _url=media.url
                )
            except Exception as e:
                logger.error(f"[Play] direct fetch failed for {media.id}: {e}")
                media.file_path = None

        if not media.file_path:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            # If the song the user asked for failed to download and nothing
            # else is queued, stop here — don't let Autoplay start some
            # unrelated "random" song in its place.
            if getattr(media, "user", None) != "Autoplay" and not queue.get_next(
                chat_id, check=True
            ):
                return await self.stop(chat_id)
            return await self.play_next(chat_id)

        def _pick_quality(enum_cls, wanted, default):
            # case-insensitive: "hd_720p", "HD_720p", "STUDIO" all work
            wanted = str(wanted).strip().lower()
            for name in dir(enum_cls):
                if name.lower() == wanted and not name.startswith("_"):
                    return getattr(enum_cls, name)
            return default

        def _ffmpeg_args(path: str) -> str | None:
            # Direct links: auto-reconnect when the connection drops mid-song
            # (this is what causes stutter/lag). Local files need none of it.
            args = []
            if str(path).startswith("http"):
                args += ["-reconnect 1", "-reconnect_streamed 1", "-reconnect_delay_max 5"]
            if seek_time > 1:
                args.append(f"-ss {seek_time}")
            return " ".join(args) or None

        def _build_stream(path: str, probe: bool = True):
            kwargs = dict(
                media_path=path,
                # config.py -> AUDIO_QUALITY: HIGH (48kHz stereo) or STUDIO (96kHz)
                audio_parameters=_pick_quality(
                    types.AudioQuality, getattr(config, "AUDIO_QUALITY", "HIGH"), types.AudioQuality.HIGH
                ),
                video_parameters=_pick_quality(
                    types.VideoQuality, getattr(config, "VIDEO_QUALITY", "HD_720p"), types.VideoQuality.HD_720p
                ),
                audio_flags=types.MediaStream.Flags.REQUIRED,
                # AUTO_DETECT makes pytgcalls run ffprobe on the link first. When that probe dies or
                # times out (ProcessLookupError) we retry with probe=False -> no ffprobe at all.
                video_flags=(
                    (
                        types.MediaStream.Flags.AUTO_DETECT
                        if probe
                        else types.MediaStream.Flags.REQUIRED
                    )
                    if media.video
                    else types.MediaStream.Flags.IGNORE
                ),
                ffmpeg_parameters=_ffmpeg_args(path),
            )
            if str(path).startswith("http"):
                kwargs["headers"] = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                    )
                }
            try:
                return types.MediaStream(**kwargs)
            except TypeError:  # this pytgcalls version has no `headers` argument
                kwargs.pop("headers", None)
                return types.MediaStream(**kwargs)

        # ffprobe/ffmpeg often cannot open the API's direct audio link from Heroku (empty probe output ->
        # JSONDecodeError / ProcessLookupError inside pytgcalls). Audio files are small, so play a local
        # copy and keep the link only as the fallback.
        _api = getattr(yt, "api_url", None)
        if _api and not media.video and str(media.file_path).startswith(_api):
            try:
                _local = await yt.download_local(media.id, media.url, media.video)
            except Exception as e:
                logger.warning(f"[Play] local copy first failed for {media.id}: {type(e).__name__}: {e}")
                _local = None
            if _local:
                media.file_path = _local

        async def _play(path: str) -> None:
            try:
                await client.play(
                    chat_id=chat_id,
                    stream=_build_stream(path),
                    config=types.GroupCallConfig(auto_start=False),
                )
            except (ProcessLookupError, asyncio.TimeoutError, ValueError) as e:
                # pytgcalls' ffprobe stream check died / timed out. Skip the check and play anyway.
                logger.warning(f"[Play] ffprobe check failed for {media.id} ({type(e).__name__}) - retrying without it.")
                await client.play(
                    chat_id=chat_id,
                    stream=_build_stream(path, probe=False),
                    config=types.GroupCallConfig(auto_start=False),
                )

        try:
            # Join the call / start the stream FIRST — thumbnail generation
            # (image processing) used to run before this and delayed the
            # assistant's join by however long that took. It now only
            # affects how fast the "Now Playing" caption appears, never
            # how fast the assistant actually joins the voice chat.
            # An already-running call keeps the mode it was started with: a call
            # that began as audio-only stays audio-only when a video is force-played
            # over it (/vplayforce, /cvplayforce) and vice-versa. When the mode
            # changes, leave and join again so the new stream starts correctly.
            want_video = bool(media.video)
            if self.call_video.get(chat_id, want_video) != want_video:
                logger.info(
                    f"[Play] {chat_id}: switching call to {'video' if want_video else 'audio'} — re-joining."
                )
                try:
                    await client.leave_call(chat_id, close=False)
                except Exception as e:
                    logger.warning(f"[Play] re-join before mode switch failed for {chat_id}: {e}")
                else:
                    await asyncio.sleep(0.5)

            try:
                await _play(media.file_path)
            except Exception as e:
                if not str(media.file_path or "").startswith("http"):
                    raise
                # ffmpeg couldn't open the direct link ("Audio source not found").
                # Fetch a real local copy and retry once, instead of letting the
                # bot think the song ended and jump to Autoplay.
                logger.warning(f"[Play] direct stream failed for {media.id}: {e} — downloading a local copy.")
                local = None
                try:
                    local = await yt.download_local(media.id, media.url, media.video)
                except Exception as de:
                    logger.error(f"[Play] local copy failed for {media.id}: {de}")
                if not local:
                    await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
                    if getattr(media, "user", None) != "Autoplay" and not queue.get_next(
                        chat_id, check=True
                    ):
                        return await self.stop(chat_id)
                    return await self.play_next(chat_id)
                media.file_path = local
                await _play(local)
            self.call_video[chat_id] = want_video
            if not seek_time:
                media.time = 1
                await db.add_call(chat_id)
                _thumb = None
                if show_thumb:
                    _thumb = (
                        await thumb.generate(media)
                        if isinstance(media, Track)
                        else config.DEFAULT_THUMB
                    )
                play_type = (
                    _lang.get("play_type_video", "🎥 Video")
                    if media.video
                    else _lang.get("play_type_audio", "🎵 Audio")
                )
                text = _lang["play_media"].format(
                    media.url,
                    media.title,
                    media.duration,
                    media.user,
                    play_type,
                )
                autoplay_on = await db.get_autoplay(chat_id)
                keyboard = buttons.controls(chat_id, _lang=_lang, autoplay_on=autoplay_on, playing=True)

                if show_thumb:
                    try:
                        await message.edit_media(
                            media=InputMediaPhoto(
                                media=_thumb,
                                caption=text,
                            ),
                            reply_markup=keyboard,
                        )
                    except (MessageIdInvalid, ChatSendMediaForbidden, ChatSendPhotosForbidden):
                        sent_msg = await app.send_photo(
                            chat_id=message.chat.id,
                            photo=_thumb,
                            caption=text,
                            reply_markup=keyboard,
                        )
                        media.message_id = sent_msg.id
                        media.message_chat_id = message.chat.id
                else:
                    try:
                        await message.edit_text(text, reply_markup=keyboard)
                    except Exception:
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        sent_msg = await app.send_message(
                            chat_id=message.chat.id,
                            text=text,
                            reply_markup=keyboard,
                        )
                        media.message_id = sent_msg.id
                        media.message_chat_id = message.chat.id
        except FileNotFoundError:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            await self.play_next(chat_id)
        except exceptions.NoActiveGroupCall:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_no_call"])
        except exceptions.NoAudioSourceFound:
            await message.edit_text(_lang["error_no_audio"])
            await self.play_next(chat_id)
        except (ConnectionError, ConnectionNotFound, TelegramServerError,
                TransportParseException, TimeoutError):
            await self.stop(chat_id)
            await message.edit_text(_lang["error_tg_server"])
        except RTMPStreamingUnsupported:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_rtmp"])
        except Exception as e:
            _why = await _diagnose_media(str(media.file_path))
            logger.error(
                f"[Play] failed for {media.id} (file_path={str(media.file_path)[:60]!r}): {type(e).__name__}: {e}"
                f" || DIAG: {_why}",
                exc_info=True,
            )
            try:
                await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            except Exception:
                pass
            await self.play_next(chat_id)


    async def replay(self, chat_id: int) -> None:
        if not await db.get_call(chat_id):
            return

        media = queue.get_current(chat_id)
        _lang = await lang.get_lang(chat_id)
        display_chat_id = getattr(media, "message_chat_id", 0) or chat_id
        msg = await app.send_message(chat_id=display_chat_id, text=_lang["play_again"])
        media.message_id = msg.id
        media.message_chat_id = display_chat_id
        await self.play_media(chat_id, msg, media)


    async def _delete_later(self, chat_id: int, message_id: int, delay: int = 1) -> None:
        try:
            await asyncio.sleep(delay)
            await app.delete_messages(chat_id=chat_id, message_ids=message_id, revoke=True)
        except Exception:
            pass

    async def play_next(self, chat_id: int) -> None:
        if loop := await db.get_loop(chat_id):
            await db.set_loop(chat_id, loop - 1)
            return await self.replay(chat_id)

        current = queue.get_current(chat_id)
        # Where the bot's status/control messages should appear — the chat
        # where /cplay (or /play) was actually typed, which can differ from
        # `chat_id` (the real playback target) when using /cplay from a
        # linked discussion group or the bot's DM. Falls back to chat_id
        # for normal same-chat plays.
        display_chat_id = getattr(current, "message_chat_id", 0) or chat_id

        if current:
            history = self.history[chat_id]
            history.append(current.id)
            del history[:-20]

            # the just-ended song's "Stream Initiated" card is no longer
            # needed once the song finishes — clear it out of the group
            # a second after it ends instead of leaving it sitting around.
            if current.message_id:
                asyncio.create_task(
                    self._delete_later(
                        getattr(current, "message_chat_id", 0) or chat_id,
                        current.message_id,
                        delay=1,
                    )
                )

        # reset the prefetch guard now that this song's lifecycle has ended
        self.autoplay_prefetching.discard(chat_id)

        media = queue.get_next(chat_id)
        try:
            if media.message_id:
                await app.delete_messages(
                    chat_id=getattr(media, "message_chat_id", 0) or chat_id,
                    message_ids=media.message_id,
                    revoke=True,
                )
                media.message_id = 0
        except:
            pass

        if not media:
            if current and isinstance(current, Track) and await db.get_autoplay(chat_id):
                _lang = await lang.get_lang(chat_id)

                # fast path: a track was already searched & downloaded in the
                # background (~30s before this song ended) — instant, no lag
                related = self.pending_autoplay.pop(chat_id, None)

                if not related:
                    notice = await app.send_message(
                        chat_id=display_chat_id,
                        text=_lang.get(
                            "autoplay_searching",
                            "🔎 Queue is empty — Autoplay is searching for a related song...",
                        ),
                    )
                    try:
                        related = await yt.get_related(current, self.history[chat_id])
                    except Exception as e:
                        logger.error(f"[Autoplay] Unexpected error for chat {chat_id}: {e}")
                        related = None

                    try:
                        await notice.delete()
                    except:
                        pass

                if related:
                    related.user = "Autoplay"
                    related.message_chat_id = display_chat_id
                    queue.add(chat_id, related)
                    media = queue.get_current(chat_id)
                else:
                    await app.send_message(
                        chat_id=display_chat_id,
                        text=_lang.get(
                            "autoplay_failed",
                            "⚠️ Autoplay couldn't find a related song to play next, so the stream has ended.",
                        ),
                    )

            if not media:
                return await self.stop(chat_id)

        _lang = await lang.get_lang(chat_id)
        display_chat_id = getattr(media, "message_chat_id", 0) or display_chat_id
        msg = await app.send_message(chat_id=display_chat_id, text=_lang["play_next"])

        MAX_AUTOPLAY_RETRIES = 3
        attempts = 0
        while not media.file_path:
            media.file_path = await yt.download(media.id, video=media.video, _url=media.url)
            if media.file_path:
                break

            # download failed. If this track came from Autoplay (not a
            # user-queued request), don't just stop the stream — try
            # another related song instead, a few times.
            autoplay_track = isinstance(media, Track) and media.user == "Autoplay"
            if autoplay_track and await db.get_autoplay(chat_id) and attempts < MAX_AUTOPLAY_RETRIES:
                attempts += 1
                logger.warning(
                    f"[Autoplay] Download failed for {media.id}, searching another "
                    f"related track ({attempts}/{MAX_AUTOPLAY_RETRIES})."
                )
                self.history[chat_id].append(media.id)
                queue.remove_current(chat_id)

                try:
                    related = await yt.get_related(current or media, self.history[chat_id])
                except Exception as e:
                    logger.error(f"[Autoplay] Unexpected error for chat {chat_id}: {e}")
                    related = None

                if not related:
                    await self.stop(chat_id)
                    return await msg.edit_text(
                        _lang.get(
                            "autoplay_failed",
                            "⚠️ Autoplay couldn't find a related song to play next, so the stream has ended.",
                        )
                    )

                related.user = "Autoplay"
                related.message_chat_id = display_chat_id
                queue.add(chat_id, related)
                media = queue.get_current(chat_id)
                continue

            await self.stop(chat_id)
            return await msg.edit_text(
                _lang["error_no_file"].format(config.SUPPORT_CHAT)
            )

        media.message_id = msg.id
        media.message_chat_id = display_chat_id
        await self.play_media(chat_id, msg, media)


    async def ping(self) -> float:
        pings = [client.ping for client in self.clients]
        return round(sum(pings) / len(pings), 2)


    async def decorators(self, client: PyTgCalls) -> None:
        participant_update = getattr(types, "UpdatedGroupCallParticipant", None)

        @client.on_update()
        async def update_handler(_, update: types.Update) -> None:
            if isinstance(update, types.StreamEnded):
                if update.stream_type == types.StreamEnded.Type.AUDIO:
                    await self.play_next(update.chat_id)
            elif isinstance(update, types.ChatUpdate):
                if update.status in [
                    types.ChatUpdate.Status.KICKED,
                    types.ChatUpdate.Status.LEFT_GROUP,
                    types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                ]:
                    await self.stop(update.chat_id)
            elif participant_update and isinstance(update, participant_update):
                try:
                    if not await db.get_vc_logger(update.chat_id):
                        return

                    # `action` lives on the update itself; `user_id` lives on
                    # update.participant. Fall back defensively in case this
                    # differs across pytgcalls versions.
                    action = getattr(update, "action", None)
                    if action is None:
                        action = getattr(update.participant, "action", None)

                    user_id = getattr(update.participant, "user_id", None)
                    if user_id is None:
                        user_id = getattr(update, "user_id", None)

                    if action == types.GroupCallParticipant.Action.JOINED:
                        await vclogger.notify_join(update.chat_id, user_id)
                    elif action == types.GroupCallParticipant.Action.LEFT:
                        await vclogger.notify_leave(update.chat_id, user_id)
                except Exception as e:
                    logger.error(f"[VCLogger] Update handling error: {e}")


    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=100)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)
        logger.info("PyTgCalls client(s) started.")
