# Copyright (c) 2025 @THECDERQUEEN
# Licensed under the MIT License.
# This file is part of @SHONA_BOTS
#SHONA-DECODER

import asyncio
import time

from pyrogram import enums, errors, filters, types

from AloneX.music import anon, app, config, db, lang, logger, queue, tasks, userbot, yt
from AloneX.music.helpers import buttons


@app.on_message(filters.video_chat_started, group=19)
@app.on_message(filters.video_chat_ended, group=20)
async def _watcher_vc(_, m: types.Message):
    await anon.stop(m.chat.id)


async def auto_leave():
    while True:
        await asyncio.sleep(1800)
        for ub in userbot.clients:
            left = 0
            try:
                for dialog in await ub.get_dialogs():
                    chat_id = dialog.chat.id
                    if left >= 20:
                        break
                    if chat_id in [app.logger, -1001686672798, -1001549206010]:
                        continue
                    if dialog.chat.type not in [
                        enums.ChatType.GROUP,
                        enums.ChatType.SUPERGROUP,
                    ]:
                        continue
                    if chat_id in db.active_calls:
                        continue

                    # keep the assistant only where the bot itself is an admin;
                    # leave everywhere else (bot not admin, or not even present)
                    try:
                        member = await app.get_chat_member(chat_id, app.id)
                        bot_is_admin = member.status in (
                            enums.ChatMemberStatus.ADMINISTRATOR,
                            enums.ChatMemberStatus.OWNER,
                        )
                    except Exception:
                        bot_is_admin = False

                    if bot_is_admin:
                        continue

                    await ub.leave_chat(chat_id)
                    left += 1
                    await asyncio.sleep(5)
            except:
                continue


async def track_time():
    while True:
        await asyncio.sleep(1)
        for chat_id in list(db.active_calls):
            if not await db.playing(chat_id):
                continue
            media = queue.get_current(chat_id)
            if not media:
                continue
            media.time += 1


_prefetch_tasks: set[str] = set()


def _start_prefetch(chat_id: int, key: str, coro) -> None:
    """Runs a download in the background so the progress-bar loop (which
    covers every chat) never waits on a slow video download."""
    guard = f"{chat_id}:{key}"
    if guard in _prefetch_tasks:
        coro.close()
        return
    _prefetch_tasks.add(guard)

    async def runner():
        try:
            await coro
        except Exception as e:
            logger.error(f"[Prefetch] {guard} failed: {e}")
        finally:
            _prefetch_tasks.discard(guard)

    asyncio.create_task(runner())


async def _prefetch_queued(next_track) -> None:
    if not next_track.file_path:
        next_track.file_path = await yt.download(
            next_track.id, video=next_track.video, _url=next_track.url
        )


async def _prefetch_autoplay(chat_id: int, media) -> None:
    try:
        related = await yt.get_related(media, anon.history[chat_id])
        if related:
            related.file_path = await yt.download(
                related.id, video=related.video, _url=related.url
            )
            if related.file_path:
                related.message_chat_id = getattr(media, "message_chat_id", 0) or chat_id
                anon.pending_autoplay[chat_id] = related
    except Exception as e:
        logger.error(f"[Autoplay] Prefetch failed for chat {chat_id}: {e}")


async def _update_chat_timer(chat_id: int, length: int) -> None:
    if not await db.playing(chat_id):
        return
    try:
        media = queue.get_current(chat_id)
        duration, message_id = media.duration_sec, media.message_id
        if not duration or not message_id or not media.time:
            return
        played = media.time
        remaining = duration - played
        pos = min(int((played / duration) * length), length - 1)
        timer = "—" * pos + "⬤" + "—" * (length - pos - 1)

        # videos are bigger/slower to fetch than audio, so start earlier
        window = 90 if getattr(media, "video", False) else 30
        if remaining <= window:
            next = queue.get_next(chat_id, check=True)
            if next and not next.file_path:
                _start_prefetch(chat_id, f"q:{next.id}", _prefetch_queued(next))
            elif (
                not next
                and chat_id not in anon.autoplay_prefetching
                and chat_id not in anon.pending_autoplay
                and await db.get_autoplay(chat_id)
            ):
                anon.autoplay_prefetching.add(chat_id)
                _start_prefetch(chat_id, f"a:{media.id}", _prefetch_autoplay(chat_id, media))

        if remaining < 10:
            remove = True
        else:
            remove = False
            timer = f"{time.strftime('%M:%S', time.gmtime(played))} | {timer} | -{time.strftime('%M:%S', time.gmtime(remaining))}"

        _lang = await lang.get_lang(chat_id)
        autoplay_on = await db.get_autoplay(chat_id)
        display_chat_id = getattr(media, "message_chat_id", 0) or chat_id
        await app.edit_message_reply_markup(
            chat_id=display_chat_id,
            message_id=message_id,
            reply_markup=buttons.controls(
                chat_id=chat_id,
                timer=timer,
                remove=remove,
                _lang=_lang,
                autoplay_on=autoplay_on,
                played=played,
                playing=True,
            ),
        )
    except Exception:
        pass


async def update_timer(length=10):
    while True:
        await asyncio.sleep(7)
        chat_ids = list(db.active_calls)
        if chat_ids:
            # Run every chat's update concurrently — a slow autoplay
            # prefetch (network + download) in one group must never
            # block the progress-bar refresh for every other group.
            await asyncio.gather(
                *(_update_chat_timer(cid, length) for cid in chat_ids),
                return_exceptions=True,
            )


async def vc_watcher(sleep=15):
    while True:
        await asyncio.sleep(sleep)
        for chat_id in list(db.active_calls):
            client = await db.get_assistant(chat_id)
            media = queue.get_current(chat_id)
            participants = await client.get_participants(chat_id)
            if len(participants) < 2 and media.time > 30:
                _lang = await lang.get_lang(chat_id)
                try:
                    sent = await app.edit_message_reply_markup(
                        chat_id=getattr(media, "message_chat_id", 0) or chat_id,
                        message_id=media.message_id,
                        reply_markup=buttons.controls(
                            chat_id=chat_id, status=_lang["stopped"], remove=True
                        ),
                    )
                    await anon.stop(chat_id)
                    await sent.reply_text(_lang["auto_left"])
                except errors.MessageIdInvalid:
                    pass


if config.AUTO_END:
    tasks.append(asyncio.create_task(vc_watcher()))
if config.AUTO_LEAVE:
    tasks.append(asyncio.create_task(auto_leave()))
tasks.append(asyncio.create_task(track_time()))
tasks.append(asyncio.create_task(update_timer()))

