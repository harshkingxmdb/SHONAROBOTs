import re
import html
import random
import io
import json
import os
import unicodedata
import uuid
import math
import csv
import base64
import time
import config
import string
import asyncio
from telegram.error import BadRequest
from functools import wraps
from collections import OrderedDict
from datetime import datetime
from typing import Union, Any, Tuple
from pyrogram import Client, enums, types
from AloneX import pbot, font
from telegram.constants import MessageEntityType, ChatType, ChatMemberStatus, ParseMode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from PIL import Image
from pyrogram.types import Message
from typing import Optional, Union

####################################################################################################

def convert_to_jpeg(path: str):
     image = Image.open(path)
     rgb_image = image.convert('RGB')
     rgb_image.save(path, 'JPEG')
     return path

def convert_to_webp(path):
    im = Image.open(path)
    maxsize = (512, 512)
    if (im.width and im.height) < 512:
           size1 = im.width
           size2 = im.height
           if im.width > im.height:
                scale = 512 / size1
                size1new = 512
                size2new = size2 * scale
           else:
                scale = 512 / size2
                size1new = size1 * scale
                size2new = 512
           size1new = math.floor(size1new)
           size2new = math.floor(size2new)
           sizenew = (size1new, size2new)
           im = im.resize(sizenew)
    else:
         im.thumbnail(maxsize)
         im.save(path, "PNG")




####################################################################################################




def cookies_csv_to_str(path: str) -> str:
    with open(path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        cookies = [f"{row['Name']}={row['Value']}" for row in reader]
    return ";".join(cookies)


def cookies_json_to_str(file: str):
    with open(file, 'r') as file:
        content = json.load(file)
        cookies = ""
        for c in content:
            cookies += f"{c['name']}={c['value']};"
        return cookies.strip()




def unicode_to_normal(unicodeText):
    return unicodedata.normalize('NFKD', unicodeText).encode('ascii','ignore').decode()


def get_nouns(length:int = 10):
    path = "./AloneX/helpers/data/Noun.txt"
    with open(path, "r") as file:
          lines = file.readlines()
          random.shuffle(lines)
          return [line.strip() for line in lines[:length]]

                  
def get_adjectives(length:int = 10):
    path = "./AloneX/helpers/data/adjectives.txt"
    with open(path, "r") as file:
          lines = file.readlines()
          random.shuffle(lines)
          return [line.strip() for line in lines[:length]]




class Password:
  
     symbols = ['#', '$', '_','@']
  
     def easy_password(length:int = 10, only_noun=True, only_adjective=True):
       
           passwords = []
           if only_noun:
               nouns:list = get_nouns(length)
               passwords.extend([noun + str(random.randrange(999, 5000)) for noun in nouns])
           if only_adjective:
               adjectives:list = get_adjectives(length)
               passwords.extend([adjective + str(random.randrange(999, 5000)) for adjective in adjectives])
             
           return passwords

           
     def normal_password(length:int = 10, only_noun=True, only_adjective=True):

           passwords = []
           if only_noun:
               nouns:list = get_nouns(length)
               passwords.extend([noun + random.choice(Password.symbols) + str(random.randrange(999, 5000)) for noun in nouns])
           if only_adjective:
               adjectives:list = get_adjectives(length)
               passwords.extend([adjective + random.choice(Password.symbols) + str(random.randrange(999, 5000)) for adjective in adjectives])
             
           return passwords
       
     def random_password(length:int = 10, characters_length:int = 10, only_string=True, only_digit=True):
           characters = ''
           if only_string:
                 characters += string.ascii_uppercase + string.ascii_lowercase
           if only_digit:
                 characters += string.digits
           passwords = [
               ''.join(random.choice(characters) for _ in range(characters_length))
               for _ in range(length)
           ]
           return passwords  
       
     
####################################################################################################


def time_formatter(seconds: int) -> str:
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        ((str(days) + " day(s), ") if days else "")
        + ((str(hours) + " hour(s), ") if hours else "")
        + ((str(minutes) + " minute(s), ") if minutes else "")
        + ((str(seconds) + " second(s), ") if seconds else "")
    )
    return tmp[:-2]
  

async def auto_delete(msg, delay: int = 10):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception as e:
        err = str(e).lower()
        if "message to delete not found" in err or "message can't be deleted" in err:
            return  # Silently ignore known cases
        print(f"[AutoDelete Error] {e}")




# Cache decorator definition
def async_cache(max_size: int = 1000, max_idle_time: [int, None] = None):
    def decorator(func):
        # Create a unique cache dictionary for each decorated function
        cache_dict = OrderedDict()
        last_access_times = {}

        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = (args, frozenset(kwargs.items()))
            current_time = time.time()

            # Only check for idle time if max_idle_time is set
            if max_idle_time is not None:
                idle_keys_to_remove = [
                    k for k, last_access in last_access_times.items()
                    if current_time - last_access > max_idle_time
                ]
                for idle_key in idle_keys_to_remove:
                    if idle_key in cache_dict:
                        del cache_dict[idle_key]
                    del last_access_times[idle_key]

            # Clear oldest items if max size is reached
            while len(cache_dict) >= max_size:
                oldest_key = next(iter(cache_dict))
                del cache_dict[oldest_key]
                del last_access_times[oldest_key]

            if key in cache_dict:
                last_access_times[key] = current_time
                return cache_dict[key]

            res = await func(*args, **kwargs)
            cache_dict[key] = res
            last_access_times[key] = current_time

            return res

        def clear_cache():
            cache_dict.clear()
            last_access_times.clear()

        def get_cache_stats():
            return {
                'total_items': len(cache_dict),
                'last_access_times': dict(last_access_times)
            }

        wrapper.clear_cache = clear_cache
        wrapper.get_cache_stats = get_cache_stats

        return wrapper

    return decorator

  

