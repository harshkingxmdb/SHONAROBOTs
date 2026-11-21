# =======================================================
# Tag-all (good night / good morning) for AloneX (Pyrogram)
# Adapted from Purvi Bots (Im-Notcoder) ©️ 2025-26 All Rights Reserved.
# Use only with permission from the author: DM @TheSigmaCoder
# =======================================================

import asyncio
import random
import re

from pyrogram import filters, enums
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.errors import FloodWait, UserNotParticipant

from AloneX import pbot as app, prefix_cmds

__module__ = "𝐆ɴ-𝐓ᴀɢ🏷️"

__help__ = """
**Good Night / Good Morning Tag 🏷️**

❂ `/gntag` – Tag all members with a good night message (admins).
❂ `/gntag` as a reply – Tag all members as replies to that message (admins).
❂ `/gmtag` – Tag all members with a good morning message (admins).
❂ `/gnstop` or `/gmstop` – Stop a running tag (admins).
"""

BATCH = 5            # members per message
DELAY = 4            # seconds between messages (avoids flood limits)
ACTIVE = set()       # chats where a tag run is in progress

EMOJI = [
    "🦋🦋🦋🦋🦋", "🧚🌸🧋🍬🫖", "🥀🌷🌹🌺💐", "🌸🌿💮🌱🌵", "❤️💚💙💜🖤", "💓💕💞💗💖",
    "🌸💐🌺🌹🦋", "🍔🦪🍛🍲🥗", "🍎🍓🍒🍑🌶️", "🧋🥤🧋🥛🍷", "🍬🍭🧁🎂🍡", "🍨🧉🍺☕🍻",
    "🥪🥧🍦🍥🍚", "🫖☕🍹🍷🥛", "☕🧃🍩🍦🍙", "🍁🌾💮🍂🌿", "🌨️🌥️⛈️🌩️🌧️", "🌷🏵️🌸🌺💐",
    "💮🌼🌻🍀🍁", "🧟🦸🦹🧙👸", "🧅🍠🥕🌽🥦", "🐷🐹🐭🐨🐻‍❄️", "🦋🐇🐀🐈🐈‍⬛", "🌼🌳🌲🌴🌵",
    "🥩🍋🍐🍈🍇", "🍴🍽️🔪🍶🥃", "🕌🏰🏩⛩️🏩", "🎉🎊🎈🎂🎀", "🪴🌵🌴🌳🌲", "🎄🎋🎍🎑🎎",
    "🦅🦜🕊️🦤🦢", "🦤🦩🦚🦃🦆", "🐬🦭🦈🐋🐳", "🐔🐟🐠🐡🦐", "🦩🦀🦑🐙🦪", "🐦🦂🕷️🕸️🐚",
    "🥪🍰🥧🍨🍨", "🥬🍉🧁🧇",
]

