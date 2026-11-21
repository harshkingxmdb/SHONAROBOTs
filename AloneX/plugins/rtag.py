# =======================================================
# Tag-all (/rtag, /vctag) for AloneX (Pyrogram)
# Adapted from Purvi Bots (Im-Notcoder) ©️ 2025-26 All Rights Reserved.
# Use only with permission from the author: DM @TheSigmaCoder
# /tagall and @all are handled by tagall.py, so they are not registered here.
# =======================================================

import asyncio
import random

from pyrogram import filters, enums
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.errors import FloodWait, UserNotParticipant

from AloneX import pbot as app, prefix_cmds

__module__ = "𝐑-𝐓ᴀɢ🔔"

__help__ = """
**Tag Members 🔔**

❂ `/rtag` – Tag all members with a random message (admins).
❂ `/rtag` as a reply – Tag all members as replies to that message (admins).
❂ `/vctag` – Ask all members to join the voice chat (admins).
❂ `/rstop`, `/tagstop`, `/vcstop` or `/tagoff` – Stop a running tag (admins).
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

TAGMES = [
    "**ʜᴇʏ ʙᴀʙʏ ᴋᴀʜᴀ ʜᴏ 🤗**",
    "**ᴏʏᴇ sᴏ ɢʏᴇ ᴋʏᴀ ᴏɴʟɪɴᴇ ᴀᴀᴏ 😊**",
    "**ᴠᴄ ᴄʜᴀʟᴏ ʙᴀᴛᴇɴ ᴋᴀʀᴛᴇ ʜᴀɪɴ ᴋᴜᴄʜ ᴋᴜᴄʜ 😃**",
    "**ᴋʜᴀɴᴀ ᴋʜᴀ ʟɪʏᴇ ᴊɪ..?? 🥲**",
    "**ɢʜᴀʀ ᴍᴇ sᴀʙ ᴋᴀɪsᴇ ʜᴀɪɴ ᴊɪ 🥺**",
    "**ᴘᴛᴀ ʜᴀɪ ʙᴏʜᴏᴛ ᴍɪss ᴋᴀʀ ʀʜɪ ᴛʜɪ ᴀᴀᴘᴋᴏ 🤭**",
    "**ᴏʏᴇ ʜᴀʟ ᴄʜᴀʟ ᴋᴇsᴀ ʜᴀɪ..?? 🤨**",
    "**ᴍᴇʀɪ ʙʜɪ sᴇᴛᴛɪɴɢ ᴋᴀʀʙᴀ ᴅᴏɢᴇ..?? 🙂**",
    "**ᴀᴀᴘᴋᴀ ɴᴀᴍᴇ ᴋʏᴀ ʜᴀɪ..?? 🥲**",
    "**ɴᴀsᴛᴀ ʜᴜᴀ ᴀᴀᴘᴋᴀ..?? 😋**",
    "**ᴍᴇʀᴇ ᴋᴏ ᴀᴘɴᴇ ɢʀᴏᴜᴘ ᴍᴇ ᴋɪᴅɴᴀᴘ ᴋʀ ʟᴏ 😍**",
    "**ᴀᴀᴘᴋɪ ᴘᴀʀᴛɴᴇʀ ᴀᴀᴘᴋᴏ ᴅʜᴜɴᴅ ʀʜᴇ ʜᴀɪɴ ᴊʟᴅɪ ᴏɴʟɪɴᴇ ᴀʏɪᴀᴇ 😅**",
    "**ᴍᴇʀᴇ sᴇ ᴅᴏsᴛɪ ᴋʀᴏɢᴇ..?? 🤔**",
    "**ᴏʏᴇ ᴘᴀɢᴀʟ ᴏɴʟɪɴᴇ ᴀᴀ ᴊᴀ 😶**",
    "**ᴀᴀᴊ ʜᴏʟɪᴅᴀʏ ʜᴀɪ ᴋʏᴀ sᴄʜᴏᴏʟ ᴍᴇ..?? 🤔**",
    "**ᴏʏᴇ ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ 😜**",
    "**sᴜɴᴏ ᴇᴋ ᴋᴀᴍ ʜᴀɪ ᴛᴜᴍsᴇ 🙂**",
    "**ᴋᴏɪ sᴏɴɢ ᴘʟᴀʏ ᴋʀᴏ ɴᴀ 😪**",
    "**ɴɪᴄᴇ ᴛᴏ ᴍᴇᴇᴛ ᴜʜ ☺**",
    "**ᴍᴇʀᴀ ʙᴀʙᴜ ɴᴇ ᴛʜᴀɴᴀ ᴋʜᴀʏᴀ ᴋʏᴀ..? 🙊**",
    "**sᴛᴜᴅʏ ᴄᴏᴍᴘʟᴇᴛᴇ ʜᴜᴀ?? 😺**",
    "**ʙᴏʟᴏ ɴᴀ ᴋᴜᴄʜ ʏʀʀ 🥲**",
    "**sᴏɴᴀʟɪ ᴋᴏɴ ʜᴀɪ...?? 😅**",
    "**ᴛᴜᴍʜᴀʀɪ ᴇᴋ ᴘɪᴄ ᴍɪʟᴇɢɪ..? 😅**",
    "**ᴍᴜᴍᴍʏ ᴀᴀ ɢʏɪ ᴋʏᴀ 😆**",
    "**ᴏʀ ʙᴀᴛᴀᴏ ʙʜᴀʙʜɪ ᴋᴀɪsɪ ʜᴀɪ 😉**",
    "**ɪ ʟᴏᴠᴇ ʏᴏᴜ 💚**",
    "**ᴅᴏ ʏᴏᴜ ʟᴏᴠᴇ ᴍᴇ..? 👀**",
    "**ʀᴀᴋʜɪ ᴋᴀʙ ʙᴀɴᴅ ʀᴀʜɪ ʜᴏ..?? 🙉**",
    "**ᴇᴋ sᴏɴɢ sᴜɴᴀᴜ..? 😹**",
    "**ᴏɴʟɪɴᴇ ᴀᴀ ᴊᴀ ʀᴇ sᴏɴɢ sᴜɴᴀ ʀᴀʜɪ ʜᴜ 😻**",
    "**ɪɴsᴛᴀɢʀᴀᴍ ᴄʜᴀʟᴀᴛᴇ ʜᴏ..?? 🙃**",
    "**ᴡʜᴀᴛsᴀᴘᴘ ɴᴜᴍʙᴇʀ ᴅᴏɢᴇ ᴀᴘɴᴀ ᴛᴜᴍ..? 😕**",
    "**ᴛᴜᴍʜᴇ ᴋᴏɴ sᴀ ᴍᴜsɪᴄ sᴜɴɴᴀ ᴘᴀsᴀɴᴅ ʜᴀɪ..? 🙃**",
    "**sᴀʀᴀ ᴋᴀᴍ ᴋʜᴀᴛᴀᴍ ʜᴏ ɢʏᴀ ᴀᴀᴘᴋᴀ..? 🙃**",
    "**ᴋᴀʜᴀ sᴇ ʜᴏ ᴀᴀᴘ 😊**",
    "**sᴜɴᴏ ɴᴀ 🧐**",
    "**ᴍᴇʀᴀ ᴇᴋ ᴋᴀᴀᴍ ᴋᴀʀ ᴅᴏɢᴇ..? ♥️**",
    "**ʙʏ ᴛᴀᴛᴀ ᴍᴀᴛ ʙᴀᴀᴛ ᴋᴀʀɴᴀ ᴀᴀᴊ ᴋᴇ ʙᴀᴅ 😠**",
    "**ᴍᴏᴍ ᴅᴀᴅ ᴋᴀɪsᴇ ʜᴀɪɴ..? ❤**",
    "**ᴋʏᴀ ʜᴜᴀ..? 🤔**",
    "**ʙᴏʜᴏᴛ ʏᴀᴀᴅ ᴀᴀ ʀʜɪ ʜᴀɪ 😒**",
    "**ʙʜᴜʟ ɢʏᴇ ᴍᴜᴊʜᴇ 😏**",
    "**ᴊᴜᴛʜ ɴʜɪ ʙᴏʟɴᴀ ᴄʜᴀʜɪʏᴇ 🤐**",
    "**ᴋʜᴀ ʟᴏ ʙʜᴀᴡ ᴍᴀᴛ ᴋʀᴏ ʙᴀᴀᴛ 😒**",
    "**ᴋʏᴀ ʜᴜᴀ 😮**",
    "**ʜɪɪ ʜᴏɪ ʜᴇʟʟᴏ 👀**",
    "**ᴀᴀᴘᴋᴇ ᴊᴀɪsᴀ ᴅᴏsᴛ ʜᴏ sᴀᴛʜ ᴍᴇ ғɪʀ ɢᴜᴍ ᴋɪs ʙᴀᴀᴛ ᴋᴀ 🙈**",
    "**ᴀᴀᴊ ᴍᴇ sᴀᴅ ʜᴏᴏɴ ☹️**",
    "**ᴍᴜsᴊʜsᴇ ʙʜɪ ʙᴀᴀᴛ ᴋᴀʀ ʟᴏ ɴᴀ 🥺**",
    "**ᴋʏᴀ ᴋᴀʀ ʀᴀʜᴇ ʜᴏ 👀**",
    "**ᴋʏᴀ ʜᴀʟ ᴄʜᴀʟ ʜᴀɪ 🙂**",
    "**ᴋᴀʜᴀ sᴇ ʜᴏ ᴀᴀᴘ..?🤔**",
    "**ᴄʜᴀᴛᴛɪɴɢ ᴋᴀʀ ʟᴏ ɴᴀ..🥺**",
    "**ᴍᴇ ᴍᴀsᴏᴏᴍ ʜᴜ ɴᴀ 🥺**",
    "**ᴋᴀʟ ᴍᴀᴊᴀ ᴀʏᴀ ᴛʜᴀ ɴᴀ 😅**",
    "**ɢʀᴏᴜᴘ ᴍᴇ ʙᴀᴀᴛ ᴋʏᴜ ɴᴀʜɪ ᴋᴀʀᴛᴇ ʜᴏ 😕**",
    "**ᴀᴀᴘ ʀᴇʟᴀᴛɪᴏɴsʜɪᴘ ᴍᴇ ʜᴏ..? 👀**",
    "**ᴋɪᴛɴᴀ ᴄʜᴜᴘ ʀᴀʜᴛᴇ ʜᴏ ʏʀʀ 😼**",
    "**ᴀᴀᴘᴋᴏ ɢᴀɴᴀ ɢᴀɴᴇ ᴀᴀᴛᴀ ʜᴀɪ..? 😸**",
    "**ɢʜᴜᴍɴᴇ ᴄʜᴀʟᴏɢᴇ..?? 🙈**",
    "**ᴋʜᴜs ʀᴀʜᴀ ᴋᴀʀᴏ 🤞**",
    "**ʜᴀᴍ ᴅᴏsᴛ ʙᴀɴ sᴀᴋᴛᴇ ʜᴀɪ...? 🥰**",
    "**ᴋᴜᴄʜ ʙᴏʟ ᴋʏᴜ ɴʜɪ ʀᴀʜᴇ ʜᴏ.. 🥺**",
    "**ᴋᴜᴄʜ ᴍᴇᴍʙᴇʀs ᴀᴅᴅ ᴋᴀʀ ᴅᴏ 🥲**",
    "**sɪɴɢʟᴇ ʜᴏ ʏᴀ ᴍɪɴɢʟᴇ 😉**",
    "**ᴀᴀᴏ ᴘᴀʀᴛʏ ᴋᴀʀᴛᴇ ʜᴀɪɴ 🥳**",
    "**ᴍᴜᴊʜᴇ ʙʜᴜʟ ɢʏᴇ ᴋʏᴀ 🥺**",
    "**ᴛʀᴜᴛʜ ᴀɴᴅ ᴅᴀʀᴇ ᴋʜᴇʟᴏɢᴇ..? 😊**",
    "**ᴀᴀᴊ ᴍᴜᴍᴍʏ ɴᴇ ᴅᴀᴛᴀ ʏʀʀ 🥺**",
    "**ᴇᴋ ᴅɪʟ ʜᴀɪ ᴇᴋ ᴅɪʟ ʜɪ ᴛᴏ ʜᴀɪ 😗**",
    "**ᴛᴜᴍʜᴀʀᴇ ᴅᴏsᴛ ᴋᴀʜᴀ ɢʏᴇ 🥺**",
    "**ᴋᴀʜᴀ ᴋʜᴏʏᴇ ʜᴏ ᴊᴀᴀɴ 😜**",
    "**ɢᴏᴏᴅ ɴɪɢʜᴛ ᴊɪ ʙʜᴜᴛ ʀᴀᴛ ʜᴏ ɢʏɪ 🥰**",
]

VC_TAG = [
    "**ᴏʏᴇ ᴠᴄ ᴀᴀᴏ ɴᴀ ᴘʟs 😒**",
    "**ᴊᴏɪɴ ᴠᴄ ғᴀsᴛ ɪᴛs ɪᴍᴘᴏʀᴛᴀɴᴛ 😐**",
    "**ʙᴀʙʏ ᴄᴏᴍᴇ ᴏɴ ᴠᴄ ғᴀsᴛ 🙄**",
    "**ᴄʜᴜᴘ ᴄʜᴀᴘ ᴠᴄ ᴘʀ ᴀᴀᴏ 🤫**",
    "**ᴍᴀɪɴ ᴠᴄ ᴍᴇ ᴛᴜᴍᴀʀᴀ ᴡᴀɪᴛ ᴋʀ ʀʜɪ 🥺**",
    "**ᴠᴄ ᴘᴀʀ ᴀᴀᴏ ʙᴀᴀᴛ ᴋʀᴛᴇ ʜᴀɪ ☺️**",
    "**ʙᴀʙᴜ ᴠᴄ ᴀᴀ ᴊᴀɪʏᴇ ᴇᴋ ʙᴀʀ 🤨**",
    "**ᴠᴄ ᴘᴀʀ ʏᴇ ʀᴜssɪᴀɴ ᴋʏᴀ ᴋᴀʀ ʀʜɪ ʜᴀɪ 😮‍💨**",
    "**ᴠᴄ ᴘᴀʀ ᴀᴀᴏ ᴠᴀʀɴᴀ ʙᴀɴ ʜᴏ ᴊᴀᴏɢᴇ 🤭**",
    "**sᴏʀʀʏ ʙᴀʙʏ ᴘʟs ᴠᴄ ᴀᴀ ᴊᴀᴏ ɴᴀ 😢**",
    "**ᴠᴄ ᴀᴀɴᴀ ᴇᴋ ᴄʜɪᴊ ᴅɪᴋʜᴀᴛɪ ʜᴜ 😮**",
    "**ᴠᴄ ᴍᴇ ᴄʜᴇᴄᴋ ᴋʀᴋᴇ ʙᴀᴛᴀɴᴀ ᴋᴏɴ sᴀ sᴏɴɢ ᴘʟᴀʏ ʜᴏ ʀʜᴀ ʜᴀɪ.. 💫**",
    "**ᴠᴄ ᴊᴏɪɴ ᴋʀɴᴇ ᴍᴇ ᴋʏᴀ ᴊᴀᴛᴀ ʜᴀɪ ᴛʜᴏʀᴀ ᴅᴇʀ ᴋᴀʀ ʟᴏ ɴᴀ 😇**",
    "**ᴊᴀɴᴇᴍᴀɴ ᴠᴄ ᴀᴀᴏ ɴᴀ ʟɪᴠᴇ sʜᴏᴡ ᴅɪᴋʜᴀᴛɪ ʜᴏᴏɴ.. 😵‍💫**",
    "**ᴏᴡɴᴇʀ ʙᴀʙᴜ ᴠᴄ ᴛᴀᴘᴋᴏ ɴᴀ... 😕**",
    "**ʜᴇʏ ᴄᴜᴛɪᴇ ᴠᴄ ᴀᴀɴᴀ ᴛᴏ ᴇᴋ ʙᴀᴀʀ... 🌟**",
    "**ᴠᴄ ᴘᴀʀ ᴀᴀ ʀʜᴇ ʜᴏ ʏᴀ ɴᴀ... ✨**",
    "**ᴠᴄ ᴘᴀʀ ᴀᴀ ᴊᴀ ᴠʀɴᴀ ɢʜᴀʀ sᴇ ᴜᴛʜᴡᴀ ᴅᴜɴɢɪ... 🌝**",
    "**ʙᴀʙʏ ᴠᴄ ᴘᴀʀ ᴋʙ ᴀᴀ ʀʜᴇ ʜᴏ. 💯**",
    "**ᴍᴇʀɪ ᴊᴀᴀɴ ᴠᴄ ᴀᴀᴋᴇ ᴍᴜᴊʜᴇ ᴅᴇᴋʜ ʟᴏ 🥰**",
    "**ᴄʜᴀʟᴏ ᴠᴄ ᴍᴇ ʙᴇʟᴀᴛᴇ ᴘᴜʀᴀ ʙᴏʀɪɴɢ ʜᴏ ʀʜᴀ 🤐**",
    "**ᴊᴏ ɴᴀ ᴀʏᴇ ᴠᴄ ᴍᴇ ᴜsᴋᴏ ʙʟᴏᴄᴋ 😈**",
    "**ᴠᴄ ᴘᴀʀ ᴀᴀᴏ ɴᴀ ᴍᴇʀɪ ɴɪᴅ ᴄʜᴏʀ ʜᴏ ɢʏɪ 😵**",
    "**ᴄʜᴀʟᴏ ᴠᴄ ᴍᴇ ʀᴏᴍᴀɴᴛɪᴄ ᴍᴏᴏᴅ ʙᴀɴᴀᴛᴇ ʜᴀɪ 😳**",
    "**ᴏʏᴇ ᴠᴄ ᴀᴀ ᴊᴀʟᴅɪ ɴᴀʜɪ ᴛᴏ ᴛʜᴀᴘᴘᴀᴅ 😡**",
    "**ᴠᴄ ᴘʀ ʙᴇʟᴀᴛᴇ ᴍᴏᴠɪᴇ ᴅᴇᴋʜᴛᴇ ʜᴀɪ 🎬**",
    "**ᴠᴄ ᴍᴇ ᴋᴏʏɪ sᴜʀᴘʀɪsᴇ ᴅᴇɴᴀ ʜᴀɪ ᴛᴜᴍʜᴇ 🎁**",
    "**ᴠᴄ ᴘᴀʀ ʜɪ ᴀᴀᴊ ᴋᴀ ᴅᴇᴠɪʟ ᴍᴏᴅᴇ ᴅᴇᴋʜᴇɴɢᴇ 😈**",
    "**ʙᴀʙᴜ ᴠᴄ ᴍᴇ ᴋʜᴀs ʙᴀᴀᴛ ᴋʀɴɪ ʜᴀɪ 💌**",
    "**ᴊᴀʟᴅɪ ᴀᴏ ɴᴀ ᴠᴄ ᴍᴇ, ᴡᴀɪᴛ ɴᴀʜɪ ʜᴏ ʀʜᴀ 😔**",
    "**ᴠᴄ ᴘʀ ᴍᴇʀɪ sɪɴɢɪɴɢ sᴜɴᴏɢᴇ ᴀᴊ 🤭**",
    "**ᴛᴜᴍʜᴀʀᴀ ғᴀᴠᴏᴜʀɪᴛᴇ sᴏɴɢ ʟɢᴀ ʀʜɪ ᴠᴄ ᴍᴇ 🎶**",
    "**ᴠᴄ ᴀᴀᴏ ɴᴀ, ᴇᴋ sᴇᴄʀᴇᴛ ʙᴀᴛᴀᴛɪ ʜᴜ 🤫**",
    "**ᴊᴏɪɴ ᴠᴄ ᴘʀ ᴠᴀʀɴᴀ ᴍᴇ sᴜʟᴋ ʜᴏ ᴊᴀᴜɴɢɪ 😞**",
    "**ᴠᴄ ᴘʀ ᴀᴀᴏ, ᴇᴋ ɴᴇᴡ ᴍᴇᴍᴇ ʙᴀɴᴀɴᴀ ʜᴀɪ 😂**",
    "**ᴠᴄ ᴍᴇ ᴛᴜᴍʜᴀʀɪ ғᴀᴠᴏ ɢᴀʟɪ ᴅᴇᴛɪ ʜᴜ 🤬**",
    "**ᴏʏᴇ ᴠᴄ ᴀᴀ, ᴍᴇʀɪ ʀᴏᴍᴀɴᴛɪᴄ ᴘᴏᴇᴍ sᴜɴᴏ 🌹**",
    "**ᴠᴄ ᴍᴇ ʀᴏᴍᴀɴᴛɪᴄ ᴅᴊ ᴘᴀʀᴛʏ ʜᴏ ʀʜɪ 💃**",
    "**ᴠᴄ ᴀᴀᴏ ɴᴀ, ʙᴀᴄʜᴘᴀɴ ᴋɪ sᴛᴏʀʏ sᴜɴᴀᴛɪ ʜᴜ 🤗**",
    "**ᴊᴏɪɴ ᴠᴄ ғᴀsᴛ, ɢᴏssɪᴘ sᴛᴀʀᴛ ʜᴏ ᴛʜᴀ 😋**",
    "**ᴠᴄ ᴀᴀᴋᴇ sʜᴀʟᴇᴇɴ ʙᴀᴛᴇɴ ᴋʀᴛᴇ ʜᴀɪ 🤭**",
    "**ᴠᴄ ᴀᴀɴᴀ ᴡᴀʀɴᴀ ᴍᴇʀɪ ᴄᴜᴛᴇɴᴇss ᴍɪss ᴋʀᴏɢᴇ 😚**",
    "**ᴠᴄ ᴀᴀ ʀʜᴇ ʜᴏ ʏᴀ ғɪʀ ᴘʀᴏᴘᴏsᴇ ᴋʀᴜ? 💍**",
    "**ᴄʜᴀʟᴏ ᴠᴄ ᴘʀ ᴍᴏᴏᴅ ғʀᴇsʜ ᴋʀᴛᴇ ʜᴀɪ 🌈**",
    "**ᴠᴄ ᴘᴀʀ ᴇᴋ ɴᴇᴡ ᴘʀᴀɴᴋ ᴋʀᴛᴇ ʜᴀɪ 🤪**",
    "**ᴠᴄ ᴀᴀ, ᴍᴇʀɪ ᴅᴜᴘᴀᴛᴛᴀ ᴜᴅᴀ ʀʜᴀ ʜᴀɪ ʙᴀʏᴇʀᴇ 😅**",
    "**ᴠᴄ ᴀᴀᴏ ɴᴀ, ᴇᴋ ᴅɪʟᴄʜᴀsᴘ ɴᴇᴡs ʜᴀɪ 📰**",
    "**ᴠᴄ ᴘʀ ᴄʜᴏᴄᴏʟᴀᴛᴇ ᴅᴇᴛɪ ʜᴜ 🍫**",
    "**ᴠᴄ ᴀᴀᴋᴇ ᴍᴇʀᴇ sᴀᴛʜ ғʟɪʀᴛ ᴋʀᴏ 😏**",
]



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
    """Mention every human member, BATCH per message, until done or stopped."""
    batch = []
    try:
        async for member in client.get_chat_members(chat_id):
            if chat_id not in ACTIVE:
                break
            user = member.user
            if not user or user.is_bot or user.is_deleted:
                continue
            name = "".join(ch for ch in (user.first_name or "User") if ch not in "[]()*_`").strip() or "User"
            batch.append(f"[{name}](tg://user?id={user.id})")
            if len(batch) == BATCH:
                await _send(client, chat_id, " ".join(batch) + (f" {closing}" if closing else ""), reply_to)
                batch = []
                await asyncio.sleep(DELAY)
        if batch and chat_id in ACTIVE:
            await _send(client, chat_id, " ".join(batch) + (f" {closing}" if closing else ""), reply_to)
    except Exception as e:
        print(f"[rtag] stopped in {chat_id}: {type(e).__name__}: {e}")
    finally:
        ACTIVE.discard(chat_id)


async def _start(message, client, closing_pool, reply_mode: bool):
    chat_id = message.chat.id
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply("⬤ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴏɴʟʏ ғᴏʀ ɢʀᴏᴜᴘs.")
    if not message.from_user or not await _is_admin(client, chat_id, message.from_user.id):
        return await message.reply("⬤ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ʙᴀʙʏ, ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴅᴏ ᴛʜɪs.")
    if chat_id in ACTIVE:
        return await message.reply("⬤ ᴘʟᴇᴀsᴇ ᴀᴛ ғɪʀsᴛ sᴛᴏᴘ ʀᴜɴɴɪɴɢ ᴍᴇɴᴛɪᴏɴ ᴘʀᴏᴄᴇss... (/rstop)")

    reply_to = None
    closing = None
    if reply_mode:
        reply_to = message.reply_to_message.id
        closing = random.choice(EMOJI)
    else:
        closing = random.choice(closing_pool)

    ACTIVE.add(chat_id)
    asyncio.create_task(_tag_run(client, chat_id, closing=closing, reply_to=reply_to))


@app.on_message(filters.command(["rtag"], prefixes=prefix_cmds) & filters.group)
async def rtag_cmd(client, message):
    # plain /rtag -> random tag message; /rtag as a reply -> tag as replies to that message
    await _start(message, client, TAGMES, reply_mode=bool(message.reply_to_message))


@app.on_message(filters.command(["vctag"], prefixes=prefix_cmds) & filters.group)
async def vctag_cmd(client, message):
    await _start(message, client, VC_TAG, reply_mode=False)


@app.on_message(filters.command(["rstop", "tagstop", "vcstop", "tagoff"], prefixes=prefix_cmds) & filters.group)
async def stop_tag(client, message):
    chat_id = message.chat.id
    if chat_id not in ACTIVE:
        return await message.reply("⬤ ᴄᴜʀʀᴇɴᴛʟʏ ɪ'ᴍ ɴᴏᴛ ᴛᴀɢɢɪɴɢ ʙᴀʙʏ.")
    if not message.from_user or not await _is_admin(client, chat_id, message.from_user.id):
        return await message.reply("⬤ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ʙᴀʙʏ, ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ sᴛᴏᴘ ɪᴛ.")
    ACTIVE.discard(chat_id)
    await message.reply("♥︎ ᴛᴀɢ sᴛᴏᴘᴘᴇᴅ.")