def sync_cache(max_size: int = 1000, max_idle_time: [int, None] = None):
    def decorator(func):
        # Create a unique cache dictionary for each decorated function
        cache_dict = OrderedDict()
        last_access_times = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, frozenset(kwargs.items()))
            current_time = time.time()

            # Only check for idle time if max_idle_time is set
            if max_idle_time is not None:
                idle_keys_to_remove = [
                    k for k, last_access in last_access_times.items()
                    if current_time - last_access > max_idle_time
                ]
                for idle_key in idle_keys_to_remove:
                    if idle_key in cache_dict:
                        del cache_dict[idle_key]
                    del last_access_times[idle_key]

            # Clear oldest items if max size is reached
            while len(cache_dict) >= max_size:
                oldest_key = next(iter(cache_dict))
                del cache_dict[oldest_key]
                del last_access_times[oldest_key]

            if key in cache_dict:
                last_access_times[key] = current_time
                return cache_dict[key]

            res = func(*args, **kwargs)
            cache_dict[key] = res
            last_access_times[key] = current_time

            return res

        def clear_cache():
            cache_dict.clear()
            last_access_times.clear()

        def get_cache_stats():
            return {
                'total_items': len(cache_dict),
                'last_access_times': dict(last_access_times)
            }

        wrapper.clear_cache = clear_cache
        wrapper.get_cache_stats = get_cache_stats

        return wrapper

    return decorator




def shuffle_text(text):
    result = ""
    for char in text:
        if random.choice([True, False]):
            result += char.upper()
        else:
            result += char.lower()
    return result




def shout_text(text):
    result = []
    result.append(' '.join([s for s in text]))
    for pos, symbol in enumerate(text[1:]):
        result.append(symbol + ' ' + '  ' * pos + symbol)
    
    result = list("\n".join(result))
    result[0] = text[0]
    result = "".join(result)
    
    return f"`\n{result}```"


def owo_text(text):
    faces = [
        '(・`ω´・)', ';;w;;', 'owo', 'UwU', '>w<', '^w^', 
        r'\(^o\) (/o^)/', '( ^ _ ^)∠☆', '(ô_ô)', '~:o', 
        ';____;', '(*^*)', '(>_', '(♥_♥)', '*(^O^)*', '((+_+))'
    ]
    
    # Replace [rl] with w
    reply_text = re.sub(r'[rl]', "w", text)
    reply_text = re.sub(r'[ｒｌ]', "ｗ", reply_text)
    reply_text = re.sub(r'[RL]', 'W', reply_text)
    reply_text = re.sub(r'[ＲＬ]', 'Ｗ', reply_text)
    
    # Replace n before vowels with ny
    reply_text = re.sub(r'n([aeiouａｅｉｏｕ])', r'ny\1', reply_text)
    reply_text = re.sub(r'ｎ([ａｅｉｏｕ])', r'ｎｙ\1', reply_text)
    reply_text = re.sub(r'N([aeiouAEIOU])', r'Ny\1', reply_text)
    reply_text = re.sub(r'Ｎ([ａｅｉｏｕＡＥＩＯＵ])', r'Ｎｙ\1', reply_text)
    
    # Replace exclamation marks with random faces
    reply_text = re.sub(r'[!！]+', ' ' + random.choice(faces), reply_text)
    
    # Replace ove with uv
    reply_text = reply_text.replace("ove", "uv")
    reply_text = reply_text.replace("ｏｖｅ", "ｕｖ")
    
    # Add random face at the end
    reply_text += ' ' + random.choice(faces)
    
    return reply_text
  
def copypasta_text(text: str):
    emojis = ["😂", "😂", "👌", "✌", "💞", "👍", "👌", "💯", "🎶", "👀", "😂", "👓", "👏", "👐", "🍕", "💥", "🍴", "💦", "💦", "🍑", "🍆", "😩", "😏", "👉👌", "👀", "👅", "😩", "🚰"]
    reply_text = random.choice(emojis)
    b_char = random.choice(text).lower() # choose a random character in the message to be substituted with 🅱️
    for c in text:
        if c == " ":
            reply_text += random.choice(emojis)
        elif c in emojis:
            reply_text += c
            reply_text += random.choice(emojis)
        elif c.lower() == b_char:
            reply_text += "🅱️"
        else:
            if bool(random.getrandbits(1)):
                reply_text += c.upper()
            else:
                reply_text += c.lower()
    reply_text += random.choice(emojis)
    return reply_text


def is_url(text):
    url_pattern = re.compile(r'http(s)?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+')
    return url_pattern.match(text) is not None

def UserId() -> str:
    return str(uuid.uuid4())

def search_text(pattern: str, text: str):
    return bool(re.search(pattern, text, re.IGNORECASE))

def match_text(pattern: str, text: str):
    return bool(re.match(pattern, text, re.IGNORECASE))

def generate_random_string(length: int = 10) -> str:
    characters = string.ascii_letters  # Contains both lowercase and uppercase letters
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string

