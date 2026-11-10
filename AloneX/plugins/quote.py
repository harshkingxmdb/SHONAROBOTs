__module__ = "𝐐ᴜᴏᴛʟʏ✨"
__help__ = """
*Commands*:
/q
*Description:*
📌 Reply to a message to convert it into a stylish quote sticker.
*Usage:*
❂ `/q [number] [color] [r/reply]` — Quote messages in your preferred style and color
*Available Colors:*
red, blue, green, yellow, pink, purple, white, cream, mint, lavender, grey, black, darkred, darkblue, darkgreen, orange, cyan, magenta, brown, navy, teal, maroon, random
*Examples:*
`/q` — Quote 1 message
`/q 3` — Quote 3 messages
`/q red` — Quote 1 message with red background
`/q 2 blue` — Quote 2 messages with blue background
`/q r` — Quote message WITH reply
`/q 3 r` — Quote 3 messages WITH replies
`/q reply red` — Quote with reply in red background
`/q orange` — Quote with orange background
`/q random` — Quote with random background color
"""

import base64
import os
from random import choice
from telethon import events
from telethon.tl import types
from telethon.utils import get_display_name, get_peer_id
from AloneX import tbot, prefix_cmds, font
import aiohttp
import asyncio

all_col = ["#110022", "#8B0000", "#006400", "#00008B", "#4B0082", "#2F4F4F", "#8B4513", "#483D8B", "#2E8B57", "#B22222", "#FF0000", "#0000FF", "#00FF00", "#FFFF00", "#FF69B4", "#800080", "#FFFFFF", "#FFFDD0", "#98FF98", "#E6E6FA", "#808080", "#FFA500", "#00FFFF", "#FF00FF", "#000080", "#008080", "#800000"]

color_map = {
    "red": "#FF0000", "blue": "#0000FF", "green": "#00FF00", "yellow": "#FFFF00",
    "pink": "#FF69B4", "purple": "#800080", "white": "#FFFFFF", "cream": "#FFFDD0",
    "mint": "#98FF98", "lavender": "#E6E6FA", "grey": "#808080", "black": "#110022",
    "darkred": "#8B0000", "darkblue": "#00008B", "darkgreen": "#006400", "orange": "#FFA500",
    "cyan": "#00FFFF", "magenta": "#FF00FF", "brown": "#8B4513", "navy": "#000080",
    "teal": "#008080", "maroon": "#800000",
}

