# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic
#ALONE-CODER
#
# /restart and /logs are provided by the manage bot (they restart / dump the whole process,
# music included), so only the music-specific /logger toggle lives here.

from pyrogram import filters, types

from AloneX.music import app, db, lang


@app.on_message(filters.command(["logger"]) & app.sudoers)
@lang.language()
async def _logger(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))
    if m.command[1] not in ("on", "off"):
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))

    if m.command[1] == "on":
        await db.set_logger(True)
        await m.reply_text(m.lang["logger_on"])
    else:
        await db.set_logger(False)
        await m.reply_text(m.lang["logger_off"])