async def check_membership(chat_id: [str,int], user_id: int) -> bool:
      try:
          info = await pbot.get_chat_member(chat_id=chat_id, user_id=user_id)
          status = enums.ChatMemberStatus
          if info.status not in (status.LEFT, status.BANNED, status.RESTRICTED):
                return True
          return False
      except Exception: 
          return False
        


def markdown_to_html(text: str) -> str:
    """
    Converts basic Markdown into HTML tags for Pyrogram.
    Supported:
    - **bold** => <b>
    - `code` => <code>
    - ```pre``` => <pre>
    """
    if not text:
        return ""

    # Convert ```pre``` blocks
    text = re.sub(r"```(.*?)```", r"<pre>\1</pre>", text, flags=re.DOTALL)

    # Convert inline `code`
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    # Convert bold **text**
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)

    return text


def file_best_name(names: list) -> str:
    # Join all names with newlines
    names_str = "\n".join(names)
    
    # Single regex pattern to match both quality and size
    # Captures full line containing both patterns
    both_pattern = r'^.*\d+p.*\s+\d+(?:\.\d+)?\s*(?:mb|gb|kb).*$'
    
    # Try to find lines with both patterns
    matches = re.findall(both_pattern, names_str, re.IGNORECASE | re.MULTILINE)
    if matches:
        return matches[0]  # Return first match with both patterns
        
    # If no matches with both, try to find quality only
    quality_pattern = r'^.*\d+p.*$'
    quality_matches = re.findall(quality_pattern, names_str, re.IGNORECASE | re.MULTILINE)
    if quality_matches:
        return quality_matches[0]
        
    # If no quality matches, try to find size only
    size_pattern = r'^.*\s+\d+(?:\.\d+)?\s*(?:mb|gb|kb).*$'
    size_matches = re.findall(size_pattern, names_str, re.IGNORECASE | re.MULTILINE)
    if size_matches:
        return size_matches[0]
    
    # If nothing found, return random choice
    return random.choice(names)


async def autofilter_send_file(bot, text, chat_id, file):
        file_type = file['file_type']
        method = bot.send_video if file_type == 'video' else bot.send_document if file_type == "document" else bot.send_audio
        time = config.AF_FILE_DEL_TIME
        text = "📛 <b>File Names</b>:\n" + "\n".join(f"<code>{name}</code>" for name in file['file_name']) + f"\n\n👥<b> Share link</b>: <code>https://t.me/{config.BOT_USERNAME[1:]}?start={text}</code>" + f"\n\n<b>By {config.BOT_USERNAME}</b>" + f"\n\n<blockquote>\nfile will be deleted in {time_formatter(time)}, so forward to somewhere else.</blockquote>" 
        try:
           buttons = InlineKeyboardMarkup(
           [[
                    InlineKeyboardButton(font('📺 Stream Link'), callback_data=f"stream#{chat_id}")
           ]])
           file_message = await method(
              chat_id, 
              file['file_id'],
              caption=text,
              parse_mode=ParseMode.HTML, 
              reply_markup = buttons if config.STREAM_MOD else None
           ) 
           await auto_delete(file_message, time*60)
           return True
        except Exception as e:
           return await bot.send_message(chat_id, f"❌ ERROR: {str(e)}")
                
                           
def fixed_file_name(name:str, file_type:str, file_size:str):
     name = re.sub(r"_|\.|@|#|\(|\)|[|]", " ", name)
     return f"[📁 {file_size}] {file_type} {name}"	

def get_size(size):
    """Get size in readable format"""

    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    text = "%.2f %s" % (size, units[i])
    return text.upper()


def convert_greetings_text(text, user, chat):
    user_full_name = user.full_name if user.full_name else "User "
    chat_title = chat.title if chat.title else "Chat"
    
    result = text.replace('{name}', user_full_name).replace("{chat}", chat_title).replace("{chat_id}", str(chat.id)).replace('{mention}', user.mention_markdown()).replace('{user_id}', str(user.id)).replace('{first_name}', user.first_name).replace('**', '*')
    return result

def split_message(message, max_length: int = 4000):
    return [message[i:i + max_length] for i in range(0, len(message), max_length)]

def get_ua() -> str:
    with open("./AloneX/helpers/data/UserAgent.json") as file:
          data = json.load(file)
          return random.choice(data)
  
def get_as_document(text_string: str, ext: str = "txt"):
    filename = f"{uuid.uuid4()}.{ext}"
    file = io.BytesIO(str.encode(text_string))
    file.name = filename
    return file
    
def decode_to_base64(input_string):
    """ Decode a base64 Encoded String """
    try:
        decoded_bytes = base64.b64decode(input_string)
        decoded_string = decoded_bytes.decode('utf-8')
        return decoded_string
    except UnicodeDecodeError:
        return "Error: Decoded bytes don't represent a valid UTF-8 string."
    except Exception as e:
        return f"An error occurred: {str(e)}"

def encode_to_base64(input_string):
    """Encode a string to Base64"""
    encoded_string = base64.b64encode(input_string.encode('utf-8')).decode('utf-8')
    return encoded_string

def is_base64_encoded(input_string):
    """Check if a string is Base64 encoded"""
    try:
        base64.b64decode(input_string)
        return True
    except Exception:
        return False
      
