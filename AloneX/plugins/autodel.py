import asyncio
import re
import logging
from telethon import events
from AloneX import tbot, prefix_cmds, DEV_LIST, font
from AloneX.db.autodelete import (
    set_autodelete, 
    get_autodelete, 
    disable_autodelete,
    get_all_autodelete_chats
)

logger = logging.getLogger(__name__)

auto_delete_chats = {}
pending_tasks = set()
shutdown_event = asyncio.Event()

def parse_time(t: str) -> int:
    t = t.lower().strip()
    m = re.match(r'^(\d+)([smhd])$', t)
    if not m:
        return None
    v, u = int(m.group(1)), m.group(2)
    return v * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[u]

def format_time(s: int) -> str:
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s//60}m"
    if s < 86400:
        return f"{s//3600}h"
    return f"{s//86400}d"

async def delete_message(msg, delay: int):
    task = asyncio.current_task()
    pending_tasks.add(task)
    
    try:
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=delay)
            return
        except asyncio.TimeoutError:
            pass
        
        await msg.delete()
        
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
    finally:
        pending_tasks.discard(task)

async def is_admin(e):
    if e.sender_id in DEV_LIST:
        return True
    try:
        p = await e.client.get_permissions(e.chat_id, e.sender_id)
        return p.is_admin
    except:
        return False

async def load_autodelete_cache():
    global auto_delete_chats
    try:
        chats = await get_all_autodelete_chats()
        auto_delete_chats.update(chats)
    except Exception as e:
        logger.error(f"Error loading cache: {e}")

async def autodel_handler(e):
    if e.is_channel and not e.is_group:
        return
    
    if e.fwd_from:
        return
    
    if not await is_admin(e):
        m = await e.reply(font("❌ Only admins or devs can use this command."))
        asyncio.create_task(delete_message(m, 3))
        asyncio.create_task(delete_message(e.message, 3))
        return
    
    cid = e.chat_id
    parts = e.text.split(maxsplit=1)
    
    if len(parts) < 2:
        d = await get_autodelete(cid)
        if d:
            m = await e.reply(f"✅ **Auto Delete: ON**\n⏱️ Time: `{format_time(d)}`\n\nTurn off: `{prefix_cmds[0]}autodel off`")
        else:
            m = await e.reply(f"❌ **Auto Delete: OFF**\n\nEnable: `{prefix_cmds[0]}autodel 30s`\nTurn off: `{prefix_cmds[0]}autodel off`")
        asyncio.create_task(delete_message(m, 5))
        asyncio.create_task(delete_message(e.message, 5))
        return
    
    arg = parts[1].lower().strip()
    
    if arg in ("off", "stop", "disable"):
        d = await get_autodelete(cid)
        if d:
            await disable_autodelete(cid)
            if cid in auto_delete_chats:
                del auto_delete_chats[cid]
            m = await e.reply(font("✅ **Auto Delete turned OFF**"))
        else:
            m = await e.reply(font("ℹ️ Auto Delete is already OFF"))
        asyncio.create_task(delete_message(m, 3))
        asyncio.create_task(delete_message(e.message, 3))
        return
    
    d = parse_time(arg)
    if d is None or d < 5 or d > 604800:
        m = await e.reply(font("❌ **Invalid time format**\n\nUse: `5s` to `7d`\nExamples: `30s`, `5m`, `1h`, `2d`"))
        asyncio.create_task(delete_message(m, 4))
        asyncio.create_task(delete_message(e.message, 4))
        return
    
    await set_autodelete(cid, d)
    auto_delete_chats[cid] = d
    m = await e.reply(f"✅ **Auto Delete: ON**\n⏱️ Time: `{format_time(d)}`\n\nAll messages will be deleted after {format_time(d)}")
    asyncio.create_task(delete_message(m, 5))
    asyncio.create_task(delete_message(e.message, 5))

async def message_watcher(e):
    if e.is_channel and not e.is_group:
        return
    
    cid = e.chat_id
    
    try:
        bot_id = (await e.client.get_me()).id
        if e.sender_id == bot_id:
            return
    except:
        return
    
    if cid not in auto_delete_chats:
        d = await get_autodelete(cid)
        if d:
            auto_delete_chats[cid] = d
        else:
            return
    else:
        d = auto_delete_chats[cid]
    
    asyncio.create_task(delete_message(e.message, d))

if not hasattr(tbot, "handlers_loaded"):
    tbot.handlers_loaded = set()

prefix_regex = f"^[{re.escape(''.join(prefix_cmds))}]autodel( |$)"

if "autodelete" not in tbot.handlers_loaded:
   # asyncio.create_task(load_autodelete_cache())
    tbot.add_event_handler(autodel_handler, events.NewMessage(pattern=prefix_regex, incoming=True))
    tbot.add_event_handler(message_watcher, events.NewMessage(incoming=True))
    tbot.handlers_loaded.add("autodelete")

__module__ = "𝐀ᴜᴛᴏ-𝐃ᴇʟ🗑"
__help__ = """
*Automatically Deleted All Massage*

• Enable: `/autodel 30s`
• Turn off: `/autodel off`

• `/autodel 1d` - Auto Delete On
• `/autodel off` - Auto Delete Off
"""
