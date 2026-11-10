from AloneX import font

import html
import random
import config
import random
from telegram import constants
from AloneX.db.user_characters import get_user_level, get_user_characters, get_user_win, get_user_lose, get_user_characters, add_user_character
from AloneX.db.characters import get_character, add_character
from AloneX.helpers.decorator import Command, devs_only
from AloneX.helpers.utils import encode_to_base64, decode_to_base64
from AloneX.db.game import get_cash, update_cash
from AloneX.helpers.decorator import Command, devs_only




user_characters = {}
tokens = {}


@Command('setclaim')
@devs_only
async def _setClaimCharacter(update, context):
      m = update.effective_message
      user = m.from_user
      if len(m.text.split()) < 2:
           return await m.reply_text(font("Hey, dev did you forget to give character code just ? 🥴"))
            
      try:
         character_id, limit = m.text.split()[1:]
         assert limit.isdigit() and character_id.isdigit()
      except Exception as e:
            return await m.reply_text(f"❌ ERROR: {e}")

      character = await get_character(character_id)
      if not character:
           return await m.reply_text(font("Not a valid character code 🧐"))
            
      code = encode_to_base64(m.text.split()[1])
      tokens[code] = {"users": [], "limit": int(limit)}
      photo = random.choice(character['images'])
      return await m.reply_photo(
            photo=photo,
            caption=f"<b>Yes. added character {character['character_name']} to claim list. p.s can be character claimed using</b> <code>/claim {code}</code>",
            parse_mode=constants.ParseMode.HTML
      )
      
      
           


@Command('claim')
async def _claimCharacter(update, context):
      m = update.effective_message
      user = m.from_user

      def append(token: str, user_id: int) -> None:
            tokens[token].setdefault('users', []).append(user_id)
      
      if len(m.text.split()) < 2:
         return await m.reply_text(font("Token Required."))
      else:
         token = m.text.split()[1]
         if not token in list(tokens.keys()):
              return await m.reply_text(font("Token expired or not a valid token."))
         else:       
             users = tokens[token].get("users", [])
             if tokens[token]['limit'] == len(users):
                   del tokens[token]
                   return await context.bot.send_message(
                         chat_id=config.SUPPORT_CHAT,
                         text=f"Token {token} has been revoked."
                   )
             if user.id in users:
                  return await m.reply_text("You can't use the token twice. 🤧")
                   
             character_id = decode_to_base64(token)
             character = await get_character(character_id)
             if not character:
                  return await m.reply_text(font("404. Character not found."))
             else:          
                  user_characters = await get_user_characters(user.id)
                  if user_characters.get(character_id):
                        cash = int(character['cash']/2)
                        append(token, user.id)
                        await update_cash(user.id, cash)
                        return await m.reply_text(f"You already own the character, but no worries 😉 I have added character half of the cash amount ({cash} 💸) to your account 🏦.")
                  else:      
                     character_name = character['character_name']
                     health = character['health']
                     attack = character['attack']
                     rarity_type = character['rarity_type']
                     images = character['images']
                     character_id = character['character_id']
                     append(token, user.id)
                     await add_user_character(
                           user_id=user.id,
                           character_name=character_name,
                           health=health,
                           attack=attack,
                           rarity_type=rarity_type,
                           images=images,
                           character_id=character_id
                     )
                     return await m.reply_text(
                           text=f"Cool, you brought {character['character_name']}! check /characters to see your updated collection."
                     )
                  
                  
             
                 

@Command("status")
async def __gameStatus(update, context):
      m = update.effective_message
      user = m.from_user
      msg = await m.reply_text(font("🔎 <b>Analyzing player status.</b>"), parse_mode=constants.ParseMode.HTML)
      level = await get_user_level(user.id)
      win_count = await get_user_win(user.id)
      lose_count = await get_user_lose(user.id)
      characters = len(await get_user_characters(user.id))
      cash = await get_cash(user.id)
      text = \
f"""
<a href='https://files.catbox.moe/562cjr.jpg'>ℹ️</a> <b>{user.mention_html()}'s Game Status </b>:

🌀 <b>Name</b>: <code>{html.escape(user.full_name)}</code>
🎚️ <b>Level</b>: <code>{level}</code>
🏆 <b>Win's</b>: <code>{win_count}</code>
☠️ <b>Lose's</b>: <code>{lose_count}</code>

🛒 <b>Character's</b>: <code>{characters}</code>
🏦 <b>Balance</b>: <code>{cash} doller</code>
"""
      return await msg.edit_text(
            text, parse_mode=constants.ParseMode.HTML
      )
      




@Command("characters")
async def _userCharacters(update, context):
      m = update.effective_message
      user = m.from_user
      characters = await get_user_characters(user.id)
      if not characters:
            return await m.reply_text(font("🥱 Try collecting some *characters* for REAL."))
      else:
          msg = await m.reply_text(font("🔎 Checking for characters ..."))
          user_characters[user.id] = characters
          shuffled_dict = dict(random.sample(list(characters.items()), len(characters)))
          text = f"ℹ️ <b>{user.mention_html()}'s Characters</b>:\n\n"
          for character_id, character in shuffled_dict.items():
                image = random.choice(character['images'])
                text += f"✦ <code>{character_id}</code> : <b><a href='{image}'>{character['character_name']}</a></b> [<code>{character['health']} HP</code>] <code>Type {character['rarity_type']}</code>\n"

          text += "\n\n<code>:D You gotta power up like a cursed spirit, fam!</code>"
          return await msg.edit_text(
                text=text,
                parse_mode=constants.ParseMode.HTML
          )
                
       
      


@Command("addcharacter")
@devs_only
async def _addCharacter(update, context):
    m = update.effective_message

    # Command format: /addcharacter <name> <health> <cash>
    args = m.text.split(maxsplit=3)
    if len(args) < 4:
        return await m.reply_text(
            "⚠️ Usage: /addcharacter <name> <health> <cash>\n"
            "Example: /addcharacter Naruto 200 2000\n"
            "Reply to an image to set it as character image."
        )

    character_name = args[1]
    try:
        health = int(args[2])
        cash = int(args[3])
    except ValueError:
        return await m.reply_text(font("⚠️ Health and cash must be integers!"))

    # Check if user replied to a photo
    images = []
    if m.reply_to_message and m.reply_to_message.photo:
        # Take the biggest photo
        images.append(m.reply_to_message.photo[-1].file_id)
    else:
        images.append(f"https://i.imgur.com/{random.randint(100,999)}.jpg")  # fallback

    # Optional default attack and rarity
    attack = ["Attack1", "Attack2"]
    rarity_type = 1

    # Add character to DB
    result = await add_character(
        character_name=character_name,
        health=health,
        attack=attack,
        images=images,
        rarity_type=rarity_type,
        cash=cash
    )

    if result:
        return await m.reply_text(
            f"✅ Character <b>{character_name}</b> added successfully with image!",
            parse_mode=constants.ParseMode.HTML
        )
    else:
        return await m.reply_text(font("❌ Failed to add character."))