class Quotly:
    _API = "https://bot.lyo.su/quote/generate"
    _entities = {
        types.MessageEntityPhone: "phone_number",
        types.MessageEntityMention: "mention",
        types.MessageEntityBold: "bold",
        types.MessageEntityCashtag: "cashtag",
        types.MessageEntityStrike: "strikethrough",
        types.MessageEntityHashtag: "hashtag",
        types.MessageEntityEmail: "email",
        types.MessageEntityMentionName: "text_mention",
        types.MessageEntityUnderline: "underline",
        types.MessageEntityUrl: "url",
        types.MessageEntityTextUrl: "text_link",
        types.MessageEntityBotCommand: "bot_command",
        types.MessageEntityCode: "code",
        types.MessageEntityPre: "pre",
        types.MessageEntityCustomEmoji: "custom_emoji",
        types.MessageEntityItalic: "italic",
        types.MessageEntitySpoiler: "spoiler",
    }

    async def _upload_to_catbox(self, file_bytes, filename, mime_type):
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://litterbox.catbox.moe/resources/internals/api.php"
                data = aiohttp.FormData()
                data.add_field('fileToUpload', file_bytes, filename=filename, content_type=mime_type)
                data.add_field('reqtype', 'fileupload')
                data.add_field('time', '72h')
                
                async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        url = await response.text()
                        return url.strip()
            return None
        except Exception as e:
            print(f"Catbox upload error: {e}")
            return None

    async def _convert_sticker_to_image(self, sticker_bytes):
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(sticker_bytes))
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            img.convert('RGB').save(output, "JPEG", quality=90)
            output.seek(0)
            img.close()
            
            return output.getvalue()
        except Exception as e:
            print(f"Sticker conversion error: {e}")
            return None

    async def _format_quote(self, event, reply=None, sender=None, type_="private"):
        reply_data = {}
        if reply:
            reply_sender = None
            try:
                reply_sender = await reply.get_sender()
            except:
                pass
            
            reply_data = {
                "name": get_display_name(reply_sender) if reply_sender else "Deleted Account",
                "text": reply.raw_text or reply.message or "",
                "chatId": reply.chat_id if hasattr(reply, 'chat_id') else 0,
            }

        is_fwd = getattr(event, 'fwd_from', None)
        name = last_name = None

        if sender and hasattr(sender, 'id'):
            id_ = get_peer_id(sender)
            name = get_display_name(sender)
        elif not is_fwd:
            id_ = getattr(event, 'sender_id', 0)
            try:
                sender = await event.get_sender()
                name = get_display_name(sender)
            except:
                sender = None
                name = "Unknown"
        else:
            id_ = sender = None
            name = getattr(is_fwd, 'from_name', 'Unknown')
            if hasattr(is_fwd, 'from_id') and is_fwd.from_id:
                id_ = get_peer_id(is_fwd.from_id)
                try:
                    sender = await event.client.get_entity(id_)
                    name = get_display_name(sender)
                except:
                    pass
        
        if sender and hasattr(sender, "last_name") and sender.last_name:
            last_name = sender.last_name

        entities = []
        if hasattr(event, 'entities') and event.entities:
            for entity in event.entities:
                try:
                    entity_dict = {
                        "type": self._entities.get(type(entity), "unknown"),
                        "offset": entity.offset,
                        "length": entity.length,
                    }
                    
                    if hasattr(entity, 'document_id') and entity.document_id:
                        entity_dict["document_id"] = str(entity.document_id)
                    
                    if hasattr(entity, 'url') and entity.url:
                        entity_dict["url"] = entity.url
                    
                    if hasattr(entity, 'language') and entity.language:
                        entity_dict["language"] = entity.language
                    
                    if hasattr(entity, 'user_id') and entity.user_id:
                        entity_dict["user_id"] = entity.user_id
                    
                    entities.append(entity_dict)
                except:
                    pass

        # हर message के लिए अपना text/caption check करो
        message_text = event.raw_text or event.message or ""
        
        # अगर photo है और caption है तो caption use करो, नहीं तो empty
        has_photo = False
        if hasattr(event, 'media') and event.media:
            if hasattr(event.media, 'photo') and event.media.photo:
                has_photo = True
                # Photo के साथ जो caption है वो ही use करो
                if not message_text:
                    message_text = ""  # Photo without caption

        message = {
            "entities": entities,
            "chatId": id_ or 0,
            "avatar": True,
            "from": {
                "id": id_ or 0,
                "first_name": (name or (getattr(sender, 'first_name', None) if sender else None)) or "Deleted Account",
                "last_name": last_name,
                "username": getattr(sender, 'username', None) if sender else None,
                "language_code": "en",
                "title": name,
                "name": name or "Unknown",
                "type": type_,
            },
            "text": message_text,  # यहाँ हर message का अपना caption/text होगा
            "replyMessage": reply_data,
        }

        if hasattr(event, 'media') and event.media:
            try:
                media_bytes = None
                is_sticker = False
                needs_conversion = False
                
                if hasattr(event.media, 'photo') and event.media.photo:
                    try:
                        media_bytes = await asyncio.wait_for(
                            event.download_media(file=bytes),
                            timeout=20
                        )
                    except:
                        pass
                
                elif hasattr(event.media, 'document') and event.media.document:
                    doc = event.media.document
                    mime_type = getattr(doc, 'mime_type', '')
                    
                    is_sticker_doc = any(isinstance(attr, types.DocumentAttributeSticker) for attr in doc.attributes)
                    is_video_doc = any(isinstance(attr, types.DocumentAttributeVideo) for attr in doc.attributes)
                    is_animated_doc = any(isinstance(attr, types.DocumentAttributeAnimated) for attr in doc.attributes)
                    
                    if is_sticker_doc:
                        if is_animated_doc or mime_type.startswith('video/') or mime_type == 'application/x-tgsticker':
                            if hasattr(doc, 'thumbs') and doc.thumbs:
                                try:
                                    media_bytes = await asyncio.wait_for(
                                        event.download_media(file=bytes, thumb=-1),
                                        timeout=15
                                    )
                                except:
                                    pass
                        else:
                            try:
                                media_bytes = await asyncio.wait_for(
                                    event.download_media(file=bytes),
                                    timeout=20
                                )
                                is_sticker = True
                                needs_conversion = True
                            except:
                                pass
                    
                    elif is_video_doc or is_animated_doc or mime_type.startswith('video/'):
                        if hasattr(doc, 'thumbs') and doc.thumbs:
                            try:
                                media_bytes = await asyncio.wait_for(
                                    event.download_media(file=bytes, thumb=-1),
                                    timeout=15
                                )
                            except:
                                pass
                    
                    else:
                        if hasattr(doc, 'thumbs') and doc.thumbs:
                            try:
                                media_bytes = await asyncio.wait_for(
                                    event.download_media(file=bytes, thumb=-1),
                                    timeout=15
                                )
                            except:
                                pass
                
                if media_bytes:
                    if needs_conversion and is_sticker:
                        converted_bytes = await self._convert_sticker_to_image(media_bytes)
                        if converted_bytes:
                            media_bytes = converted_bytes
                    
                    mime_type = "image/jpeg"
                    filename = f"quote_media_{os.urandom(4).hex()}.jpg"
                    
                    url = await self._upload_to_catbox(media_bytes, filename, mime_type)
                    
                    if url:
                        message["media"] = {"url": url}
                    
            except Exception as e:
                print(f"Media processing error: {e}")
                pass

        return message

    async def create_quotly(self, event, reply=None, bg=None, sender=None, file_name="quote.webp"):
        if not isinstance(event, list):
            event = [event]
        
        if bg and bg.lower() in color_map:
            bg = color_map[bg.lower()]
        elif bg == "random":
            bg = choice(all_col)
        else:
            bg = "#110022"
        
        messages = []
        for message in event:
            try:
                msg = await self._format_quote(message, reply=reply, sender=sender)
                messages.append(msg)
            except Exception as e:
                print(f"Message format error: {e}")
                pass
        
        if not messages:
            raise Exception("No valid messages to quote")
        
        content = {
            "type": "quote",
            "format": "webp",
            "backgroundColor": bg,
            "width": 512,
            "height": 768,
            "scale": 2,
            "messages": messages,
        }
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=40)) as session:
            async with session.post(self._API, json=content) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API returned status {response.status}: {error_text[:100]}")
                request = await response.json()
        
        if not request.get("ok"):
            raise Exception("Failed to create quote")
        
        with open(file_name, "wb") as file:
            image = base64.b64decode(request["result"]["image"])
            file.write(image)
        
        return file_name

