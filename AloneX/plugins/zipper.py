from AloneX import font
import zipfile, os, shutil
from AloneX.helpers.decorator import Command, spam_control, disableable
from telegram import constants


__module__ = "𝐙ɪᴘᴘᴇʀ🗜️"

__help__ = """
*Zipper🗜️*

*Description:*  
This module allows you to zip multiple media files into a single archive and unzip existing zip files directly in the chat.

*Commands:*  
❂ `/zip` — Reply to a media file to add it to the zip store.  
❂ `/getzip` — After adding all files, retrieve the final zip archive.  
❂ `/unzip` — Reply to a zip file to extract its contents.

*Examples:*  
`/zip` — Reply to media  
`/getzip` — Get zipped file  
`/unzip` — Reply to zip file
"""

user_temp = {}

def remove_images(image_paths: list = []):
    for path in image_paths:
        try:
            os.remove(path)
        except Exception as e:
              pass

async def get_media_size(message):
    
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
                return media_type, media[-1].file_id, media[-1].file_size
            else:
                return media_type, media.file_id, media.file_size
    
    return None, None, None
  



@Command("unzip")
@disableable("unzip")
@spam_control
async def unzipFile(update, context):
    m = message = update.effective_message
    reply = message.reply_to_message
    user = update.effective_user

    if not reply or not (reply.document and reply.document.mime_type.endswith('zip')):
        return await m.reply_text(font("🙋 <b>Please reply to a ZIP file!</b>"), parse_mode=constants.ParseMode.HTML)

    # File size check
    file_size = reply.document.file_size
    if (file_size / 1024**2) >= 19:
        return await m.reply_text(font("❌ <b>File size too big! Please use ZIP files under 20MB.</b>"), parse_mode=constants.ParseMode.HTML)

    try:
        # Create user-specific temporary directory
        user_dir = f"user_{user.id}_unzip"
        os.makedirs(user_dir, exist_ok=True)

        # Download the ZIP file
        zip_file = await context.bot.get_file(reply.document.file_id)
        zip_path = os.path.join(user_dir, "archive.zip")
        await zip_file.download_to_drive(zip_path)

        # Extract ZIP file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(user_dir)

        # Collect all extracted files (including nested directories)
        files_to_send = []
        for root, _, files in os.walk(user_dir):
            for file in files:
                if file != "archive.zip":  # Skip the original ZIP
                    files_to_send.append(os.path.join(root, file))

        if not files_to_send:
            return await m.reply_text(font("❌ <b>The ZIP file is empty!</b>"), parse_mode=constants.ParseMode.HTML)
            
        status_msg = await m.reply_text(font('⚡ <b>Sending files ...</b>'), parse_mode=constants.ParseMode.HTML)

        # Send files with proper cleanup
        failed_files = []
        for file_path in files_to_send:
            try:
                await m.reply_document(
                    document=open(file_path, 'rb'),
                    filename=os.path.basename(file_path)
                )
            except Exception as e:
                failed_files.append(f"{os.path.basename(file_path)}: {str(e)}")
            finally:
                if open(file_path, 'r').closed is False:
                    open(file_path, 'r').close()

        # Prepare status message
        success_count = len(files_to_send) - len(failed_files)
        status_msg_text = f"✅ <b>Successfully sent {success_count} files unzipped!</b>"
        if failed_files:
            status_msg_text += f"\n❌ <b>Failed to send {len(failed_files)} zipped files</b>:\n" + "\n".join(failed_files)

        await status_msg.edit_text(status_msg_text, parse_mode=constants.ParseMode.HTML)

    except zipfile.BadZipFile:
        await status_msg.edit_text(font("❌ Invalid ZIP file format!"))
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")
    finally:
        # Cleanup temporary files
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)





      

@Command('getzip')
@disableable("getzip")
@spam_control
async def getZipFile(update, context):
    m = message = update.effective_message
    reply = message.reply_to_message
    user = update.effective_user
  
    if not user.id in user_temp:
        return await message.reply_text(
            "🙋 It seems you haven't added any media to zip please use /zip for add media."
        )
    medias = user_temp[user.id].get('files', [])
  
    if not medias:
       return await m.reply_text(font("🤔 No medias found in data."))

    zip_path = f"user_{user.full_name}_file.zip"
    try:
       with zipfile.ZipFile(zip_path, 'w') as zipf:
           write = lambda file: zipf.write(file, os.path.basename(file))
           list(map(write, medias))
    except Exception as e:
        return await m.reply_text(f"❌ Error: {e}")
      
    if (await m.reply_document(zip_path)):
        remove_images(medias)
        medias.clear()
        return os.remove(zip_path)
      
  

@Command('zip')
@disableable("zip")
async def zipFile(update, context):
    m = message = update.effective_message
    reply = message.reply_to_message
    user = update.effective_user


    if not reply or not (reply and (reply.photo or reply.document or reply.animation or reply.audio)):
        return await message.reply_text(font("Reply to a photo/document/gif for convert to zip."))

    type, file_id, file_size = await get_media_size(reply)
    if (int(file_size) / 1024**2) >= 19:
          return await m.reply_text(font("The file size is too big try with only below 20mb media."))
             
    if not user.id in user_temp:
           user_temp.setdefault(user.id, {'files': []})
           file = await (await context.bot.get_file(file_id)).download_to_drive()
           user_temp[user.id]['files'].append(file)
           images = user_temp[user.id].get('files', [])
           await message.reply_text(
               f"⚡ Successfully media {len(images)} added to zip but if you want to add multiply media please continue to use /zip to add more. and after all done, use /getzip to get the zip file."
           )
    else:
        file = await (await context.bot.get_file(file_id)).download_to_drive()
        user_temp[user.id]['files'].append(file)
        images = user_temp[user.id]['files']
        await message.reply_text(
               f"⚡ Successfully media {len(images)} added to zip but if you want to add multiple media please continue to use /zip to add more. and after all done use /getzip to get the zip file."
           )
      
