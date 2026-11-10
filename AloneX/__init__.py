import pyrogram 
from pyrogram import Client, idle
#from pytgcalls import PyTgCalls
from telegram.ext import Defaults, ApplicationBuilder, Application, PicklePersistence
from motor.motor_asyncio import AsyncIOMotorClient
from telegram import constants
from telegraph.aio import Telegraph
from telethon import TelegramClient
from telethon.sessions import StringSession
from AloneX.helpers.data.fonts import Fonts
from config import *
import time
import logging
import aiohttp
import asyncio
import random
import importlib
import os

LOGGER = logging.getLogger(__name__)
START_TIME = time.time()
FORMAT = f"[Bot] %(message)s"
logging.basicConfig(level=logging.INFO, handlers=[logging.FileHandler('logs.txt'), logging.StreamHandler()], format=FORMAT)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telethon').setLevel(logging.ERROR)
logging.getLogger('pyrogram').setLevel(logging.ERROR)


telegraph = Telegraph(access_token=getenv('TELEGRAPH_TOKEN'), domain="graph.org")
async def telegraph_create():
       await telegraph.create_account(
            short_name=BOT_NAME,
            author_name=BOT_NAME,
            author_url=("https://t.me/"+BOT_USERNAME[1:])
    )
  

db_client = AsyncIOMotorClient(DB_URL)
database = db_client['AloneX']
db2_client = AsyncIOMotorClient(DB_URL2)
database2 = db2_client['AloneX2']

async def send_restart(application: Application) -> None:
    try:
        with open("restart_data.txt", "r") as f:
            data = f.read().strip()
        chat_id, message_id = map(int, data.split(":"))

        await application.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="✅ Alone Bot Restarted Successfully! ✨"
        )
        os.remove("restart_data.txt")  
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Restart edit failed: {e}")
    try:
        if LOGS_CHANNEL:
            await application.bot.send_message(
                chat_id=LOGS_CHANNEL,
                text=f"<b>Alone robot just restarted! ♥️</b>\n\n<b>Time:</b> <code>{time.ctime()}</code>",
                parse_mode=constants.ParseMode.HTML
            )
    except Exception as e:
        print(f"Sending restart log failed: {e}")

from AloneX.helpers.font_helper import apply_custom_font
font = apply_custom_font

ptb_defaults = Defaults(
    parse_mode=constants.ParseMode.MARKDOWN,
    allow_sending_without_reply=True,
    do_quote=True,
)

# PTB Application
app = ApplicationBuilder().defaults(ptb_defaults).token(TOKEN).post_init(send_restart).build()

# Pyrogram Bot Client
pbot = Client("AloneX_pyro_bot", api_id=API_ID, api_hash=API_HASH, bot_token=TOKEN, max_concurrent_transmissions=5)
#pytgcalls = PyTgCalls(user)

# Pyrogram User Client
user = Client("AloneX_pyro_user", api_id=API_ID, api_hash=API_HASH, session_string=USER_STRING, max_concurrent_transmissions=5)

# Telethon Bot Client
tbot = TelegramClient("AloneX_telethon_bot", API_ID, API_HASH)



multi_clients = {}
work_loads = {}
multi_clients[0] = pbot
work_loads[0] = 0

async def start_all_clients():
    await pbot.start()
    LOGGER.info("Pyrogram Bot Started!")
    
    try:
        await user.start()
        LOGGER.info("Pyrogram User Started!")
    except Exception as e:
        LOGGER.warning(f"Pyrogram User not started: {e}")
    
    await tbot.start(bot_token=TOKEN)
    LOGGER.info("Telethon Bot Started!")
    
    #try:
    #    await pytgcalls.start()
    #    LOGGER.info("PyTgCalls Started!")
    #except Exception as e:
    #    LOGGER.error(f'❌ ERROR when starting PyTgCalls: {e}')
    
    LOGGER.info("All Clients Started!")

async def stop_all_clients():
    await pbot.stop()
    await user.stop()
    await tbot.disconnect()
    LOGGER.info("All Clients Stopped!")
     
aiohttpsession = None
process = {}

async def init_aiohttp_session():
    global aiohttpsession
    if aiohttpsession is None or aiohttpsession.closed:
        aiohttpsession = aiohttp.ClientSession()

async def initialize_database():
    from AloneX.db import (
        users, chats, afk, chatbot, ignore, characters,
        riddle, user_characters, autofilter, notes, fsub,
        warn_db, locks_db, antiflood, antiraid, 
        approval_db, filter, sudo, antiremovelink_db,
        joinmute_db, antiforward_db, mediadelete_db, antitag_db,
        ghost_db, nightmode_db, logchannel_db, bio_filter, greetings,
        banall_db
    )
    await users.initialize_db_users()
    await afk.initialize_afk_users()
    await users.initialize_db_premium_users()
    await autofilter.initialize_db_chats()
    await chatbot.initialize_db_chats()
    await ignore.initialize_db_users()
    await notes.initialize_chats()
    await fsub.initialize_chats()
    await riddle.initialize_db_chats()
    await warn_db.initialize_chats()
    await locks_db.initialize_chats()
    await antiflood.initialize_chats()
    await antiraid.initialize_chats()
    await approval_db.initialize_chats()
    await filter.initialize_chats()
    await antiremovelink_db.initialize_chats()
    await joinmute_db.initialize_chats()
    await antiforward_db.initialize_chats()
    await mediadelete_db.initialize_chats()
    await antitag_db.initialize_chats()
    await ghost_db.initialize_chats()
    await nightmode_db.initialize_chats()
    await logchannel_db.initialize_chats()
    await bio_filter.initialize_chats()
    await greetings.initialize_chats()
    await banall_db.initialize_chats()
    await sudo.initialize_cache()
    LOGGER.info(
        "Initialized (All) - [users, chats, riddle, premium, afk, chatbot, blocks, autofilter, notes, fsub, warns, locks, antiflood, antiraid, approvals, filters, sudo, antiremovelink, antitag, joinmute, antiforward, mediadelete, ghost, nightmode, logs, bio, greetings, banall] —» DATABASE"
    )
    if LOGS_CHANNEL:
        try:
            await app.bot.send_message(
                LOGS_CHANNEL,
                f"<b>AloneX Robot has successfully initialized! 🚀</b>\n\n"
                f"<b>Modules:</b> <code>ALL</code>\n"
                f"<b>Database:</b> <code>CONNECTED</code>\n"
                f"<b>Time:</b> <code>{time.ctime()}</code>",
                parse_mode=constants.ParseMode.HTML
            )
        except Exception as e:
            LOGGER.error(f"Failed to send startup log: {e}")
if not hasattr(tbot, "handlers_loaded"):
    tbot.handlers_loaded = set()
