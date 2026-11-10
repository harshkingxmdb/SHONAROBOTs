from pyrogram import filters
from AloneX import pbot, font
from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URL, DB_URL2, DEV_LIST

db_client = AsyncIOMotorClient(DB_URL)
database = db_client["AloneX"]

db2_client = AsyncIOMotorClient(DB_URL2)
database2 = db2_client["AloneX2"]


@pbot.on_message(filters.command("resetdb") & filters.user(DEV_LIST), group=-398)
async def resetdb_request(_, message):
    await message.reply_text(
        "⚠️ Are you sure you want to reset **ALL DATABASES**?\n"
        "This will delete all data permanently!\n\n"
        "Type `/confirmreset` to continue."
    )



@pbot.on_message(filters.command("confirmreset") & filters.user(DEV_LIST))
async def resetdb_confirm(_, message):
    # Reset first DB
    collections1 = await database.list_collection_names()
    for col in collections1:
        await database[col].delete_many({})

    # Reset second DB
    collections2 = await database2.list_collection_names()
    for col in collections2:
        await database2[col].delete_many({})

    await message.reply_text(font("✅ Both databases (`AloneX` & `AloneX2`) have been fully reset!"))