def get_message_link(message) -> str:
    '''
    Info:
      Takes chat id and message id.
      returns a share link of message id.
    '''

    chat = message.chat
    message_id = message.message_id
  
    if chat.type == ChatType.PRIVATE:
        chat = message.from_user
        link = f"tg://openmessage?user_id={chat.id}&message_id={message_id}"
    else:
       if not getattr(chat, 'username', None):
           chat_id = str(chat.id)
           if chat_id.startswith('-'):
                chat_id = int(chat_id.split('-')[1])
           link = f"https://t.me/c/{chat_id}/{message_id}"
       else:
           link = f"https://t.me/{chat.username}/{message_id}"
         
    return link
         



def get_media(bot, message):
    media_types = {
        'photo': (message.photo, bot.send_photo),
        'animation': (message.animation, bot.send_animation),
        'document': (message.document, bot.send_document),
        'sticker': (message.sticker, bot.send_sticker),
        'audio': (message.audio, bot.send_audio)
    }
    
    for media_type, media in media_types.items():
        if media[0]:
            if media_type == 'photo':
                return media_type, media[0][-1].file_id, media[1]
            else:
                return media_type, media[0].file_id, media[1]
    
    return None, None, None


def get_media_id(message):
    '''
    Info: 
      returns a tuple of (type, file_id) of any media in
      message if no media will return (None, None)
    '''
    
    media_types = {
        'photo': message.photo,
        'animation': message.animation,
        'document': message.document,
        'sticker': message.sticker,
        'voice': message.voice,
        'audio': message.audio
    }
    
    for media_type, media in media_types.items():
        if media:
            if media_type == 'photo':
                return media_type, media[-1].file_id
            else:
                return media_type, media.file_id
    
    return None, None
  

def get_method_by_type(bot, file_type):
    file_type = file_type.lower()
    types = {
           'photo': bot.send_photo,
           'video': bot.send_video,
           'audio': bot.send_audio,
           'text': bot.send_message,
           'document': bot.send_document,
           'animation': bot.send_animation,
    }
    return types[file_type]
       
async def extract_user(message, self: bool = True) -> int:
    user_id = None

    try:
        if message.text and len(message.text.strip().split()) >= 2:
            second_word = message.text.strip().split()[1]

            if second_word.startswith('@'):
                username = second_word[1:]
                try:
                    user = await pbot.get_users(username)
                    if user and hasattr(user, 'id'):
                        user_id = user.id
                except Exception:
                    try:
                        from AloneX.db.users import get_user_id_by_username
                        user_id = await get_user_id_by_username(username)
                    except Exception:
                        pass

            elif second_word.isdigit():
                user_id = int(second_word)

        if not user_id and message.entities:
            for entity in message.entities:
                if entity.type == MessageEntityType.TEXT_MENTION and entity.user:
                    user_id = entity.user.id
                    break
                elif entity.type == MessageEntityType.MENTION:
                    username = message.text[entity.offset:entity.offset + entity.length].lstrip('@')
                    try:
                        user = await pbot.get_users(username)
                        if user and hasattr(user, 'id'):
                            user_id = user.id
                            break
                    except Exception:
                        try:
                            from AloneX.db.users import get_user_id_by_username
                            user_id = await get_user_id_by_username(username)
                            if user_id:
                                break
                        except Exception:
                            pass

        if not user_id and message.reply_to_message and message.reply_to_message.from_user:
            user_id = message.reply_to_message.from_user.id

        if not user_id and self and message.from_user:
            user_id = message.from_user.id

    except Exception as e:
        print(f"❌ [extract_user] Exception: {e}")
        return None

    return user_id
     
