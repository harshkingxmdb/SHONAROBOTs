# Copyright (c) 2025 @THECDERQUEEN
# Licensed under the MIT License.
# This file is part of @SHONA_BOTS
#SHONA-DECODER

import asyncio
import platform
import sys
import time

import psutil

from pyrogram import __version__ as pyrover
from pyrogram import filters, types
from pytgcalls import __version__ as pytgver

from AloneX.music import anon, app, boot, config, lang
from AloneX.music.helpers import buttons


def _get_uptime(seconds: int) -> str:
    units = [("s", 60), ("m", 60), ("h", 24), ("days", None)]
    parts = []
    remaining = seconds
    for unit, mod in units:
        value = remaining % mod if mod else remaining
        remaining = remaining // mod if mod else 0
        parts.append(f"{value}{unit}")
    days = parts[-1]
    rest = ":".join(reversed(parts[:-1]))
    if parts[-1][:-4] != "0":
        return f"{days}, {rest}"
    return rest


def _get_cpu_model() -> str:
    try:
        if platform.system() == "Linux":
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or platform.machine() or "Unknown"


def _get_network_speed() -> str:
    try:
        stats = psutil.net_if_stats()
        best = max((s.speed for s in stats.values() if s.speed > 0), default=0)
        if best:
            return f"{best} Mbps"
    except Exception:
        pass
    return "Unknown"


def _get_active_tasks() -> int:
    try:
        return len(asyncio.all_tasks())
    except Exception:
        return 0


@app.on_message(filters.command(["mping", "musicping"]) & ~app.bl_users)
@lang.language()
async def _ping(_, m: types.Message):
    start = time.time()
    sent = await m.reply_text(m.lang["pinging"])

    latency = round((time.time() - start) * 1000, 2)
    uptime = _get_uptime(int(time.time() - boot))

    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    pytg_latency = await anon.ping()

    status = "✅ Running Stable"
    if cpu_percent > 90 or mem.percent > 90 or disk.percent > 95:
        status = "⚠️ Under Heavy Load"

    text = (
        "🏓 <b>Pong!</b>\n\n"
        f"⚡ <b>Response Time:</b> <code>{latency}ms</code>\n\n"
        f"⏰ <b>Uptime:</b> <code>{uptime}</code>\n\n"
        f"🖥 <b>Runtime:</b> Python {sys.version.split()[0]} "
        f"⚙️ Tasks: {_get_active_tasks()}\n\n"
        f"🔥 <b>CPU Usage:</b> <code>{cpu_percent}%</code>\n"
        f"💾 <b>Memory Usage:</b> <code>{mem.percent}%</code>\n"
        f"📦 <b>Disk Usage:</b> <code>{disk.percent}%</code>\n\n"
        f"🖳 <b>Server:</b> {_get_cpu_model()}\n"
        f"🌐 <b>Network:</b> {_get_network_speed()}\n"
        f"🚀 <b>PyTgCalls Latency:</b> <code>{pytg_latency}ms</code>\n\n"
        f"{status}"
    )

    await sent.edit_media(
        media=types.InputMediaPhoto(
            media=config.PING_IMG,
            caption=text,
        ),
        reply_markup=buttons.ping_markup(m.lang["support"]),
    )
