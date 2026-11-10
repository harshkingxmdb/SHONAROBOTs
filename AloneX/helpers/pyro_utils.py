import math
import config
import logging
import asyncio
from pyrogram import types, enums, Client
from pyrogram.types import Message
from pyrogram import Client, utils, raw, enums
from pyrogram.session import Session, Auth
from urllib.parse import quote_plus
from pyrogram.file_id import FileId, FileType, ThumbnailSource
from AloneX import pbot as bot, work_loads
from functools import wraps

class InvalidHash(Exception):
    message = "Invalid hash"

class FIleNotFound(Exception):
    message = "File not found"



def no_channel(func):
    @wraps(func)
    async def wrapper(client, message: Message, *args, **kwargs):
        if message.chat.type == enums.ChatType.CHANNEL:
            return  
        return await func(client, message, *args, **kwargs)
    return wrapper


def humanbytes(size):
    # https://stackoverflow.com/a/49361727/4723940
    # 2**10 = 1024
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'
      

async def check_membership(chat_id: [str,int], user_id: int) -> bool:
      try:
          info = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
          status = enums.ChatMemberStatus
          if info.status not in (status.LEFT, status.BANNED, status.RESTRICTED):
                return True
          return False
      except Exception: 
          return False


async def is_admin(chat_id: [str,int], user_id: [int, str]):
       try:
          member = await bot.get_chat_member(chat_id, user_id)
          return bool(member.privileges)
       except Exception as e:
          return False


async def check_admin_rights(chat_id: [str,int], user_id: [int, str], permission: str):
       try:
          member = await bot.get_chat_member(chat_id, user_id)
          if bool(member.privileges):
              return getattr(member.privileges, permission, None)
       except Exception as e:
          return False
       return False



def get_media_from_message(message: Message):
    media_types = (
        "audio",
        "document",
        "photo",
        "sticker",
        "animation",
        "video",
        "voice",
        "video_note",
    )
    for attr in media_types:
        media = getattr(message, attr, None)
        if media:
            return media


def get_hash(media_msg: Message) -> str:
    media = get_media_from_message(media_msg)
    return getattr(media, "file_unique_id", "")[:6]

def get_media_file_size(m):
    media = get_media_from_message(m)
    return getattr(media, "file_size", "None")

def get_name(media_msg: Message) -> str:
    media = get_media_from_message(media_msg)
    return str(getattr(media, "file_name", "None"))

def get_media_mime_type(m):
    media = get_media_from_message(m)
    return getattr(media, "mime_type", "None/unknown")

def gen_link(log_msg):
    watch_link = f"{config.WEB_URL}watch/{log_msg.id}?file_name={quote_plus(get_name(log_msg))}&hash={get_hash(log_msg)}"
    download_link = f"{config.WEB_URL}{log_msg.id}?file_name={quote_plus(get_name(log_msg))}&hash={get_hash(log_msg)}"
    return watch_link, download_link


async def parse_file_id(message: Message) -> [FileId, None]:
    media = get_media_from_message(message)
    if media:
        return FileId.decode(media.file_id)

async def parse_file_unique_id(message: Message) -> [str, None]:
    media = get_media_from_message(message)
    if media:
        return media.file_unique_id


async def get_file_ids(client: Client, chat_id: int, message_id: int) -> [FileId, None]:
    message = await client.get_messages(chat_id, message_id)
      
    if message.empty:
        raise FIleNotFound
          
    media = get_media_from_message(message)
    file_unique_id = await parse_file_unique_id(message)
    file_id = await parse_file_id(message)
    setattr(file_id, "file_size", getattr(media, "file_size", 0))
    setattr(file_id, "mime_type", getattr(media, "mime_type", ""))
    setattr(file_id, "file_name", getattr(media, "file_name", ""))
    setattr(file_id, "unique_id", file_unique_id)
    return file_id
      

async def chunk_size(length):
    return 2 ** max(min(math.ceil(math.log2(length / 1024)), 10), 2) * 1024


async def offset_fix(offset, chunksize):
    offset -= offset % chunksize
    return offset