GOOD_NIGHT = [
    "**ɢᴏᴏᴅ ɴɪɢʜᴛ 🌚**",
    "**ᴄʜᴜᴘ ᴄʜᴀᴘ sᴏ ᴊᴀ 🙊**",
    "**ᴘʜᴏɴᴇ ʀᴀᴋʜ ᴋᴀʀ sᴏ ᴊᴀ, ɴᴀʜɪ ᴛᴏ ʙʜᴏᴏᴛ ᴀᴀ ᴊᴀʏᴇɢᴀ..👻**",
    "**ᴀᴡᴇᴇ ʙᴀʙᴜ sᴏɴᴀ ᴅɪɴ ᴍᴇɪɴ ᴋᴀʀ ʟᴇɴᴀ ᴀʙʜɪ sᴏ ᴊᴀᴏ..?? 🥲**",
    "**ᴍᴜᴍᴍʏ ᴅᴇᴋʜᴏ ʏᴇ ᴀᴘɴᴇ ɢғ sᴇ ʙᴀᴀᴛ ᴋʀ ʀʜᴀ ʜ ʀᴀᴊᴀɪ ᴍᴇ ɢʜᴜs ᴋᴀʀ, sᴏ ɴᴀʜɪ ʀᴀʜᴀ 😜**",
    "**ᴘᴀᴘᴀ ʏᴇ ᴅᴇᴋʜᴏ ᴀᴘɴᴇ ʙᴇᴛᴇ ᴋᴏ ʀᴀᴀᴛ ʙʜᴀʀ ᴘʜᴏɴᴇ ᴄʜᴀʟᴀ ʀʜᴀ ʜᴀɪ 🤭**",
    "**ᴊᴀɴᴜ ᴀᴀᴊ ʀᴀᴀᴛ ᴋᴀ sᴄᴇɴᴇ ʙɴᴀ ʟᴇ..?? 🌠**",
    "**ɢɴ sᴅ ᴛᴄ.. 🙂**",
    "**ɢᴏᴏᴅ ɴɪɢʜᴛ sᴡᴇᴇᴛ ᴅʀᴇᴀᴍ ᴛᴀᴋᴇ ᴄᴀʀᴇ..?? ✨**",
    "**ʀᴀᴀᴛ ʙʜᴜᴛ ʜᴏ ɢʏɪ ʜᴀɪ sᴏ ᴊᴀᴏ, ɢɴ..?? 🌌**",
    "**ᴍᴜᴍᴍʏ ᴅᴇᴋʜᴏ 11 ʙᴀᴊɴᴇ ᴡᴀʟᴇ ʜᴀɪ ʏᴇ ᴀʙʜɪ ᴛᴀᴋ ᴘʜᴏɴᴇ ᴄʜᴀʟᴀ ʀʜᴀ ɴᴀʜɪ sᴏ ɴᴀʜɪ ʀʜᴀ 🕦**",
    "**ᴋᴀʟ sᴜʙʜᴀ sᴄʜᴏᴏʟ ɴᴀʜɪ ᴊᴀɴᴀ ᴋʏᴀ, ᴊᴏ ᴀʙʜɪ ᴛᴀᴋ ᴊᴀɢ ʀʜᴇ ʜᴏ 🏫**",
    "**ʙᴀʙᴜ, ɢᴏᴏᴅ ɴɪɢʜᴛ sᴅ ᴛᴄ..?? 😊**",
    "**ᴀᴀᴊ ʙʜᴜᴛ ᴛʜᴀɴᴅ ʜᴀɪ, ᴀᴀʀᴀᴍ sᴇ ᴊᴀʟᴅɪ sᴏ ᴊᴀᴛɪ ʜᴏᴏɴ 🌼**",
    "**ᴊᴀɴᴇᴍᴀɴ, ɢᴏᴏᴅ ɴɪɢʜᴛ 🌷**",
    "**ᴍᴇ ᴊᴀ ʀᴀʜɪ sᴏɴᴇ, ɢɴ sᴅ ᴛᴄ 🏵️**",
    "**ʜᴇʟʟᴏ ᴊɪ ɴᴀᴍᴀsᴛᴇ, ɢᴏᴏᴅ ɴɪɢʜᴛ 🍃**",
    "**ʜᴇʏ, ʙᴀʙʏ ᴋᴋʀʜ..? sᴏɴᴀ ɴᴀʜɪ ʜᴀɪ ᴋʏᴀ ☃️**",
    "**ɢᴏᴏᴅ ɴɪɢʜᴛ ᴊɪ, ʙʜᴜᴛ ʀᴀᴀᴛ ʜᴏ ɢʏɪ..? ⛄**",
    "**ᴍᴇ ᴊᴀ ʀᴀʜɪ ʀᴏɴᴇ, ɪ ᴍᴇᴀɴ sᴏɴᴇ ɢᴏᴏᴅ ɴɪɢʜᴛ ᴊɪ 😁**",
    "**ᴍᴀᴄʜʜᴀʟɪ ᴋᴏ ᴋᴇʜᴛᴇ ʜᴀɪ ғɪsʜ, ɢᴏᴏᴅ ɴɪɢʜᴛ ᴅᴇᴀʀ ᴍᴀᴛ ᴋʀɴᴀ ᴍɪss, ᴊᴀ ʀʜɪ sᴏɴᴇ 🌄**",
    "**ɢᴏᴏᴅ ɴɪɢʜᴛ ʙʀɪɢʜᴛғᴜʟʟ ɴɪɢʜᴛ 🤭**",
    "**ᴛʜᴇ ɴɪɢʜᴛ ʜᴀs ғᴀʟʟᴇɴ, ᴛʜᴇ ᴅᴀʏ ɪs ᴅᴏɴᴇ,, ᴛʜᴇ ᴍᴏᴏɴ ʜᴀs ᴛᴀᴋᴇɴ ᴛʜᴇ ᴘʟᴀᴄᴇ ᴏғ ᴛʜᴇ sᴜɴ... 😊**",
    "**ᴍᴀʏ ᴀʟʟ ʏᴏᴜʀ ᴅʀᴇᴀᴍs ᴄᴏᴍᴇ ᴛʀᴜᴇ ❤️**",
    "**ɢᴏᴏᴅ ɴɪɢʜᴛ sᴘʀɪɴᴋʟᴇs sᴡᴇᴇᴛ ᴅʀᴇᴀᴍ 💚**",
    "**ɢᴏᴏᴅ ɴɪɢʜᴛ, ɴɪɴᴅ ᴀᴀ ʀʜɪ ʜᴀɪ 🥱**",
    "**ᴅᴇᴀʀ ғʀɪᴇɴᴅ ɢᴏᴏᴅ ɴɪɢʜᴛ 💤**",
    "**ʙᴀʙʏ ᴀᴀᴊ ʀᴀᴀᴛ ᴋᴀ sᴄᴇɴᴇ ʙɴᴀ ʟᴇ 🥰**",
    "**ɪᴛɴɪ ʀᴀᴀᴛ ᴍᴇ ᴊᴀɢ ᴋᴀʀ ᴋʏᴀ ᴋᴀʀ ʀʜᴇ ʜᴏ sᴏɴᴀ ɴᴀʜɪ ʜᴀɪ ᴋʏᴀ 😜**",
    "**ᴄʟᴏsᴇ ʏᴏᴜʀ ᴇʏᴇs sɴᴜɢɢʟᴇ ᴜᴘ ᴛɪɢʜᴛ,, ᴀɴᴅ ʀᴇᴍᴇᴍʙᴇʀ ᴛʜᴀᴛ ᴀɴɢᴇʟs, ᴡɪʟʟ ᴡᴀᴛᴄʜ ᴏᴠᴇʀ ʏᴏᴜ ᴛᴏɴɪɢʜᴛ... 💫**",
]

