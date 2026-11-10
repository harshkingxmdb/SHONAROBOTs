import random
import aiohttp
import uuid
import config
import os
import tempfile
from datetime import date
from urllib.parse import quote
from AloneX.db.couple import *
from AloneX import pbot, LOGGER, font
from AloneX.helpers.decorator import Command, admin_check, only_groups
from telegram import constants, helpers
from telegram.error import BadRequest

__module__ = "𝐂ᴏᴜᴘʟᴇs💑"

__help__ = """
*𝐂ᴏᴜᴘʟᴇs💑*

*Description:*  
Manage virtual couples in your chat with daily assignments and fun interactions.

*Commands:*  
❂ `/couple` – Generate a unique couple image. Each day, two people are selected.  
❂ `/divorce` – End the marriage of your assigned couple.  
❂ `/couples` – Show all couples in the chat.  
❂ `/rmcouples` – Clear all couples in the chat.
"""

PROMPTS = [
    # ... (keep your full PROMPTS list here unchanged) ...
    "anime couple in a romantic moment"
]


async def create_couple_image(bot):
    """
    Generate an image using pollinations and upload it to the logs channel.
    Returns: file_id (str) on success, or None on failure (or fallback file_id).
    """
    prompt = random.choice(PROMPTS)
    url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=1024&height=1024&seed={random.randint(1,10000)}"

    # Use a temp file to avoid clashes and guarantee cleanup
    tmp = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    LOGGER.error(f"Create couple image failed, status={response.status}")
                    return None
                image_data = await response.read()

        tmp = tempfile.NamedTemporaryFile(suffix=".jpeg", delete=False)
        tmp.write(image_data)
        tmp.close()
        # send the photo to logs channel and return its file_id
        msg = None
        if config.LOGS_CHANNEL:
            msg = await bot.send_photo(config.LOGS_CHANNEL, tmp.name)
        file_id = None
        if msg and getattr(msg, "photo", None):
            file_id = msg.photo[-1].file_id
        # cleanup file
        try:
            os.remove(tmp.name)
        except Exception:
            pass
        return file_id
    except Exception as e:
        LOGGER.error(f"Error while generating couple image: {str(e)}")
        # attempt to cleanup
        if tmp and os.path.exists(tmp.name):
            try:
                os.remove(tmp.name)
            except Exception:
                pass
        # You had a fallback file_id in original code; keep that as fallback if desired:
        fallback = 'AgACAgQAAxUHZ1Q2EN9vjvhN07zG-QNGybEl4tsAAq2zMRuVewRRwIHAII7NSzEBAAMCAAN4AAM2BA'
        return fallback


