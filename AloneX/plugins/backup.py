from os import remove, system as execute
from pyrogram import filters, enums
from pyrogram.types import Message
from AloneX import pbot, LOGGER, font
from config import DB_URL, OWNER_ID, prefix_cmds
import zipfile
import os
from pathlib import Path

MODULE = {}
MODULE["Backup"] = {
    "description": "Database backup and restore commands",
    "commands": {
        "backup": "Create a backup of all databases",
        "restore": "Restore databases from backup file",
        "backupinfo": "View backup file contents"
    }
}


def create_zip(source_dir, output_filename):
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                zipf.write(file_path, arcname)


@pbot.on_message(filters.command("backup", prefix_cmds) & filters.user(OWNER_ID), group=118)
async def backup_database(_, message: Message):
    if message.chat.type != enums.ChatType.PRIVATE:
        return await message.reply_text(font("⚠️ Use this command in private chat."))

    m = await message.reply_text(font("🔄 Backing up..."))
    
    try:
        code1 = execute(f'mongodump --uri "{DB_URL}"')
        if int(code1) != 0:
            return await m.edit_text(font("❌ Backup failed! Install mongodump."))
        
        await m.edit_text(font("📦 Compressing..."))
        
        try:
            create_zip("dump", "backup.zip")
        except Exception as e:
            return await m.edit_text(f"❌ Compression failed: {str(e)}")
        
        await message.reply_document(
            document="backup.zip",
            caption="✅ Backup complete"
        )
        
        await m.delete()
        LOGGER.info("✓ Database backup completed")
        
    except Exception as e:
        LOGGER.error(f"Backup error: {e}")
        await m.edit_text(f"❌ Error: {str(e)}")
    
    finally:
        try:
            execute("rm -rf dump/")
            remove("backup.zip")
        except:
            pass


@pbot.on_message(filters.command("backupinfo", prefix_cmds) & filters.user(OWNER_ID), group=119)
async def backup_info(_, message: Message):
    if message.chat.type != enums.ChatType.PRIVATE:
        return await message.reply_text(font("⚠️ Use this command in private chat."))
    
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text(font("❌ Reply to backup.zip file with /backupinfo"))
    
    m = await message.reply_text(font("📥 Checking backup..."))
    
    try:
        file_path = await message.reply_to_message.download(file_name="backup.zip")
        
        if not file_path or not os.path.exists(file_path):
            return await m.edit_text(font("❌ Failed to download backup file"))
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(".")
        except Exception as e:
            return await m.edit_text(f"❌ Invalid backup file: {str(e)}")
        
        databases = []
        collections_info = ""
        
        for root, dirs, files in os.walk("dump"):
            for dir_name in dirs:
                db_path = os.path.join(root, dir_name)
                bson_files = [f for f in os.listdir(db_path) if f.endswith('.bson')]
                if bson_files:
                    databases.append(dir_name)
                    collections_info += f"\n📁 **{dir_name}**\n"
                    for bson_file in bson_files:
                        collection_name = bson_file.replace('.bson', '')
                        file_size = os.path.getsize(os.path.join(db_path, bson_file))
                        size_mb = file_size / (1024 * 1024)
                        collections_info += f"  └ {collection_name} ({size_mb:.2f} MB)\n"
        
        info_text = f"📊 **Backup Information**\n\n"
        info_text += f"**Databases:** {len(databases)}\n"
        info_text += collections_info
        
        await m.edit_text(info_text)
        
    except Exception as e:
        LOGGER.error(f"Backup info error: {e}")
        await m.edit_text(f"❌ Error: {str(e)}")
    
    finally:
        try:
            execute("rm -rf dump/")
            remove("backup.zip")
        except:
            pass


@pbot.on_message(filters.command("restore", prefix_cmds) & filters.user(OWNER_ID), group=120)
async def restore_database(_, message: Message):
    if message.chat.type != enums.ChatType.PRIVATE:
        return await message.reply_text(font("⚠️ Use this command in private chat."))
    
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text(font("❌ Reply to backup.zip file with /restore"))
    
    m = await message.reply_text(font("📥 Downloading backup..."))
    
    try:
        file_path = await message.reply_to_message.download(file_name="backup.zip")
        
        if not file_path or not os.path.exists(file_path):
            return await m.edit_text(font("❌ Failed to download backup file"))
        
        await m.edit_text(font("📦 Extracting..."))
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(".")
        except Exception as e:
            return await m.edit_text(f"❌ Extraction failed: {str(e)}")
        
        await m.edit_text(font("🔄 Restoring databases..."))
        
        code2 = execute(f'mongorestore --uri "{DB_URL}" --drop dump/')
        if int(code2) != 0:
            return await m.edit_text(font("❌ Restore failed!"))
        
        await m.edit_text(font("✅ Restore complete!\nRestart bot: /restart"))
        
        LOGGER.info("✓ Database restored successfully")
        
    except Exception as e:
        LOGGER.error(f"Restore error: {e}")
        await m.edit_text(f"❌ Error: {str(e)}")
    
    finally:
        try:
            execute("rm -rf dump/")
            remove("backup.zip")
        except:
            pass


__mod_name__ = "𝐁ᴀᴄᴋᴜᴘ🔃"
__help__ = """
**Database Backup & Restore**

Owner only commands:

• /backup - Create database backup
• /backupinfo - Check backup contents (reply to backup.zip)
• /restore - Restore from backup (reply to backup.zip)

**Note:** All commands work in private chat only.
"""
