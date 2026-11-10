import os
import zipfile
import subprocess
import shutil
import time
import logging
import traceback
from telegram import Update, constants
from telegram.ext import ContextTypes
from AloneX import app, prefix_cmds, BOT_USERNAME, font
from AloneX.helpers.decorator import Command, sudos_only, only_private
from github import Github
import config

TEMP_DIR = "temp_repos"
os.makedirs(TEMP_DIR, exist_ok=True)

TEMP_CONFIG = {}

def run(cmd, cwd):
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proc.stdout

def safe_rm(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

def config_valid():
    if not TEMP_CONFIG:
        return False
    if time.time() - TEMP_CONFIG.get("timestamp", 0) > 300:
        TEMP_CONFIG.clear()
        return False
    return True


@Command("gitconfig")
@sudos_only
@only_private
async def gitconfig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    if len(context.args) < 3:
        return await m.reply_text(
            "» ᴜsᴀɢᴇ :- `/gitconfig username email token`",
            parse_mode=constants.ParseMode.MARKDOWN
        )
    name = context.args[0]
    email = context.args[1]
    token = context.args[2]
    TEMP_CONFIG.update({"name": name, "email": email, "token": token, "timestamp": time.time()})
    await m.reply_text(font("✅ ɢɪᴛʜᴜʙ ᴄᴏɴꜰɪɢ sᴇᴛ sᴜᴄᴄᴇssғᴜʟʟʏ! (ᴠᴀʟɪᴅ ꜰᴏʀ 5 ᴍɪɴᴜᴛᴇs)"))


@Command(["gitupload", "gt"])
@sudos_only
@only_private
async def gitupload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = update.effective_message
    bot = context.bot

    if len(context.args) < 1:
        return await m.reply_text(
            "» ᴜsᴀɢᴇ :- `/gitupload repo_name private/public branch_name` (ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴢɪᴘ ғɪʟᴇ)",
            parse_mode=constants.ParseMode.MARKDOWN
        )

    if not config_valid():
        return await m.reply_text(font("⚠️ ᴄᴏɴꜰɪɢ ᴇxᴘɪʀᴇᴅ ᴏʀ ɴᴏᴛ sᴇᴛ!\n\n» ᴘʟᴇᴀsᴇ ʀᴜɴ `/gitconfig` ғɪʀsᴛ."))

    GITHUB_NAME = TEMP_CONFIG["name"]
    GITHUB_EMAIL = TEMP_CONFIG["email"]
    GITHUB_TOKEN = TEMP_CONFIG["token"]
    g = Github(GITHUB_TOKEN)

    repo_name = context.args[0]
    visibility = context.args[1].lower() if len(context.args) >= 2 else "public"
    is_private = visibility == "private"
    branch_name = context.args[2] if len(context.args) >= 3 else "main"

    replied = m.reply_to_message
    if not (replied and replied.document and replied.document.file_name.endswith(".zip")):
        return await m.reply_text(font("⚠️ ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴢɪᴘ ғɪʟᴇ!"))

    zip_path = os.path.join(TEMP_DIR, replied.document.file_name)
    extract_root = os.path.join(TEMP_DIR, f"{repo_name}_extract")
    final_path = os.path.join(TEMP_DIR, f"{repo_name}_final")

    safe_rm(zip_path)
    safe_rm(extract_root)
    safe_rm(final_path)


    status = await m.reply_text(font("⏳ ᴘʀᴏᴄᴇssɪɴɢ ʏᴏᴜʀ ʀᴇqᴜᴇsᴛ..."))

    try:
        file = await bot.get_file(replied.document.file_id)
        await file.download_to_drive(custom_path=zip_path)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_root)

        inner_items = os.listdir(extract_root)
        inner_dirs = [d for d in inner_items if os.path.isdir(os.path.join(extract_root, d))]
        inner_files = [f for f in inner_items if os.path.isfile(os.path.join(extract_root, f))]

        if len(inner_dirs) == 1 and not inner_files:
            shutil.move(os.path.join(extract_root, inner_dirs[0]), final_path)
        else:
            shutil.move(extract_root, final_path)

        for root, dirs, _ in os.walk(final_path):
            if ".git" in dirs:
                safe_rm(os.path.join(root, ".git"))

        user = g.get_user()
        repo = user.create_repo(repo_name, private=is_private, description="sᴏᴜʀᴄᴇ ᴄᴏᴅᴇ ᴜᴘʟᴏᴀᴅ ʙʏ :- ᴀʟᴏɴᴇ ᴄᴏᴅᴇʀ", auto_init=False)


        run(["git", "init"], cwd=final_path)
        run(["git", "config", "user.email", GITHUB_EMAIL], cwd=final_path)
        run(["git", "config", "user.name", GITHUB_NAME], cwd=final_path)
        remote_url = repo.clone_url.replace("https://", f"https://{GITHUB_TOKEN}@")
        run(["git", "remote", "add", "origin", remote_url], cwd=final_path)
        run(["git", "add", "."], cwd=final_path)

        status_out = subprocess.run(["git", "status", "--porcelain"], cwd=final_path, text=True, capture_output=True)
        if status_out.stdout.strip():
            run(["git", "commit", "-m", "ᴜᴘʟᴏᴀᴅᴇᴅ-ʙʏ-ᴀʟᴏɴᴇ-ᴄᴏᴅᴇʀ"], cwd=final_path)
        else:
            run(["git", "commit", "--allow-empty", "-m", "ɴᴇᴡ-ᴜᴘᴅᴀᴛᴇ-ʙʏ-ᴀʟᴏɴᴇ-ᴄᴏᴅᴇʀ"], cwd=final_path)

        run(["git", "branch", "-M", branch_name], cwd=final_path)
        run(["git", "push", "-u", "origin", branch_name], cwd=final_path)

    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"[GITHUB UPLOADER ERROR]\n{error_details}")
        safe_rm(zip_path)
        safe_rm(extract_root)
        safe_rm(final_path)
        if status:
            await status.delete()
        return await m.reply_text(f"❌ ᴇʀʀᴏʀ :- `{str(e)}`", parse_mode=constants.ParseMode.MARKDOWN)

    # Cleanup
    safe_rm(zip_path)
    safe_rm(extract_root)
    safe_rm(final_path)
    await status.delete()
    await m.reply_text(
        f"✅ ʀᴇᴘᴏ `{repo_name}` ᴜᴘʟᴏᴀᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!\n\n"
        f"🔒 ᴠɪsɪʙɪʟɪᴛʏ :- `{'Private' if is_private else 'Public'}`\n"
        f"🌿 ʙʀᴀɴᴄʜ :- `{branch_name}`\n\n"
        f"🔗 ᴜʀʟ :- {repo.html_url}",
        parse_mode=constants.ParseMode.MARKDOWN
    )
