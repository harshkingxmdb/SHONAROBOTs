# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic


import asyncio
import os
import platform
import sys

import psutil
from pyrogram import __version__, filters, types
from pytgcalls import __version__ as pytgver

from AloneX.music import app, config, db, lang, userbot
from AloneX.music.plugins import all_modules


def _sudo_stats(pid: int) -> tuple:
    """psutil calls block (cpu_percent waits 1s), so run them in a thread."""
    process = psutil.Process(pid)
    storage = psutil.disk_usage("/")
    return (
        f"{process.memory_info().rss / 1024**2:.2f}",
        round(psutil.virtual_memory().total / (1024.0**3)),
        process.cpu_percent(interval=1.0),
        psutil.cpu_count(logical=False) or psutil.cpu_count() or "?",
        f"{storage.used / (1024.0**3):.2f}",
        f"{storage.total / (1024.0**3):.2f}",
    )


@app.on_message(filters.command(["mstats", "musicstats"]) & ~app.bl_users)
@lang.language()
async def _stats(_, m: types.Message):
    # works in groups AND in private chat; falls back to plain text if the
    # photo can't be sent (dead PING_IMG link etc.)
    has_photo = True
    try:
        sent = await m.reply_photo(photo=config.PING_IMG, caption=m.lang["stats_fetching"])
    except Exception:
        has_photo = False
        sent = await m.reply_text(m.lang["stats_fetching"])

    _utext = m.lang["stats_user"].format(
        app.name,
        len(userbot.clients),
        config.AUTO_LEAVE,
        len(db.blacklisted),
        len(app.bl_users),
        len(app.sudoers),
        len(await db.get_chats()),
        len(await db.get_users()),
    )
    if m.from_user.id in app.sudoers:
        ram, total_ram, cpu, cores, used, total = await asyncio.to_thread(_sudo_stats, os.getpid())
        _utext += m.lang["stats_sudo"].format(
            len(all_modules),
            platform.system(),
            ram,
            total_ram,
            cpu,
            cores,
            used,
            total,
            sys.version.split()[0],
            __version__,
            pytgver,
        )

    if has_photo:
        await sent.edit_caption(_utext)
    else:
        await sent.edit_text(_utext)