GOOD_MORNING = [
    "**ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ, ᴋᴇsᴇ ʜᴏ 🐱**",
    "**ɢᴍ, sᴜʙʜᴀ ʜᴏ ɢʏɪ ᴜᴛʜɴᴀ ɴᴀʜɪ ʜᴀɪ ᴋʏᴀ 🌤️**",
    "**ɢᴍ ʙᴀʙʏ, ᴄʜᴀɪ ᴘɪ ʟᴏ ☕**",
    "**ᴊᴀʟᴅɪ ᴜᴛʜᴏ, sᴄʜᴏᴏʟ ɴᴀʜɪ ᴊᴀɴᴀ ᴋʏᴀ 🏫**",
    "**ɢᴍ, ᴄʜᴜᴘ ᴄʜᴀᴘ ʙɪsᴛᴇʀ sᴇ ᴜᴛʜᴏ ᴠʀɴᴀ ᴘᴀɴɪ ᴅᴀʟ ᴅᴜɴɢɪ 🧊**",
    "**ʙᴀʙʏ ᴜᴛʜᴏ ᴀᴜʀ ᴊᴀʟᴅɪ ғʀᴇsʜ ʜᴏ ᴊᴀᴏ, ɴᴀsᴛᴀ ʀᴇᴀᴅʏ ʜᴀɪ 🫕**",
    "**ᴏғғɪᴄᴇ ɴᴀʜɪ ᴊᴀɴᴀ ᴋʏᴀ ᴊɪ ᴀᴀᴊ, ᴀʙʜɪ ᴛᴀᴋ ᴜᴛʜᴇ ɴᴀʜɪ 🏣**",
    "**ɢᴍ ᴅᴏsᴛ, ᴄᴏғғᴇᴇ/ᴛᴇᴀ ᴋʏᴀ ʟᴏɢᴇ ☕🍵**",
    "**ʙᴀʙʏ 8 ʙᴀᴊɴᴇ ᴡᴀʟᴇ ʜᴀɪ, ᴀᴜʀ ᴛᴜᴍ ᴀʙʜɪ ᴛᴋ ᴜᴛʜᴇ ɴᴀʜɪ 🕖**",
    "**ᴋʜᴜᴍʙʜᴋᴀʀᴀɴ ᴋɪ ᴀᴜʟᴀᴅ ᴜᴛʜ ᴊᴀᴀ... ☃️**",
    "**ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ ʜᴀᴠᴇ ᴀ ɴɪᴄᴇ ᴅᴀʏ... 🌄**",
    "**ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ, ʜᴀᴠᴇ ᴀ ɢᴏᴏᴅ ᴅᴀʏ... 🪴**",
    "**ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ, ʜᴏᴡ ᴀʀᴇ ʏᴏᴜ ʙᴀʙʏ 😇**",
    "**ᴍᴜᴍᴍʏ ᴅᴇᴋʜᴏ ʏᴇ ɴᴀʟᴀʏᴋ ᴀʙʜɪ ᴛᴀᴋ sᴏ ʀʜᴀ ʜᴀɪ... 😵‍💫**",
    "**ʀᴀᴀᴛ ʙʜᴀʀ ʙᴀʙᴜ sᴏɴᴀ ᴋʀ ʀʜᴇ ᴛʜᴇ ᴋʏᴀ, ᴊᴏ ᴀʙʜɪ ᴛᴋ sᴏ ʀʜᴇ ʜᴏ ᴜᴛʜɴᴀ ɴᴀʜɪ ʜᴀɪ ᴋʏᴀ... 😏**",
    "**ʙᴀʙᴜ ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ ᴜᴛʜ ᴊᴀᴏ ᴀᴜʀ ɢʀᴏᴜᴘ ᴍᴇ sᴀʙ ғʀɪᴇɴᴅs ᴋᴏ ɢᴍ ᴡɪsʜ ᴋʀᴏ... 🌟**",
    "**ᴘᴀᴘᴀ ʏᴇ ᴀʙʜɪ ᴛᴀᴋ ᴜᴛʜ ɴᴀʜɪ, sᴄʜᴏᴏʟ ᴋᴀ ᴛɪᴍᴇ ɴɪᴋᴀʟᴛᴀ ᴊᴀ ʀʜᴀ ʜᴀɪ... 🥲**",
    "**ᴊᴀɴᴇᴍᴀɴ ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ, ᴋʏᴀ ᴋʀ ʀʜᴇ ʜᴏ ... 😅**",
    "**ɢᴍ ʙᴇᴀsᴛɪᴇ, ʙʀᴇᴀᴋғᴀsᴛ ʜᴜᴀ ᴋʏᴀ... 🍳**",
    "**ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ, ᴀʙʜɪ ᴛᴋ ʙɪsᴛᴇʀ ᴘᴇ ʜɪ ᴘᴀᴅʼᴇ ʜᴏ 😴**",
    "**ᴊᴀɢᴏ ʙʜᴀɪ ᴊᴀɢᴏ, ᴅᴇsʜ ᴋᴏ ᴛᴜᴍʜᴀʀɪ ᴢᴀʀᴜʀᴀᴛ ʜᴀɪ 🤓**",
    "**ᴀʙʜɪ ᴛᴋ sᴏ ʀʜᴇ ʜᴏ ᴋʏᴀ, ᴍᴇʜɴᴛɪ ᴋᴀᴍᴀɴᴇ ɴᴀʜɪ ᴊᴀɴᴀ ᴋʏᴀ 💸**",
    "**ʙᴀʙᴜ ʙɪsᴛᴇʀ sᴇ ᴜᴛʜ ᴊᴀᴏ, ɴᴀʜɪ ᴛᴏ ᴘʀᴏᴘᴇʀᴛʏ ᴘᴀᴘᴀ ᴋᴇ ɴᴀᴀᴍ ʜᴏ ᴊᴀʏᴇɢɪ 😏**",
    "**ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ, ᴋʏᴀ ᴀᴊ ᴘʜɪʀ ᴄʟᴀss ᴍᴇ ʟᴀᴛᴇ ʜᴏɢᴇ 😂**",
    "**ᴜᴛʜᴏ ᴊɪ, ᴍᴏʙɪʟᴇ ᴄʜᴀʀɢᴇʀ ᴋʀᴛᴇ ʀʜᴏ ᴀᴜʀ ᴋʜᴜᴅ ʙᴀᴛᴛᴇʀʏ ᴋʜᴀᴛᴀᴍ ᴋᴀʀᴛᴇ ʀʜᴏ 🔋**",
    "**ʙᴇᴛᴀ ᴊᴀɢᴏ, ɴᴀʜɪ ᴛᴏ ʙᴏss ɴᴏᴛɪᴄᴇ ʟɪᴋʜ ᴅᴇɢᴀ 📄**",
    "**ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ ʙᴇʜᴇɴᴊɪ, ᴀᴊ ʙʜɪ ᴀʟᴀʀᴍ ᴋᴇ sᴀᴀᴛʜ ʟᴀᴅᴀɪ ʜᴀᴀʀ ɢʏᴇ 🛏️**",
    "**ᴀʙʜɪ ᴜᴛʜᴏ ɴᴀʜɪ ᴛᴏ ᴍᴀᴍᴍɪ ᴋɪ ᴄʜᴀᴘᴘᴀʟ ᴜᴛʜ ᴊᴀʏᴇɢɪ 🩴**",
    "**ᴊᴀɢ ᴊᴀᴀᴏ ᴅᴏsᴛ, ᴀᴊ ᴘʜɪʀ ᴏɴʟɪɴᴇ ᴄʟᴀss ᴍᴇ ᴄᴀᴍᴇʀᴀ ᴏғғ ᴋᴀʀ ᴋᴇ sᴏɴᴀ ʜᴀɪ ᴋʏᴀ 💻**",
    "**ᴜᴛʜᴏ ᴊᴀɴᴇᴍᴀɴ, ᴘᴇᴛʜ ᴋᴇ ᴄʜᴀᴠᴀʟ ʙʜɪ ʙʜᴏᴏᴋʜᴇ ʜᴀɪ 🐕**",
    "**ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ, ʙᴀᴛʜʀᴏᴏᴍ ᴋɪ ʟɪɴᴇ ʟᴀɢ ɢʏɪ ʜᴀɪ 🚿**",
    "**ʙᴀʙʏ, ᴊᴀʟᴅɪ ᴜᴛʜᴏ, ɴᴀʜɪ ᴛᴏ ʀᴏᴛɪ ʙʜɪ ᴛᴜᴍʜᴀʀɪ ᴛᴀʀᴀʜ ʜᴀʀᴅ ʜᴏ ᴊᴀʏᴇɢɪ 🍪**",
    "**ᴊᴀɢᴏ ʙʀᴏ, ᴀᴊ ʙʜɪ ᴋᴏʟʜᴀᴘᴜʀɪ ᴄʜᴀᴘᴘᴀʟ ᴋᴇ sᴀᴡᴀᴀᴅ ᴀᴜʀ ᴀʟᴀʀᴍ ᴋᴇ ᴡᴀᴊᴀʜ sᴇ ᴜᴛʜᴇ ɴᴀ? 🩴⏰**",
    "**ʙᴏʟᴏ ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ, ɴᴀʜɪ ᴛᴏ ᴍᴀᴍᴍɪ ᴋʜᴀɴᴀ ɴᴀʜɪ ᴅᴇɴɢɪ 🍲**",
    "**ᴘʀɪɴᴄᴇss ᴜᴛʜᴏ, ʀᴀᴊᴋᴜᴍᴀʀ ʙᴀʜᴀʀ ʙᴇᴄʜᴀʀᴀ ɪɴᴛᴢᴀᴀʀ ᴋᴀʀ ʀʜᴀ ʜᴀɪ 👑**",
    "**ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ ᴘᴀɢʟᴇ, ᴊᴀᴀɴ ᴜᴛʜ ɢʏɪ ᴛᴏ ᴛᴜᴍʜᴀʀᴀ ᴍᴏᴏᴅ ʙʜɪ ᴏɴ ʜᴏ ᴊᴀʏᴇɢᴀ 😜**",
    "**ᴅᴏsᴛ ᴀᴊ ᴅɪɴ ʙʜᴀʀ ᴏɴʟʏ ᴏɴʟɪɴᴇ ᴄʜᴀᴛ ᴋᴀʀɴᴀ ʜᴀɪ ᴋʏᴀ, ᴘᴇʜʟᴇ ᴜᴛʜᴏ ᴛᴏ sᴀʜɪ 😏**",
]

