from AloneX import font
import random
import html
import re
from telegram import helpers, constants, MessageEntity
from telegram.ext import filters, ApplicationHandlerStop
from AloneX.helpers.decorator import Messages, Command, admin_check, disableable
from AloneX.db.afk import add_user_afk, get_user_afk, remove_user_afk
from AloneX.db.users import get_user_id_by_username
from cachetools import TTLCache

afk_cache = TTLCache(maxsize=10000, ttl=3600)
username_cache = TTLCache(maxsize=5000, ttl=1800)

__module__ = "𝐀ғᴋ🛌"
__help__ = """
*Afk🛌*
*Description:*  
This module lets you mark yourself as AFK (Away From Keyboard). When you return online, the bot will automatically greet you in the group.
*Commands:*  
❂ `/afk` - Set your AFK status with an optional reason.
❂ `brb` - Set your AFK status with an optional reason.
*Example:*  
`/afk I'm studying`  
`brb I'm watching anime`
"""

AFK_BACK_STRING_LIST = [
    "🎉 Welcome back, {}! The cursed spirits can finally relax!",
    "👀 Look who decided to show up! It's the sorcerer, {}!",
    "🔥 Hot stuff alert! {} has returned to exorcise the vibes!",
    "😎 You missed me, didn't you? Just kidding, {}! You know I'm unbeatable!",
    "🚀 Blast off! {} is back, ready to unleash some cursed techniques!",
    "🍕 Pizza's here, and so is the strongest sorcerer, {}!",
    "🎈 Time to celebrate, {} is back to save the day!",
    "💥 Boom! {} has re-entered the chat like a true sorcerer!",
    "🕺 Dance time! {} is back on the battlefield, let's go!",
    "🤩 Did you miss me? Nah, just kidding, {}! You know I'm always around!",
    "🌟 Shine bright like a cursed technique, {} is here to dazzle!",
    "🎤 Mic check! 1, 2, 3... it's the legendary sorcerer, {}!",
    "🦸‍♂️ Superhero landing! Welcome back, {}! Time to exorcise some spirits!",
    "🎭 The show can go on, {} is here to dominate the stage!",
    "🍹 Time for some fun, {} is back in the Jujutsu game!"
]

AFK_MESSAGES = [
    "User  {} is currently on a quest for snacks. 🍕",
    "User  {} has entered the realm of the AFK. 💤",
    "User  {} is busy fighting the urge to procrastinate. ⚔️",
    "User  {} is off saving the world... or just their phone battery. 🔋",
    "User  {} has temporarily vanished like a cursed spirit. 👻",
    "User  {} is in a deep meditation... or napping. 🧘‍♂️",
    "User  {} is away, probably plotting world domination. 🌍"
]

AFK_STRING = """
<b>⚡ Yo, {} is chillin' AFK!</b>
<b>🕣 Since</b>: <code>{}</code>
<b>🕣 Now</b>: <code>{}</code>
<b>📑 Reason</b>: 
<code>{}</code>
"""

BACK_AFK_STRING = """
<b>{}</b>
<b>🕣 Since</b>: <code>{}</code>
<b>🕣 Now</b>: <code>{}</code>
<b>📑 Reason</b>: 
<code>{}</code>
"""

async def get_afk_cached(user_id):
    cached = afk_cache.get(user_id)
    if cached is not None:
        return cached
    result = await get_user_afk(user_id)
    if result:
        afk_cache[user_id] = result
    return result

async def get_username_cached(username):
    cached = username_cache.get(username)
    if cached is not None:
        return cached
    result = await get_user_id_by_username(username)
    if result:
        username_cache[username] = result
    return result

def invalidate_afk_cache(user_id):
    afk_cache.pop(user_id, None)

@Messages(filters=filters.ChatType.GROUPS & ~filters.COMMAND & ~filters.Regex(re.compile(r'^brb\b', re.IGNORECASE)), group=1)
async def NoLongerAfk(update, context):
    message = update.effective_message
    user = update.effective_user
    if user.id in afk_cache or await get_afk_cached(user.id):
        afk = await get_afk_cached(user.id)
        if afk:
            reason = html.escape(afk.get('reason', '✋ Reason Not Provided.'))
            datetime = afk['datetime']
            await remove_user_afk(user.id)
            invalidate_afk_cache(user.id)
            mention = helpers.mention_html(user.id, user.first_name)
            # Use font() safely on the fixed part of the message
            fixed_part = font(random.choice(AFK_BACK_STRING_LIST))
            afk_string = fixed_part.format(mention)

            await message.reply_text(
                text=font(BACK_AFK_STRING).format(afk_string, datetime, str(message.date).split('+')[0], reason),
                parse_mode=constants.ParseMode.HTML
            )

@Messages(filters=filters.ChatType.GROUPS, group=2)
async def ReplyAfk(update, context):
    message = update.effective_message
    reply = message.reply_to_message
    try:
        async def check_afk(message, user_id):
            user = await get_afk_cached(user_id)
            if not user:
                return
            mention = helpers.mention_html(user['user_id'], user['first_name'])
            datetime = user['datetime']
            reason = html.escape(user['reason'])
            return await message.reply_text(
                text=font(AFK_STRING).format(mention, datetime, str(message.date).split('+')[0], reason),
                parse_mode=constants.ParseMode.HTML
            )
    except Exception as e:
        print(repr(e))
    entities = message.parse_entities([MessageEntity.TEXT_MENTION, MessageEntity.MENTION])
    if entities:
        for ent in entities:
            if ent.type == MessageEntity.TEXT_MENTION:
                user_id = ent.user.id
                await check_afk(message, user_id)
            elif ent.type == MessageEntity.MENTION:
                username = message.text[ent.offset:ent.offset + ent.length][1:]
                user_id = await get_username_cached(username)
                if user_id:
                    await check_afk(message, user_id)
    elif reply and not reply.sender_chat:
        user_id = reply.from_user.id
        await check_afk(message, user_id)

async def set_afk_handler(update, context):
    message = update.effective_message
    if message.sender_chat:
        return
    first_name = message.from_user.first_name
    user_id = message.from_user.id
    datetime = str(message.date).split('+')[0]
    if len(message.text) >= 100:
        await message.reply_text(font('🧏 Your Afk Reason was shortened to 100 characters.'))
    if message.text.lower().startswith('brb'):
        reason = message.text[3:].strip()[:100] if len(message.text) > 3 else "✋ Reason Not Provided. "
    else:
        reason = message.text.split(maxsplit=1)[1][:100] if len(message.text.split()) >= 2 else "✋ Reason Not Provided. "
    await add_user_afk(
        user_id=user_id,
        first_name=first_name,
        datetime=datetime,
        reason=reason
    )
    afk_cache[user_id] = {
        'user_id': user_id,
        'first_name': first_name,
        'datetime': datetime,
        'reason': reason
    }
    mention = helpers.mention_html(user_id, first_name)

    # Use font() safely
    msg_template = font(random.choice(AFK_MESSAGES))
    await message.reply_text(
        msg_template.format(mention),
        parse_mode=constants.ParseMode.HTML
    )

@Command('afk', block=True)
@disableable("afk")
async def SetAfk(update, context):
    await set_afk_handler(update, context)

@Messages(filters=filters.ChatType.GROUPS & filters.Regex(re.compile(r'^brb\b', re.IGNORECASE)), group=0)
async def SetAfkBrb(update, context):
    await set_afk_handler(update, context)