quotly = Quotly()

async def quote_handler(event):
    if (hasattr(event, 'is_channel') and event.is_channel and not getattr(event, 'is_group', False)) or getattr(event, 'fwd_from', None):
        return
    
    match = event.pattern_match.group(1).strip() if event.pattern_match.group(1) else ""
    
    if not event.is_reply:
        await event.reply(font("❂ **Please reply to a message to create a quote.**"))
        return

    msg = await event.reply(font("❂ **Creating quote...**"))
    
    try:
        reply = await event.get_reply_message()
        if not reply:
            await msg.edit("❂ **Error: Could not get replied message.**")
            return
            
        replied_to = None
        reply_ = [reply]
        color_choice = None

        if match:
            spli_ = match.split(maxsplit=1)
            
            if spli_[0] in ["r", "reply"]:
                try:
                    replied_to = await reply.get_reply_message()
                except:
                    pass
                match = spli_[1] if len(spli_) > 1 else None
            
            elif spli_[0].isdigit():
                num = int(spli_[0])
                if 1 <= num <= 20:
                    reply_ = []
                    try:
                        for i in range(num):
                            try:
                                m = await event.client.get_messages(event.chat_id, ids=reply.id + i)
                                if m:
                                    reply_.append(m)
                            except:
                                pass
                        
                        if not reply_:
                            reply_ = [reply]
                    except:
                        reply_ = [reply]
                
                match = spli_[1] if len(spli_) > 1 else None
            
            elif spli_[0].lower() in color_map or spli_[0] == "random":
                color_choice = spli_[0].lower()
                match = spli_[1] if len(spli_) > 1 else None

        user = None
        if match:
            match_parts = match.split(maxsplit=1)
            
            if match_parts[0].startswith("@") or match_parts[0].isdigit():
                try:
                    if match_parts[0].startswith("@"):
                        user = await event.client.get_entity(match_parts[0])
                    else:
                        user = await event.client.get_entity(int(match_parts[0]))
                except:
                    pass
                match = match_parts[1] if len(match_parts) == 2 else None
            
            elif match_parts[0].lower() in color_map or match_parts[0] == "random":
                color_choice = match_parts[0].lower()
                match = match_parts[1] if len(match_parts) > 1 else None
            
            else:
                if match_parts[0].lower() in color_map or match_parts[0] == "random":
                    color_choice = match_parts[0].lower()

        await msg.edit("❂ **Processing...**")

        file = await quotly.create_quotly(reply_, bg=color_choice, reply=replied_to, sender=user)
        
        await msg.edit("❂ **Uploading sticker...**")
        
        await event.reply(file=file)
        
        try:
            os.remove(file)
        except:
            pass
        
        await msg.delete()
        
    except asyncio.TimeoutError:
        try:
            await msg.edit("❂ **Error:** `Timeout while processing. Please try again.`")
        except:
            pass
    except Exception as e:
        error_msg = str(e)
        try:
            await msg.edit(f"❂ **Error:** `{error_msg[:100]}`")
        except:
            pass
        print(f"Quote error: {error_msg}")

if "quotely" not in tbot.handlers_loaded:
    tbot.add_event_handler(quote_handler, events.NewMessage(pattern=f"^{prefix_cmds}q(?: |$)(.*)", incoming=True))
    tbot.handlers_loaded.add("quotely")