async def send_couple(msg, man, woman, photo, bot):
    """
    Send a couple photo + caption to the chat.
    msg: placeholder Message (text) that was previously sent by the bot (we will delete it after sending photo).
    photo: can be a Telegram file_id, a URL, or local path.
    bot: context.bot (python-telegram-bot Bot instance)
    """
    if not photo:
        return await msg.edit_text(
            "❌ Could not find a valid couple image.",
            parse_mode=constants.ParseMode.MARKDOWN
        )

    today = date.today()
    man_mention = helpers.mention_html(user_id=man['user_id'], name=man['name'])
    woman_mention = helpers.mention_html(user_id=woman['user_id'], name=woman['name'])
    date_str = f"{today.year}-{today.month}-{today.day}"
    text = (
        f"❣️ <b>Couple of the day (</b><code>{date_str}</code><b>)</b> ❣️\n\n"
        f"🤵 <b>Husband</b>: <b>{man_mention}</b>\n"
        f"👰 <b>Fiancée</b>: <b>{woman_mention}</b>\n\n"
        f"✨ <b>Congrats By {config.BOT_USERNAME}</b>"
    )

    chat_id = msg.chat.id
    try:
        # Try to send photo as a new message (caption supports HTML)
        sent = await bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=text,
            parse_mode=constants.ParseMode.HTML
        )
        # Delete placeholder msg (bot's own message)
        try:
            await msg.delete()
        except Exception:
            # not critical if delete fails (permissions etc.)
            LOGGER.warning("Couldn't delete placeholder message after sending photo.")
        return sent
    except BadRequest as e:
        # Common cause: invalid file_id or URL; fallback to text with the error
        LOGGER.error(f"Failed to send couple photo: {e}")
        return await msg.edit_text(
            f"{text}\n\n❌ Failed to send couple image: `{str(e)}`",
            parse_mode=constants.ParseMode.HTML
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error when sending couple photo: {e}")
        return await msg.edit_text(
            f"{text}\n\n❌ Failed to send couple image: `{str(e)}`",
            parse_mode=constants.ParseMode.HTML
        )


def get_opposite_person(couple_dict, user_id):
    """
    Get the opposite person's data from a couple dictionary

    :param couple_dict: Dictionary with 'man' and 'woman' keys
    :param user_id: User ID to check
    :return: Dictionary of the opposite person or None
    """
    if couple_dict['man']['user_id'] == user_id:
        return couple_dict['woman']
    elif couple_dict['woman']['user_id'] == user_id:
        return couple_dict['man']
    else:
        return None  # User not found in the couple


@Command('couples')
@only_groups
async def get_couples(update, context):
    m = update.effective_message
    user = m.from_user
    bot = context.bot
    chat = m.chat
    # send a placeholder text (we will replace by sending a photo or editing)
    msg = await chat.send_message(font('❣️ *Check-ing couples in chat*'), parse_mode=constants.ParseMode.MARKDOWN)
    couple = await get_couple(chat.id)
    if couple and len(couples := couple.get('couples', [])) != 0:
        text = f"<b>💖 Couples in {chat.title} </b>💖\n\n<blockquote>"
        for idx, data in enumerate(couples, start=1):
            man = data['man']
            woman = data['woman']
            man_mention = helpers.mention_html(user_id=man['user_id'], name=man['name'])
            woman_mention = helpers.mention_html(user_id=woman['user_id'], name=woman['name'])
            text += f"<b>{idx}, 🧑‍💼 {man_mention} & 👰 {woman_mention}</b>\n"
        text += f"</blockquote><b>\n\nBy {config.BOT_USERNAME}</b>"
        # Default image file_id used as cover if you want to show a photo
        media = "AgACAgQAAxkBAAEBfIFnVIvmG68Wy0PKbrD0q5vmtVG4IgACQ7YxG6hnpFKJAAHfTierp2MBAAMCAAN5AAM2BA"
        if len(text) < 1024:
            # send photo (caption) instead of editing a text message into media (not allowed)
            try:
                sent = await bot.send_photo(chat.id, photo=media, caption=text, parse_mode=constants.ParseMode.HTML)
                # delete placeholder
                try:
                    await msg.delete()
                except Exception:
                    pass
                return sent
            except BadRequest as e:
                LOGGER.error(f"Failed to send couples cover image: {e}")
                # fallback to editing text
                return await msg.edit_text(text, parse_mode=constants.ParseMode.HTML)
            except Exception as e:
                LOGGER.error(f"Unexpected error in get_couples send_photo: {e}")
                return await msg.edit_text(text, parse_mode=constants.ParseMode.HTML)
        else:
            return await msg.edit_text(text, parse_mode=constants.ParseMode.HTML)
    else:
        return await msg.edit_text(font('*👀 This chat has no couples yet. use /couple to find them.*'), parse_mode=constants.ParseMode.MARKDOWN)


@Command('divorce')
@only_groups
async def divorce(update, context):
    m = update.effective_message
    user = m.from_user
    bot = context.bot
    chat = m.chat

    couple = await get_user_couple(chat.id, user.id)
    if couple and (await remove_couple_by_user(chat.id, user.id)):
        other = get_opposite_person(couple, user.id)
        mention = helpers.mention_html(user_id=other['user_id'], name=other['name'])
        return await m.reply_text(f'<b>You divorced with {mention} 💔</b>.', parse_mode=constants.ParseMode.HTML)
    else:
        return await m.reply_text("*You didn't married anyone yet. 🤣*", parse_mode=constants.ParseMode.MARKDOWN)


couple_process = {}  # for avoid spam.


@Command('couple')
@only_groups
async def couple(update, context):
    m = update.effective_message
    bot = context.bot
    chat = m.chat
    today = date.today()
    msg = await m.reply_text(font('*👀 Checking couple of the day ...*'), parse_mode=constants.ParseMode.MARKDOWN)
    couple = await get_couple(chat.id)
    if couple and len(couple.get('couples', [])) == 30:
        try:
            await msg.edit_text(font('🤯 *Maximum couples for this chat have been chosen, to clear couples in chat use /rmcouples.*'), parse_mode=constants.ParseMode.MARKDOWN)
        except Exception:
            pass
        return

    day = couple['day'] if couple and couple.get('day') else 0

    if day != today.day:
        # Let's find a new couple for the day
        if couple_process.get(chat.id, False):
            try:
                await msg.edit_text(font('*Spammer spotted!* 💀'), parse_mode=constants.ParseMode.MARKDOWN)
            except Exception:
                pass
            return

        couple_process[chat.id] = True
        try:
            await msg.edit_text(font('*💖 Finding new couple of the day ...*'), parse_mode=constants.ParseMode.MARKDOWN)
            members = []
            members_data = []
            async for mbr in pbot.get_chat_members(chat.id):
                if mbr.user.is_bot or mbr.user.is_deleted:  # skip bots and deleted accounts
                    continue
                else:
                    members.append(mbr.user.id)
                    members_data.append({mbr.user.id: mbr.user})

            if not members:
                return await msg.edit_text("👀 *I couldn't find anyone here to make a match.*", parse_mode=constants.ParseMode.MARKDOWN)

            users = await get_users_not_in_couples(chat.id, members)
            if len(users) < 2:
                return await msg.edit_text(font("*🤣 We need more people to match a couple since most of them are already coupled!*"), parse_mode=constants.ParseMode.MARKDOWN)

            # Choose two persons in chat who are not married yet
            man_id, woman_id = random.sample(users, 2)
            man_info = next(d[man_id] for d in members_data if man_id in d)
            woman_info = next(d[woman_id] for d in members_data if woman_id in d)
            man = {'user_id': man_info.id, 'name': man_info.full_name}
            woman = {'user_id': woman_info.id, 'name': woman_info.full_name}

            await msg.edit_text("😍 *New couple is decided, now making couple's art for them ...*", parse_mode=constants.ParseMode.MARKDOWN)
            photo = await create_couple_image(bot)
            if await update_couple(chat.id, man=man, woman=woman, day=today.day, photo_id=photo):
                try:
                    await send_couple(msg, man, woman, photo, bot)
                except Exception as e:
                    return await msg.edit_text(f"👀 *Looks like we encountered an error when sending couple image*: `{str(e)}`.", parse_mode=constants.ParseMode.MARKDOWN)
            else:
                return await msg.edit_text("*Couple are not updated 🤔 what's wrong.*", parse_mode=constants.ParseMode.MARKDOWN)
        finally:
            # Always clear the process lock
            couple_process.pop(chat.id, None)
    else:
        man = couple['man']
        woman = couple['woman']
        photo = couple.get('photo_id', 'AgACAgQAAxUHZ1Q2EN9vjvhN07zG-QNGybEl4tsAAq2zMRuVewRRwIHAII7NSzEBAAMCAAN4AAM2BA')
        try:
            await send_couple(msg, man, woman, photo, bot)
        except Exception as e:
            return await msg.edit_text(f"👀 *Looks like we encountered an error when sending couple image*: `{str(e)}`.", parse_mode=constants.ParseMode.MARKDOWN)


@Command('rmcouples')
@admin_check('can_change_info')
@only_groups
async def removeCouples(update, context):
    m = update.effective_message
    chat = m.chat
    doc = await remove_couple(chat.id)
    if doc:
        await m.reply_text(font('😼 *Every couples in this chat has been cleaned.*'), parse_mode=constants.ParseMode.MARKDOWN)
    else:
        await m.reply_text("✋ *Looks like there's no single couples saved.*", parse_mode=constants.ParseMode.MARKDOWN)
