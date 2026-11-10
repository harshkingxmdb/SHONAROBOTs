import psutil
import platform
import time
import requests
from datetime import datetime
import pytz
from telethon import events, Button
from telegram import __version__ as ptbver
from pyrogram import __version__ as pyrover
from telethon import __version__ as tlver
try:
    from pytgcalls import __version__ as pytgver
except ImportError:
    pytgver = "Not Installed"
try:
    from ntgcalls import __version__ as ntgver
except ImportError:
    ntgver = "Not Installed"
from AloneX import tbot, pbot, app, START_TIME, database as db, prefix_cmds, font

IST = pytz.timezone("Asia/Kolkata")
_handlers_registered = False

def readable_time(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    return f"{d}d {h}h {m}m {s}s"

async def get_basic_stats() -> dict:
    try:
        current_time = time.time()
        bot_uptime = readable_time(current_time - START_TIME)
        ist_time = datetime.now(IST).strftime("%d %b %Y • %I:%M:%S %p")
        
        return {
            "bot_uptime": bot_uptime,
            "ist_time": ist_time,
            "python_version": platform.python_version(),
            "pyrogram_version": pyrover,
            "ptb_version": ptbver,
            "telethon_version": tlver,
            "pytgcalls_version": pytgver,
            "ntgcalls_version": ntgver
        }
    except Exception:
        return None

async def get_detailed_stats() -> dict:
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        current_time = time.time()
        bot_uptime = readable_time(current_time - START_TIME)
        system_uptime = readable_time(current_time - psutil.boot_time())
        ist_time = datetime.now(IST).strftime("%d %b %Y • %I:%M:%S %p")
        
        try:
            cpu_freq = psutil.cpu_freq().current
            cpu_freq = f"{round(cpu_freq / 1000, 2)} GHz" if cpu_freq >= 1000 else f"{round(cpu_freq, 2)} MHz"
        except:
            cpu_freq = "Unknown"
        
        p_core = psutil.cpu_count(logical=False)
        t_core = psutil.cpu_count(logical=True)
        
        try:
            response = requests.get("http://ipinfo.io/json", timeout=5)
            ip_info = response.json()
            public_ip = ip_info.get('ip', 'Unknown')
            location = f"{ip_info.get('city', 'Unknown')}, {ip_info.get('country', 'Unknown')}"
        except:
            public_ip = "Unknown"
            location = "Unknown"
        
        try:
            result = await db.command({"dbStats": 1})
            data_size = round(result['dataSize']/(1024*1024), 2)
            storage_size = round(result['storageSize']/(1024*1024), 2)
            index_size = round(result['indexSize']/(1024*1024), 2)
            collections = result['collections']
        except Exception:
            data_size = storage_size = index_size = collections = 0
        
        return {
            "cpu": cpu_percent,
            "ram_used": memory.percent,
            "ram_total": round(memory.total / (1024**3), 1),
            "ram_available": round(memory.available / (1024**3), 1),
            "disk_used": round((disk.used / disk.total) * 100, 1),
            "disk_total": round(disk.total / (1024**3), 1),
            "disk_free": round(disk.free / (1024**3), 1),
            "cpu_freq": cpu_freq,
            "p_core": p_core,
            "t_core": t_core,
            "bot_uptime": bot_uptime,
            "system_uptime": system_uptime,
            "ist_time": ist_time,
            "python_version": platform.python_version(),
            "pyrogram_version": pyrover,
            "ptb_version": ptbver,
            "telethon_version": tlver,
            "pytgcalls_version": pytgver,
            "ntgcalls_version": ntgver,
            "platform": f"{platform.system()} {platform.release()}",
            "architecture": platform.architecture()[0],
            "public_ip": public_ip,
            "location": location,
            "data_size": data_size,
            "storage_size": storage_size,
            "index_size": index_size,
            "collections": collections
        }
    except Exception:
        return None

async def alive_handler(event):
    if event.is_channel and not event.is_group:
        return
    if event.fwd_from:
        return
    
    stats = await get_basic_stats()
    
    if not stats:
        text = f"❂ **Shona is Alive**\n\n**Uptime:** `{readable_time(time.time() - START_TIME)}`"
        buttons = None
    else:
        text = (
            f"❂ **Shona is Online**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**Uptime:** `{stats['bot_uptime']}`\n"
            f"**Time:** `{stats['ist_time']}`\n\n"
            f"**Software Versions:**\n"
            f"• **Python:** `{stats['python_version']}`\n"
            f"• **Pyrogram:** `{stats['pyrogram_version']}`\n"
            f"• **PTB:** `{stats['ptb_version']}`\n"
            f"• **Telethon:** `{stats['telethon_version']}`\n"
            f"• **Py-TgCalls:** `{stats['pytgcalls_version']}`\n"
            f"• **NTgCalls:** `{stats['ntgcalls_version']}`"
        )
        buttons = [[Button.inline("❂ System Stats", b"system_stats")]]
    
    await event.reply(
        text,
        file="https://litter.catbox.moe/653xsr.jpg",
        buttons=buttons
    )

async def show_system_stats(event):
    await event.answer(font("❂ Loading system stats..."))
    await event.edit("❂ **Loading System Stats...**")
    
    stats = await get_detailed_stats()
    
    if not stats:
        await event.edit("❂ **Error loading system stats**")
        return
    
    text = (
        f"❂ **System Statistics**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"**Performance:**\n"
        f"├ **CPU:** `{stats['cpu']:.1f}%` (`{stats['cpu_freq']}`)\n"
        f"├ **Cores:** `{stats['p_core']}P + {stats['t_core']}T`\n"
        f"├ **RAM:** `{stats['ram_used']:.1f}%` (`{stats['ram_total'] - stats['ram_available']:.1f}GB/{stats['ram_total']}GB`)\n"
        f"└ **Storage:** `{stats['disk_used']}%` (`{stats['disk_free']:.1f}GB/{stats['disk_total']:.1f}GB`)\n\n"
        f"**System Info:**\n"
        f"├ **Platform:** `{stats['platform']}`\n"
        f"├ **Architecture:** `{stats['architecture']}`\n"
        f"├ **Location:** `{stats['location']}`\n"
        f"├ **Public IP:** `{stats['public_ip']}`\n"
        f"├ **Bot Uptime:** `{stats['bot_uptime']}`\n"
        f"└ **System Uptime:** `{stats['system_uptime']}`\n\n"
        f"**Database:**\n"
        f"├ **Collections:** `{stats['collections']}`\n"
        f"├ **Data Size:** `{stats['data_size']} MB`\n"
        f"├ **Storage Size:** `{stats['storage_size']} MB`\n"
        f"└ **Index Size:** `{stats['index_size']} MB`\n\n"
        f"**Versions:**\n"
        f"├ **Python:** `{stats['python_version']}`\n"
        f"├ **Pyrogram:** `{stats['pyrogram_version']}`\n"
        f"├ **PTB:** `{stats['ptb_version']}`\n"
        f"├ **Telethon:** `{stats['telethon_version']}`\n"
        f"├ **Py-TgCalls:** `{stats['pytgcalls_version']}`\n"
        f"└ **NTgCalls:** `{stats['ntgcalls_version']}`"
    )
    
    buttons = [
        [Button.inline("❂ Back", b"back_to_alive"),
         Button.inline("❂ Refresh", b"refresh_system_stats")]
    ]
    
    await event.edit(text, buttons=buttons)

async def refresh_system_stats(event):
    await event.answer(font("❂ Refreshing stats..."))
    await event.edit("❂ **Refreshing System Stats...**")
    await show_system_stats(event)

async def backs_to_alive(event):
    await event.answer()
    stats = await get_basic_stats()
    
    if not stats:
        text = f"❂ **shona is Alive**\n\n**Uptime:** `{readable_time(time.time() - START_TIME)}`"
        buttons = None
    else:
        text = (
            f"❂ **shona is Online**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**Uptime:** `{stats['bot_uptime']}`\n"
            f"**Time:** `{stats['ist_time']}`\n\n"
            f"**Software Versions:**\n"
            f"• **Python:** `{stats['python_version']}`\n"
            f"• **Pyrogram:** `{stats['pyrogram_version']}`\n"
            f"• **PTB:** `{stats['ptb_version']}`\n"
            f"• **Telethon:** `{stats['telethon_version']}`\n"
            f"• **Py-TgCalls:** `{stats['pytgcalls_version']}`\n"
            f"• **NTgCalls:** `{stats['ntgcalls_version']}`"
        )
        buttons = [[Button.inline("❂ System Stats", b"system_stats")]]
    
    await event.edit(text, buttons=buttons, file="https://litter.catbox.moe/653xsr.jpg")

async def close_panel(event):
    await event.delete()
    await event.answer(font("Panel closed successfully!"))

async def ping_handler(event):
    if event.is_channel and not event.is_group:
        return
    if event.fwd_from:
        return
    
    start_ptb = time.perf_counter()
    try:
        await app.bot.get_me()
        end_ptb = time.perf_counter()
        ptb_ping = round((end_ptb - start_ptb) * 1000, 2)
    except:
        ptb_ping = "N/A"
    
    start_pyro = time.perf_counter()
    try:
        await pbot.get_me()
        end_pyro = time.perf_counter()
        pyro_ping = round((end_pyro - start_pyro) * 1000, 2)
    except:
        pyro_ping = "N/A"
    
    start_tl = time.perf_counter()
    ping_msg = await event.reply("❂")
    end_tl = time.perf_counter()
    tl_ping = round((end_tl - start_tl) * 1000, 2)
    
    uptime = readable_time(time.time() - START_TIME)
    current_time = datetime.now(IST).strftime("%I:%M:%S %p")
    
    text = (
        f"❂ **Pong!**\n\n"
        f"**Telethon:** `{tl_ping} ms`\n"
        f"**Pyrogram:** `{pyro_ping} ms`\n"
        f"**PTB:** `{ptb_ping} ms`\n\n"
        f"**Uptime:** `{uptime}`\n"
        f"**Time:** `{current_time}`"
    )
    await ping_msg.edit(text)

if "alive" not in tbot.handlers_loaded:
    tbot.add_event_handler(alive_handler, events.NewMessage(pattern=f"^{prefix_cmds}alive$", incoming=True))
    tbot.add_event_handler(ping_handler, events.NewMessage(pattern=f"^{prefix_cmds}ping$", incoming=True))
    tbot.add_event_handler(show_system_stats, events.CallbackQuery(pattern=b"system_stats"))
    tbot.add_event_handler(refresh_system_stats, events.CallbackQuery(pattern=b"refresh_system_stats"))
    tbot.add_event_handler(backs_to_alive, events.CallbackQuery(pattern=b"back_to_alive"))
    tbot.add_event_handler(close_panel, events.CallbackQuery(pattern=b"alive_close_panel"))
    tbot.handlers_loaded.add("alive")