_BAD_CHARS = re.compile(r"[\[\]\(\)\*_`]")


def _display(user) -> str:
    name = _BAD_CHARS.sub("", (user.first_name or "User").strip()) or "User"
    return f"[{name}](tg://user?id={user.id})"


async def _is_admin(client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except (UserNotParticipant, Exception):
        return False


async def _send(client, chat_id: int, text: str, reply_to: int = None):
    while True:
        try:
            if reply_to:
                return await client.send_message(chat_id, text, reply_to_message_id=reply_to)
            return await client.send_message(chat_id, text)
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)


async def _tag_run(client, chat_id: int, closing: str = None, reply_to: int = None):
    """Mention every human member, BATCH per message, until done or stopped with /gnstop or /gmstop."""
    batch = []
    try:
        async for member in client.get_chat_members(chat_id):
            if chat_id not in ACTIVE:
                break
            user = member.user
            if not user or user.is_bot or user.is_deleted:
                continue
            batch.append(_display(user))
            if len(batch) == BATCH:
                text = " ".join(batch) + (f" {closing}" if closing else "")
                await _send(client, chat_id, text, reply_to)
                batch = []
                await asyncio.sleep(DELAY)
        if batch and chat_id in ACTIVE:
            text = " ".join(batch) + (f" {closing}" if closing else "")
            await _send(client, chat_id, text, reply_to)
    except Exception as e:
        print(f"[gntag] stopped in {chat_id}: {type(e).__name__}: {e}")
    finally:
        ACTIVE.discard(chat_id)