Langs = {
    "ab":{
        "name":"Abkhaz",
        "nativeName":"аҧсуа"
    },
    "aa":{
        "name":"Afar",
        "nativeName":"Afaraf"
    },
    "af":{
        "name":"Afrikaans",
        "nativeName":"Afrikaans"
    },
    "ak":{
        "name":"Akan",
        "nativeName":"Akan"
    },
    "sq":{
        "name":"Albanian",
        "nativeName":"Shqip"
    },
    "am":{
        "name":"Amharic",
        "nativeName":"አማርኛ"
    },
    "ar":{
        "name":"Arabic",
        "nativeName":"العربية"
    },
    "an":{
        "name":"Aragonese",
        "nativeName":"Aragonés"
    },
    "hy":{
        "name":"Armenian",
        "nativeName":"Հայերեն"
    },
    "as":{
        "name":"Assamese",
        "nativeName":"অসমীয়া"
    },
    "av":{
        "name":"Avaric",
        "nativeName":"авар мацӀ, магӀарул мацӀ"
    },
    "ae":{
        "name":"Avestan",
        "nativeName":"avesta"
    },
    "ay":{
        "name":"Aymara",
        "nativeName":"aymar aru"
    },
    "az":{
        "name":"Azerbaijani",
        "nativeName":"azərbaycan dili"
    },
    "bm":{
        "name":"Bambara",
        "nativeName":"bamanankan"
    },
    "ba":{
        "name":"Bashkir",
        "nativeName":"башҡорт теле"
    },
    "eu":{
        "name":"Basque",
        "nativeName":"euskara, euskera"
    },
    "be":{
        "name":"Belarusian",
        "nativeName":"Беларуская"
    },
    "bn":{
        "name":"Bengali",
        "nativeName":"বাংলা"
    },
    "bh":{
        "name":"Bihari",
        "nativeName":"भोजपुरी"
    },
    "bi":{
        "name":"Bislama",
        "nativeName":"Bislama"
    },
    "bs":{
        "name":"Bosnian",
        "nativeName":"bosanski jezik"
    },
    "br":{
        "name":"Breton",
        "nativeName":"brezhoneg"
    },
    "bg":{
        "name":"Bulgarian",
        "nativeName":"български език"
    },
    "my":{
        "name":"Burmese",
        "nativeName":"ဗမာစာ"
    },
    "ca":{
        "name":"Catalan; Valencian",
        "nativeName":"Català"
    },
    "ch":{
        "name":"Chamorro",
        "nativeName":"Chamoru"
    },
    "ce":{
        "name":"Chechen",
        "nativeName":"нохчийн мотт"
    },
    "ny":{
        "name":"Chichewa; Chewa; Nyanja",
        "nativeName":"chiCheŵa, chinyanja"
    },
    "zh":{
        "name":"Chinese",
        "nativeName":"中文 (Zhōngwén), 汉语, 漢語"
    },
    "cv":{
        "name":"Chuvash",
        "nativeName":"чӑваш чӗлхи"
    },
    "kw":{
        "name":"Cornish",
        "nativeName":"Kernewek"
    },
    "co":{
        "name":"Corsican",
        "nativeName":"corsu, lingua corsa"
    },
    "cr":{
        "name":"Cree",
        "nativeName":"ᓀᐦᐃᔭᐍᐏᐣ"
    },
    "hr":{
        "name":"Croatian",
        "nativeName":"hrvatski"
    },
    "cs":{
        "name":"Czech",
        "nativeName":"česky, čeština"
    },
    "da":{
        "name":"Danish",
        "nativeName":"dansk"
    },
    "dv":{
        "name":"Divehi; Dhivehi; Maldivian;",
        "nativeName":"ދިވެހި"
    },
    "nl":{
        "name":"Dutch",
        "nativeName":"Nederlands, Vlaams"
    },
    "en":{
        "name":"English",
        "nativeName":"English"
    },
    "eo":{
        "name":"Esperanto",
        "nativeName":"Esperanto"
    },
    "et":{
        "name":"Estonian",
        "nativeName":"eesti, eesti keel"
    },
    "ee":{
        "name":"Ewe",
        "nativeName":"Eʋegbe"
    },
    "fo":{
        "name":"Faroese",
        "nativeName":"føroyskt"
    },
    "fj":{
        "name":"Fijian",
        "nativeName":"vosa Vakaviti"
    },
    "fi":{
        "name":"Finnish",
        "nativeName":"suomi, suomen kieli"
    },
    "fr":{
        "name":"French",
        "nativeName":"français, langue française"
    },
    "ff":{
        "name":"Fula; Fulah; Pulaar; Pular",
        "nativeName":"Fulfulde, Pulaar, Pular"
    },
    "gl":{
        "name":"Galician",
        "nativeName":"Galego"
    },
    "ka":{
        "name":"Georgian",
        "nativeName":"ქართული"
    },
    "de":{
        "name":"German",
        "nativeName":"Deutsch"
    },
    "el":{
        "name":"Greek, Modern",
        "nativeName":"Ελληνικά"
    },
    "gn":{
        "name":"Guaraní",
        "nativeName":"Avañeẽ"
    },
    "gu":{
        "name":"Gujarati",
        "nativeName":"ગુજરાતી"
    },
    "ht":{
        "name":"Haitian; Haitian Creole",
        "nativeName":"Kreyòl ayisyen"
    },
    "ha":{
        "name":"Hausa",
        "nativeName":"Hausa, هَوُسَ"
    },
    "he":{
        "name":"Hebrew (modern)",
        "nativeName":"עברית"
    },
    "hz":{
        "name":"Herero",
        "nativeName":"Otjiherero"
    },
    "hi":{
        "name":"Hindi",
        "nativeName":"हिन्दी, हिंदी"
    },
    "ho":{
        "name":"Hiri Motu",
        "nativeName":"Hiri Motu"
    },
    "hu":{
        "name":"Hungarian",
        "nativeName":"Magyar"
    },
    "ia":{
        "name":"Interlingua",
        "nativeName":"Interlingua"
    },
    "id":{
        "name":"Indonesian",
        "nativeName":"Bahasa Indonesia"
    },
    "ie":{
        "name":"Interlingue",
        "nativeName":"Originally called Occidental; then Interlingue after WWII"
    },
    "ga":{
        "name":"Irish",
        "nativeName":"Gaeilge"
    },
    "ig":{
        "name":"Igbo",
        "nativeName":"Asụsụ Igbo"
    },
    "ik":{
        "name":"Inupiaq",
        "nativeName":"Iñupiaq, Iñupiatun"
    },
    "io":{
        "name":"Ido",
        "nativeName":"Ido"
    },
    "is":{
        "name":"Icelandic",
        "nativeName":"Íslenska"
    },
    "it":{
        "name":"Italian",
        "nativeName":"Italiano"
    },
    "iu":{
        "name":"Inuktitut",
        "nativeName":"ᐃᓄᒃᑎᑐᑦ"
    },
    "ja":{
        "name":"Japanese",
        "nativeName":"日本語 (にほんご／にっぽんご)"
    },
    "jv":{
        "name":"Javanese",
        "nativeName":"basa Jawa"
    },
    "kl":{
        "name":"Kalaallisut, Greenlandic",
        "nativeName":"kalaallisut, kalaallit oqaasii"
    },
    "kn":{
        "name":"Kannada",
        "nativeName":"ಕನ್ನಡ"
    },
    "kr":{
        "name":"Kanuri",
        "nativeName":"Kanuri"
    },
    "ks":{
        "name":"Kashmiri",
        "nativeName":"कश्मीरी, كشميري‎"
    },
    "kk":{
        "name":"Kazakh",
        "nativeName":"Қазақ тілі"
    },
    "km":{
        "name":"Khmer",
        "nativeName":"ភាសាខ្មែរ"
    },
    "ki":{
        "name":"Kikuyu, Gikuyu",
        "nativeName":"Gĩkũyũ"
    },
    "rw":{
        "name":"Kinyarwanda",
        "nativeName":"Ikinyarwanda"
    },
    "ky":{
        "name":"Kirghiz, Kyrgyz",
        "nativeName":"кыргыз тили"
    },
    "kv":{
        "name":"Komi",
        "nativeName":"коми кыв"
    },
    "kg":{
        "name":"Kongo",
        "nativeName":"KiKongo"
    },
    "ko":{
        "name":"Korean",
        "nativeName":"한국어 (韓國語), 조선말 (朝鮮語)"
    },
    "ku":{
        "name":"Kurdish",
        "nativeName":"Kurdî, كوردی‎"
    },
    "kj":{
        "name":"Kwanyama, Kuanyama",
        "nativeName":"Kuanyama"
    },
    "la":{
        "name":"Latin",
        "nativeName":"latine, lingua latina"
    },
    "lb":{
        "name":"Luxembourgish, Letzeburgesch",
        "nativeName":"Lëtzebuergesch"
    },
    "lg":{
        "name":"Luganda",
        "nativeName":"Luganda"
    },
    "li":{
        "name":"Limburgish, Limburgan, Limburger",
        "nativeName":"Limburgs"
    },
    "ln":{
        "name":"Lingala",
        "nativeName":"Lingála"
    },
    "lo":{
        "name":"Lao",
        "nativeName":"ພາສາລາວ"
    },
    "lt":{
        "name":"Lithuanian",
        "nativeName":"lietuvių kalba"
    },
    "lu":{
        "name":"Luba-Katanga",
        "nativeName":""
    },
    "lv":{
        "name":"Latvian",
        "nativeName":"latviešu valoda"
    },
    "gv":{
        "name":"Manx",
        "nativeName":"Gaelg, Gailck"
    },
    "mk":{
        "name":"Macedonian",
        "nativeName":"македонски јазик"
    },
    "mg":{
        "name":"Malagasy",
        "nativeName":"Malagasy fiteny"
    },
    "ms":{
        "name":"Malay",
        "nativeName":"bahasa Melayu, بهاس ملايو‎"
    },
    "ml":{
        "name":"Malayalam",
        "nativeName":"മലയാളം"
    },
    "mt":{
        "name":"Maltese",
        "nativeName":"Malti"
    },
    "mi":{
        "name":"Māori",
        "nativeName":"te reo Māori"
    },
    "mr":{
        "name":"Marathi (Marāṭhī)",
        "nativeName":"मराठी"
    },
    "mh":{
        "name":"Marshallese",
        "nativeName":"Kajin M̧ajeļ"
    },
    "mn":{
        "name":"Mongolian",
        "nativeName":"монгол"
    },
    "na":{
        "name":"Nauru",
        "nativeName":"Ekakairũ Naoero"
    },
    "nv":{
        "name":"Navajo, Navaho",
        "nativeName":"Diné bizaad, Dinékʼehǰí"
    },
    "nb":{
        "name":"Norwegian Bokmål",
        "nativeName":"Norsk bokmål"
    },
    "nd":{
        "name":"North Ndebele",
        "nativeName":"isiNdebele"
    },
    "ne":{
        "name":"Nepali",
        "nativeName":"नेपाली"
    },
    "ng":{
        "name":"Ndonga",
        "nativeName":"Owambo"
    },
    "nn":{
        "name":"Norwegian Nynorsk",
        "nativeName":"Norsk nynorsk"
    },
    "no":{
        "name":"Norwegian",
        "nativeName":"Norsk"
    },
    "ii":{
        "name":"Nuosu",
        "nativeName":"ꆈꌠ꒿ Nuosuhxop"
    },
    "nr":{
        "name":"South Ndebele",
        "nativeName":"isiNdebele"
    },
    "oc":{
        "name":"Occitan",
        "nativeName":"Occitan"
    },
    "oj":{
        "name":"Ojibwe, Ojibwa",
        "nativeName":"ᐊᓂᔑᓈᐯᒧᐎᓐ"
    },
    "cu":{
        "name":"Old Church Slavonic, Church Slavic, Church Slavonic, Old Bulgarian, Old Slavonic",
        "nativeName":"ѩзыкъ словѣньскъ"
    },
    "om":{
        "name":"Oromo",
        "nativeName":"Afaan Oromoo"
    },
    "or":{
        "name":"Oriya",
        "nativeName":"ଓଡ଼ିଆ"
    },
    "os":{
        "name":"Ossetian, Ossetic",
        "nativeName":"ирон æвзаг"
    },
    "pa":{
        "name":"Panjabi, Punjabi",
        "nativeName":"ਪੰਜਾਬੀ, پنجابی‎"
    },
    "pi":{
        "name":"Pāli",
        "nativeName":"पाऴि"
    },
    "fa":{
        "name":"Persian",
        "nativeName":"فارسی"
    },
    "pl":{
        "name":"Polish",
        "nativeName":"polski"
    },
    "ps":{
        "name":"Pashto, Pushto",
        "nativeName":"پښتو"
    },
    "pt":{
        "name":"Portuguese",
        "nativeName":"Português"
    },
    "qu":{
        "name":"Quechua",
        "nativeName":"Runa Simi, Kichwa"
    },
    "rm":{
        "name":"Romansh",
        "nativeName":"rumantsch grischun"
    },
    "rn":{
        "name":"Kirundi",
        "nativeName":"kiRundi"
    },
    "ro":{
        "name":"Romanian, Moldavian, Moldovan",
        "nativeName":"română"
    },
    "ru":{
        "name":"Russian",
        "nativeName":"русский язык"
    },
    "sa":{
        "name":"Sanskrit (Saṁskṛta)",
        "nativeName":"संस्कृतम्"
    },
    "sc":{
        "name":"Sardinian",
        "nativeName":"sardu"
    },
    "sd":{
        "name":"Sindhi",
        "nativeName":"सिन्धी, سنڌي، سندھی‎"
    },
    "se":{
        "name":"Northern Sami",
        "nativeName":"Davvisámegiella"
    },
    "sm":{
        "name":"Samoan",
        "nativeName":"gagana faa Samoa"
    },
    "sg":{
        "name":"Sango",
        "nativeName":"yângâ tî sängö"
    },
    "sr":{
        "name":"Serbian",
        "nativeName":"српски језик"
    },
    "gd":{
        "name":"Scottish Gaelic; Gaelic",
        "nativeName":"Gàidhlig"
    },
    "sn":{
        "name":"Shona",
        "nativeName":"chiShona"
    },
    "si":{
        "name":"Sinhala, Sinhalese",
        "nativeName":"සිංහල"
    },
    "sk":{
        "name":"Slovak",
        "nativeName":"slovenčina"
    },
    "sl":{
        "name":"Slovene",
        "nativeName":"slovenščina"
    },
    "so":{
        "name":"Somali",
        "nativeName":"Soomaaliga, af Soomaali"
    },
    "st":{
        "name":"Southern Sotho",
        "nativeName":"Sesotho"
    },
    "es":{
        "name":"Spanish; Castilian",
        "nativeName":"español, castellano"
    },
    "su":{
        "name":"Sundanese",
        "nativeName":"Basa Sunda"
    },
    "sw":{
        "name":"Swahili",
        "nativeName":"Kiswahili"
    },
    "ss":{
        "name":"Swati",
        "nativeName":"SiSwati"
    },
    "sv":{
        "name":"Swedish",
        "nativeName":"svenska"
    },
    "ta":{
        "name":"Tamil",
        "nativeName":"தமிழ்"
    },
    "te":{
        "name":"Telugu",
        "nativeName":"తెలుగు"
    },
    "tg":{
        "name":"Tajik",
        "nativeName":"тоҷикӣ, toğikī, تاجیکی‎"
    },
    "th":{
        "name":"Thai",
        "nativeName":"ไทย"
    },
    "ti":{
        "name":"Tigrinya",
        "nativeName":"ትግርኛ"
    },
    "bo":{
        "name":"Tibetan Standard, Tibetan, Central",
        "nativeName":"བོད་ཡིག"
    },
    "tk":{
        "name":"Turkmen",
        "nativeName":"Türkmen, Түркмен"
    },
    "tl":{
        "name":"Tagalog",
        "nativeName":"Wikang Tagalog, ᜏᜒᜃᜅ᜔ ᜆᜄᜎᜓᜄ᜔"
    },
    "tn":{
        "name":"Tswana",
        "nativeName":"Setswana"
    },
    "to":{
        "name":"Tonga (Tonga Islands)",
        "nativeName":"faka Tonga"
    },
    "tr":{
        "name":"Turkish",
        "nativeName":"Türkçe"
    },
    "ts":{
        "name":"Tsonga",
        "nativeName":"Xitsonga"
    },
    "tt":{
        "name":"Tatar",
        "nativeName":"татарча, tatarça, تاتارچا‎"
    },
    "tw":{
        "name":"Twi",
        "nativeName":"Twi"
    },
    "ty":{
        "name":"Tahitian",
        "nativeName":"Reo Tahiti"
    },
    "ug":{
        "name":"Uighur, Uyghur",
        "nativeName":"Uyƣurqə, ئۇيغۇرچە‎"
    },
    "uk":{
        "name":"Ukrainian",
        "nativeName":"українська"
    },
    "ur":{
        "name":"Urdu",
        "nativeName":"اردو"
    },
    "uz":{
        "name":"Uzbek",
        "nativeName":"zbek, Ўзбек, أۇزبېك‎"
    },
    "ve":{
        "name":"Venda",
        "nativeName":"Tshivenḓa"
    },
    "vi":{
        "name":"Vietnamese",
        "nativeName":"Tiếng Việt"
    },
    "vo":{
        "name":"Volapük",
        "nativeName":"Volapük"
    },
    "wa":{
        "name":"Walloon",
        "nativeName":"Walon"
    },
    "cy":{
        "name":"Welsh",
        "nativeName":"Cymraeg"
    },
    "wo":{
        "name":"Wolof",
        "nativeName":"Wollof"
    },
    "fy":{
        "name":"Western Frisian",
        "nativeName":"Frysk"
    },
    "xh":{
        "name":"Xhosa",
        "nativeName":"isiXhosa"
    },
    "yi":{
        "name":"Yiddish",
        "nativeName":"ייִדיש"
    },
    "yo":{
        "name":"Yoruba",
        "nativeName":"Yorùbá"
    },
    "za":{
        "name":"Zhuang, Chuang",
        "nativeName":"Saɯ cueŋƅ, Saw cuengh"
    }
}



