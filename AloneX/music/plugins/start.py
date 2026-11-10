# Copyright (c) 2025 @THECDERQUEEN
# Licensed under the MIT License.
# This file is part of @SHONA_BOTS
#SHONA-DECODER
#
# /start and /help (and the welcome message) are owned by the manage bot. The music panel
# is opened from the "Music" button of the manage bot's start menu (callback: mzpanelopen).
# What stays here is the music-specific bookkeeping and the play-mode settings.

import asyncio

from pyrogram import enums, filters, types

from AloneX.music import app, db, lang, logger
from AloneX.music.helpers import buttons


@app.on_message(filters.command(["start"]), group=5)
async def _register_start(_, message: types.Message):
    """Silently remember users / chats for music stats & broadcast (no reply, the manage bot answers)."""
    try:
        if message.chat.type == enums.ChatType.PRIVATE:
            if message.from_user and not await db.is_user(message.from_user.id):
                await db.add_user(message.from_user.id)
        elif not await db.is_chat(message.chat.id):
            await db.add_chat(message.chat.id)
    except Exception as e:
        logger.error(f"[Start] register failed: {e}")


# "/settings" belongs to the manage bot, so music uses only /playmode.
@app.on_message(filters.command(["playmode"]) & (filters.group | filters.channel) & ~app.bl_users)
@lang.language()
async def settings(_, message: types.Message):
    admin_only = await db.get_play_mode(message.chat.id)
    cmd_delete = await db.get_cmd_delete(message.chat.id)
    _language = await db.get_lang(message.chat.id)
    await message.reply_text(
        text=message.lang["start_settings"].format(message.chat.title),
        reply_markup=buttons.settings_markup(
            message.lang, admin_only, cmd_delete, _language, message.chat.id
        ),
    )


@app.on_message(filters.new_chat_members, group=7)
async def _new_member(_, message: types.Message):
    bot_joined = any(member.id == app.id for member in message.new_chat_members)

    if not bot_joined:
        # keep music-blacklisted users out of groups the bot is in
        try:
            banned_users = await db.get_blacklisted()
        except Exception:
            return
        for member in message.new_chat_members:
            if member.id in banned_users:
                try:
                    await message.chat.ban_member(member.id)
                except Exception:
                    pass
        return

    if message.chat.id in await db.get_blacklisted(True):
        try:
            await message.reply_text("This group is blacklisted from using this bot.")
        except Exception:
            pass
        return await message.chat.leave()

    # the manage bot sends the welcome message; music only registers the chat
    await asyncio.sleep(3)
    if not await db.is_chat(message.chat.id):
        await db.add_chat(message.chat.id)
