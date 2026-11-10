# Copyright (c) 2025 @THECDERQUEEN
# Licensed under the MIT License.
# This file is part of @SHONA_BOTS
#SHONA-DECODER

import asyncio

from pyrogram import filters, types

from AloneX.music import app, db, lang
from AloneX.music.helpers import can_manage_vc

DELETE_DELAY = 7
MAX_LOOP = 20


async def _delete_later(message: types.Message) -> None:
    try:
        await asyncio.sleep(DELETE_DELAY)
        await message.delete()
    except Exception:
        pass


@app.on_message(filters.command(["loop"]) & filters.group & ~app.bl_users)
@can_manage_vc
async def _loop(_, m: types.Message):
    chat_lang = await lang.get_lang(m.chat.id)

    if len(m.command) < 2:
        current = await db.get_loop(m.chat.id)
        state = f"✅ {current}" if current else "❌ off"
        msg = await m.reply_text(
            chat_lang.get(
                "loop_status",
                "🔁 Loop Status: {0}\n\nUsage: /loop [count|off]",
            ).format(state)
        )
        asyncio.create_task(_delete_later(msg))
        return

    arg = m.command[1].lower()

    if arg in ("off", "disable", "0"):
        await db.set_loop(m.chat.id, 0)
        msg = await m.reply_text(
            chat_lang.get("loop_disabled", "🚫 Loop disabled.")
        )
        asyncio.create_task(_delete_later(msg))
        return

    if not arg.isdigit():
        msg = await m.reply_text(
            chat_lang.get("loop_usage", "Usage: /loop [count|off]")
        )
        asyncio.create_task(_delete_later(msg))
        return

    count = int(arg)
    if count < 1 or count > MAX_LOOP:
        msg = await m.reply_text(
            chat_lang.get(
                "loop_limit",
                f"Please pick a number between 1 and {MAX_LOOP}.",
            )
        )
        asyncio.create_task(_delete_later(msg))
        return

    await db.set_loop(m.chat.id, count)
    msg = await m.reply_text(
        chat_lang.get(
            "loop_enabled",
            "🔁 Loop enabled — current song will repeat {0} more time(s).",
        ).format(count)
    )
    asyncio.create_task(_delete_later(msg))