def find_registration_time(user_id: int) -> Tuple[str, datetime]:
    def parse_registration_time(prefix: str, reg_time: int) -> Tuple[str, datetime]:
        return prefix, datetime.fromtimestamp(reg_time).strftime("%Y/%m/%d")

    user_data = [
        (1000000, 1380326400),  # 2013
        (2768409, 1383264000),
        (7679610, 1388448000),
        (11538514, 1391212000),  # 2014
        (15835244, 1392940000),
        (23646077, 1393459000),
        (38015510, 1393632000),
        (44634663, 1399334000),
        (46145305, 1400198000),
        (54845238, 1411257000),
        (63263518, 1414454000),
        (101260938, 1425600000),  # 2015
        (101323197, 1426204000),
        (103151531, 1433376000),
        (103258382, 1432771000),
        (109393468, 1439078000),
        (111220210, 1429574000),
        (112594714, 1439683000),
        (116812045, 1437696000),
        (122600695, 1437782000),
        (124872445, 1439856000),
        (125828524, 1444003000),
        (130029930, 1441324000),
        (133909606, 1444176000),
        (143445125, 1448928000),
        (148670295, 1452211000),  # 2016
        (152079341, 1453420000),
        (157242073, 1446768000),
        (171295414, 1457481000),
        (181783990, 1460246000),
        (222021233, 1465344000),
        (225034354, 1466208000),
        (278941742, 1473465000),
        (285253072, 1476835000),
        (294851037, 1479600000),
        (297621225, 1481846000),
        (328594461, 1482969000),
        (337808429, 1487707000),  # 2017
        (341546272, 1487782000),
        (352940995, 1487894000),
        (369669043, 1490918000),
        (400169472, 1501459000),
        (616816630, 1529625600),  # 2018
        (681896077, 1532821500),
        (727572658, 1543708800),
        (796147074, 1541371800),
        (925078064, 1563290000),  # 2019
        (928636984, 1581513420),  # 2020
        (1054883348, 1585674420),
        (1057704545, 1580393640),
        (1145856008, 1586342040),
        (1227964864, 1596127860),
        (1382531194, 1600188120),
        (1658586909, 1613148540),  # 2021
        (1660971491, 1613329440),
        (1692464211, 1615402500),
        (1719536397, 1619293500),
        (1721844091, 1620224820),
        (1772991138, 1617540360),
        (1807942741, 1625520300),
        (1893429550, 1622040000),
        (1972424006, 1631669400),
        (1974255900, 1634000000),
        (2030606431, 1631992680),
        (2041327411, 1631989620),
        (2078711279, 1634321820),
        (2104178931, 1638353220),
        (2120496865, 1636714020),
        (2123596685, 1636503180),
        (2138472342, 1637590800),
        (3318845111, 1618028800),
        (4317845111, 1620028800),
        (5162494923, 1652449800),  # 2022
        (5186883095, 1648764360),
        (5304951856, 1656718440),
        (5317829834, 1653152820),
        (5318092331, 1652024220),
        (5336336790, 1646368100),
        (5362593868, 1652024520),
        (5387234031, 1662137700),
        (5396587273, 1648014800),
        (5409444610, 1659025020),
        (5416026704, 1660925460),
        (5465223076, 1661710860),
        (5480654757, 1660926300),
        (5499934702, 1662130740),
        (5513192189, 1659626400),
        (5522237606, 1654167240),
        (5537251684, 1664269800),
        (5559167331, 1656718560),
        (5568348673, 1654642200),
        (5591759222, 1659025500),
        (5608562550, 1664012820),
        (5614111200, 1661780160),
        (5666819340, 1664112240),
        (5684254605, 1662134040),
        (5684689868, 1661304720),
        (5707112959, 1663803300),
        (5756095415, 1660925940),
        (5772670706, 1661539140),
        (5778063231, 1667477640),
        (5802242180, 1671821040),
        (5853442730, 1674866100),  # 2023
        (5859878513, 1673117760),
        (5885964106, 1671081840),
        (5982648124, 1686941700),
        (6020888206, 1675534800),
        (6032606998, 1686998640),
        (6057123350, 1676198350),
        (6058560984, 1686907980),
        (6101607245, 1686830760),
        (6108011341, 1681032060),
        (6132325730, 1692033840),
        (6182056052, 1687870740),
        (6279839148, 1688399160),
        (6306077724, 1692442920),
        (6321562426, 1688486760),
        (6364973680, 1696349340),
        (6386727079, 1691696880),
        (6429580803, 1692082680),
        (6527226055, 1690289160),
        (6813121418, 1698489600),
        (6865576492, 1699052400),
        (6925870357, 1701192327),  # 2024
    ]

    user_data.sort(key=lambda x: x[0])

    for i in range(1, len(user_data)):
        if user_id >= user_data[i - 1][0] and user_id <= user_data[i][0]:
            t = (user_id - user_data[i - 1][0]) / (
                user_data[i][0] - user_data[i - 1][0]
            )
            reg_time = int(
                user_data[i - 1][1] + t * (user_data[i][1] - user_data[i - 1][1])
            )
            return parse_registration_time("~", reg_time)

    if user_id <= 1000000:
        return parse_registration_time("<", 1380326400)
    else:
        return parse_registration_time(">", 1701192327)