async def _start(message, client, pool: list, reply_mode: bool):
    chat_id = message.chat.id
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply("**⬤ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴏɴʟʏ ғᴏʀ ɢʀᴏᴜᴘs.**")
    if not message.from_user or not await _is_admin(client, chat_id, message.from_user.id):
        return await message.reply("**⬤ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ʙᴀʙʏ, ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴛᴀɢ ᴍᴇᴍʙᴇʀs.**")
    if chat_id in ACTIVE:
        return await message.reply("**⬤ ᴘʟᴇᴀsᴇ ᴀᴛ ғɪʀsᴛ sᴛᴏᴘ ʀᴜɴɴɪɴɢ ᴍᴇɴᴛɪᴏɴ ᴘʀᴏᴄᴇss... (/gnstop)**")

    reply_to = None
    if reply_mode:
        if not message.reply_to_message:
            return await message.reply("**⬤ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇssᴀɢᴇ ᴛᴏ ᴛᴀɢ ᴍᴇᴍʙᴇʀs ᴀs ʀᴇᴘʟɪᴇs.**")
        reply_to = message.reply_to_message.id
        closing = None
    else:
        closing = random.choice(pool)

    ACTIVE.add(chat_id)
    asyncio.create_task(_tag_run(client, chat_id, closing=closing, reply_to=reply_to))


