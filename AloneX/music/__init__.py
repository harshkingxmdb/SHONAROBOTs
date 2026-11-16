# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic
#ALONE-CODER
#
# Music system, embedded inside the manage bot as the `AloneX.music` sub-package.
# It is started from AloneX/__main__.py (see AloneX/music/runner.py) and shares the
# manage bot's .env, so the manage bot keeps working even if music is not configured.

import time
import asyncio
import logging

import shutil

# Heroku installs ffmpeg through the Aptfile. static_ffmpeg is only a fallback: it downloads a
# binary on every start (the Heroku disk is wiped on each restart), so skip it when ffmpeg exists.
if not shutil.which("ffmpeg"):
    try:
        import static_ffmpeg

        static_ffmpeg.add_paths()
    except Exception:  # pragma: no cover
        pass

# pytgcalls runs `ffprobe` on a stream link and kills it after a timeout. When the process has
# already exited by then, asyncio raises ProcessLookupError and the whole play() call crashes
# (seen on Heroku). Killing / terminating a process that is already gone is a harmless no-op, so
# ignore that error. Nothing else is changed.
if not getattr(asyncio.subprocess.Process, "_music_safe_signals", False):
    _orig_kill = asyncio.subprocess.Process.kill
    _orig_terminate = asyncio.subprocess.Process.terminate

    def _safe_kill(self):
        try:
            _orig_kill(self)
        except ProcessLookupError:
            pass

    def _safe_terminate(self):
        try:
            _orig_terminate(self)
        except ProcessLookupError:
            pass

    asyncio.subprocess.Process.kill = _safe_kill
    asyncio.subprocess.Process.terminate = _safe_terminate
    asyncio.subprocess.Process._music_safe_signals = True

# NOTE: the manage bot already configures the root logger, so no basicConfig() here.
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("ntgcalls").setLevel(logging.CRITICAL)
logging.getLogger("pymongo").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("pytgcalls").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


def _fix_apt_library_path() -> None:
    """Heroku's apt buildpack installs ffmpeg under ~/.apt, but the folder that holds
    libpulsecommon-*.so (usr/lib/<arch>/pulseaudio) is not on LD_LIBRARY_PATH, so ffmpeg AND ffprobe die
    with "error while loading shared libraries: libpulsecommon-17.0.so". Add that folder to the
    environment: every ffmpeg / ffprobe we start inherits it. Safe no-op everywhere else."""
    try:
        import glob
        import os

        apt = os.path.join(os.environ.get("HOME", "/app"), ".apt")
        if not os.path.isdir(apt):
            return
        found = {
            os.path.dirname(path)
            for path in glob.glob(os.path.join(apt, "usr", "lib", "**", "libpulsecommon-*.so"), recursive=True)
        }
        current = [d for d in os.environ.get("LD_LIBRARY_PATH", "").split(":") if d]
        extra = [d for d in sorted(found) if d not in current]
        if extra:
            os.environ["LD_LIBRARY_PATH"] = ":".join(current + extra)
            logger.info(f"[FFmpeg] added to LD_LIBRARY_PATH: {', '.join(extra)}")
        elif not found:
            logger.error(
                "[FFmpeg] libpulsecommon-*.so not found under ~/.apt - add `libpulse0` to the Aptfile "
                "if ffmpeg still fails to start."
            )
    except Exception as e:  # never break startup because of this
        logger.warning(f"[FFmpeg] library path fix skipped: {type(e).__name__}: {e}")


_fix_apt_library_path()

# "Too many open files" fix: the default limit (often 1024) is far too low for a
# music bot (every call = ffmpeg pipes, every request = a socket). Raise the
# soft limit up to the hard limit.
try:
    import resource

    _soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    _target = 65535 if _hard == resource.RLIM_INFINITY else min(_hard, 65535)
    if _soft == resource.RLIM_INFINITY or _soft < _target:
        resource.setrlimit(resource.RLIMIT_NOFILE, (_target, _hard))
    logger.info(f"Open files limit: {resource.getrlimit(resource.RLIMIT_NOFILE)[0]}")
except Exception as _e:
    logger.warning(f"Could not raise open files limit: {_e}")


__version__ = "3.0.1"

# One config for everything: the music settings live in the root config.py (class MusicConfig).
from config import MusicConfig

config = MusicConfig()
tasks = []
boot = time.time()

#: True only when every required music setting (assistant session etc.) is present.
#: When False nothing below is created, so the manage bot is not affected at all.
READY = not config.missing()

if not READY:
    logger.warning(
        "Music system is DISABLED - missing settings: %s. "
        "Set them in .env (SESSION1 is the music assistant account).",
        ", ".join(config.missing()),
    )
else:
    from AloneX.music.core.bot import Bot

    app = Bot()

    from AloneX.music.core.dir import ensure_dirs

    ensure_dirs()

    from AloneX.music.core.userbot import Userbot

    userbot = Userbot()

    from AloneX.music.core.mongo import MongoDB

    db = MongoDB()

    from AloneX.music.core.lang import Language

    lang = Language()

    from AloneX.music.core.telegram import Telegram
    from AloneX.music.core.youtube import YouTube

    tg = Telegram()
    yt = YouTube()

    from AloneX.music.helpers import Queue

    queue = Queue()

    from AloneX.music.core.calls import TgCall

    anon = TgCall()

    async def stop() -> None:
        """Stop the music system only (the manage bot keeps running)."""
        logger.info("Stopping music...")
        for task in tasks:
            task.cancel()
            try:
                await task
            except BaseException:
                pass

        try:
            await app.exit()
        except Exception:
            pass
        try:
            await userbot.exit()
        except Exception:
            pass
        try:
            await db.close()
        except Exception:
            pass

        logger.info("Music stopped.")