class ByteStreamer:
    def __init__(self, client: Client):
        """A custom class that holds the cache of a specific client and class functions.
        attributes:
            client: the client that the cache is for.
            cached_file_ids: a dict of cached file IDs.
            cached_file_properties: a dict of cached file properties.
        
        functions:
            generate_file_properties: returns the properties for a media of a specific message contained in Tuple.
            generate_media_session: returns the media session for the DC that contains the media file.
            yield_file: yield a file from telegram servers for streaming.
            
        This is a modified version of the <https://github.com/eyaadh/megadlbot_oss/blob/master/mega/telegram/utils/custom_download.py>
        Thanks to Eyaadh <https://github.com/eyaadh>
        """
        self.clean_timer = 30 * 60
        self.client: Client = client
        self.cached_file_ids: dict[int, FileId] = {}
        asyncio.create_task(self.clean_cache())

    async def get_file_properties(self, message_id: int) -> FileId:
        """
        Returns the properties of a media of a specific message in a FIleId class.
        if the properties are cached, then it'll return the cached results.
        or it'll generate the properties from the Message ID and cache them.
        """
        if message_id not in self.cached_file_ids:
            await self.generate_file_properties(message_id)
            logging.debug(f"Cached file properties for message with ID {message_id}")
        return self.cached_file_ids[message_id]

    async def generate_file_properties(self, message_id: int) -> FileId:
        """
        Generates the properties of a media file on a specific message.
        returns ths properties in a FIleId class.
        """
        file_id = await get_file_ids(self.client, config.FILE_DB_CHANNEL, message_id)
        logging.debug(f"Generated file ID and Unique ID for message with ID {message_id}")
        if not file_id:
            logging.debug(f"Message with ID {message_id} not found")
            raise FIleNotFound
        self.cached_file_ids[message_id] = file_id
        logging.debug(f"Cached media message with ID {message_id}")
        return self.cached_file_ids[message_id]

    async def generate_media_session(self, client: Client, file_id: FileId) -> Session:
        """
        Generates the media session for the DC that contains the media file.
        This is required for getting the bytes from Telegram servers.
        """

        media_session = client.media_sessions.get(file_id.dc_id, None)

        if media_session is None:
            if file_id.dc_id != await client.storage.dc_id():
                media_session = Session(
                    client,
                    file_id.dc_id,
                    await Auth(
                        client, file_id.dc_id, await client.storage.test_mode()
                    ).create(),
                    await client.storage.test_mode(),
                    is_media=True,
                )
                await media_session.start()

                for _ in range(6):
                    exported_auth = await client.invoke(
                        raw.functions.auth.ExportAuthorization(dc_id=file_id.dc_id)
                    )

                    try:
                        await media_session.invoke(
                            raw.functions.auth.ImportAuthorization(
                                id=exported_auth.id, bytes=exported_auth.bytes
                            )
                        )
                        break
                    except AuthBytesInvalid:
                        logging.debug(
                            f"Invalid authorization bytes for DC {file_id.dc_id}"
                        )
                        continue
                else:
                    await media_session.stop()
                    raise AuthBytesInvalid
            else:
                media_session = Session(
                    client,
                    file_id.dc_id,
                    await client.storage.auth_key(),
                    await client.storage.test_mode(),
                    is_media=True,
                )
                await media_session.start()
            logging.debug(f"Created media session for DC {file_id.dc_id}")
            client.media_sessions[file_id.dc_id] = media_session
        else:
            logging.debug(f"Using cached media session for DC {file_id.dc_id}")
        return media_session


    @staticmethod
    async def get_location(file_id: FileId) -> [
         raw.types.InputPhotoFileLocation,
         raw.types.InputDocumentFileLocation,
         raw.types.InputPeerPhotoFileLocation
    ]:
        """
        Returns the file location for the media file.
        """
        file_type = file_id.file_type

        if file_type == FileType.CHAT_PHOTO:
            if file_id.chat_id > 0:
                peer = raw.types.InputPeerUser(
                    user_id=file_id.chat_id, access_hash=file_id.chat_access_hash
                )
            else:
                if file_id.chat_access_hash == 0:
                    peer = raw.types.InputPeerChat(chat_id=-file_id.chat_id)
                else:
                    peer = raw.types.InputPeerChannel(
                        channel_id=utils.get_channel_id(file_id.chat_id),
                        access_hash=file_id.chat_access_hash,
                    )

            location = raw.types.InputPeerPhotoFileLocation(
                peer=peer,
                volume_id=file_id.volume_id,
                local_id=file_id.local_id,
                big=file_id.thumbnail_source == ThumbnailSource.CHAT_PHOTO_BIG,
            )
        elif file_type == FileType.PHOTO:
            location = raw.types.InputPhotoFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )
        else:
            location = raw.types.InputDocumentFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )
        return location

    async def yield_file(
        self,
        file_id: FileId,
        index: int,
        offset: int,
        first_part_cut: int,
        last_part_cut: int,
        part_count: int,
        chunk_size: int,
    ) -> [str, None]:
        """
        Custom generator that yields the bytes of the media file.
        Modded from <https://github.com/eyaadh/megadlbot_oss/blob/master/mega/telegram/utils/custom_download.py#L20>
        Thanks to Eyaadh <https://github.com/eyaadh>
        """
        client = self.client
        work_loads[index] += 1
        logging.debug(f"Starting to yielding file with client {index}.")
        media_session = await self.generate_media_session(client, file_id)

        current_part = 1

        location = await self.get_location(file_id)

        try:
            r = await media_session.send(
                raw.functions.upload.GetFile(
                    location=location, offset=offset, limit=chunk_size
                ),
            )
            if isinstance(r, raw.types.upload.File):
                while current_part <= part_count:
                    chunk = r.bytes
                    if not chunk:
                        break
                    offset += chunk_size
                    if part_count == 1:
                        yield chunk[first_part_cut:last_part_cut]
                        break
                    if current_part == 1:
                        yield chunk[first_part_cut:]
                    if 1 < current_part <= part_count:
                        yield chunk

                    r = await media_session.send(
                        raw.functions.upload.GetFile(
                            location=location, offset=offset, limit=chunk_size
                        ),
                    )

                    current_part += 1
        except (TimeoutError, AttributeError):
            pass
        finally:
            logging.debug("Finished yielding file with {current_part} parts.")
            work_loads[index] -= 1


    async def clean_cache(self) -> None:
        """
        function to clean the cache to reduce memory usage
        """
        while True:
            await asyncio.sleep(self.clean_timer)
            self.cached_file_ids.clear()
            logging.debug("Cleaned the cache")