@app.on_message(filters.command(["gntag"], prefixes=prefix_cmds) & filters.group)
async def gntag_cmd(client, message):
    # plain /gntag -> good night tag; /gntag as a reply -> tag as replies to that message
    await _start(message, client, GOOD_NIGHT, reply_mode=bool(message.reply_to_message))


@app.on_message(filters.command(["gmtag"], prefixes=prefix_cmds) & filters.group)
async def gmtag_cmd(client, message):
    await _start(message, client, GOOD_MORNING, reply_mode=False)


@app.on_message(filters.command(["gnstop", "gmstop"], prefixes=prefix_cmds) & filters.group)
async def stop_tag(client, message):
    chat_id = message.chat.id
    if chat_id not in ACTIVE:
        return await message.reply("**⬤ ᴄᴜʀʀᴇɴᴛʟʏ ɪ'ᴍ ɴᴏᴛ ᴛᴀɢɢɪɴɢ ʙᴀʙʏ.**")
    if not message.from_user or not await _is_admin(client, chat_id, message.from_user.id):
        return await message.reply("**⬤ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ʙᴀʙʏ, ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ sᴛᴏᴘ ɪᴛ.**")
    ACTIVE.discard(chat_id)
    await message.reply("**♥︎ ᴛᴀɢ sᴛᴏᴘᴘᴇᴅ.**")
