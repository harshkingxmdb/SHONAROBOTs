from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InputMediaPhoto
from pyrogram.enums import ButtonStyle
from pyrogram.enums import ParseMode
from AloneX import pbot, OWNER_ID, font
import speedtest
from config import UPDATE_CHANNEL
import aiohttp
import io
import asyncio
import os
import tempfile

def convert(speed):
    return round(int(speed) / 1048576, 2)

async def download_and_validate_image(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/png,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        timeout = aiohttp.ClientTimeout(total=45)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    content = await response.read()
                    content_size = len(content)
                    if content_size < 1000:
                        return None
                    if not content.startswith(b'\x89PNG\r\n\x1a\n'):
                        return None
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                        temp_file.write(content)
                        temp_file.flush()
                        return temp_file.name
                else:
                    return None
    except Exception as e:
        return None

def owner_only(_, __, message):
    return message.from_user and message.from_user.id == OWNER_ID

@pbot.on_message(filters.command("speedtest") & filters.create(owner_only),group=-60)
async def speed_test(_, message):
    buttons = [
        [
            InlineKeyboardButton(font("ɪᴍᴀɢᴇ"), callback_data="speedtest_image", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(font("ᴛᴇxᴛ"), callback_data="speedtest_text", style=ButtonStyle.PRIMARY),
        ]
    ]
    await message.reply_text(font("Select mode for speedtest:"), reply_markup=InlineKeyboardMarkup(buttons))

@pbot.on_callback_query(filters.regex("^speedtest"))
async def callback_handler(_, query: CallbackQuery):
    if not query.from_user or query.from_user.id != OWNER_ID:
        await query.answer(font("❌ Only the owner can use this."), show_alert=True)
        return
    data = query.data
    if data == "speedtest_close":
        await query.message.delete()
        return
    mode = "text" if "text" in data else "image"
    await query.message.edit_text(font("⚡ Running speedtest... ⏳"))
    temp_file_path = None
    try:
        loop = asyncio.get_event_loop()
        def run_speedtest():
            speed = speedtest.Speedtest()
            speed.get_best_server()
            speed.download()
            speed.upload()
            return speed
        speed = await loop.run_in_executor(None, run_speedtest)
        result = speed.results.dict()
        download_mb = convert(result['download'])
        upload_mb = convert(result['upload'])
        ping_ms = result['ping']
        replymsg = (
            f"📊 **Speedtest Result**\n\n"
            f"📥 **Download:** `{download_mb} MB/s`\n"
            f"📤 **Upload:** `{upload_mb} MB/s`\n"
            f"📡 **Ping:** `{ping_ms} ms`\n"
            f"🌐 **Server:** `{result['server']['name']}`"
        )
        buttons_after_result = [
            [
                InlineKeyboardButton(font("🔄 Refresh"), callback_data=f"speedtest_{mode}", style=ButtonStyle.SUCCESS),
                InlineKeyboardButton(font("❌ Close"), callback_data="speedtest_close", style=ButtonStyle.DANGER),
            ]
        ]
        if mode == "image":
            try:
                speedtest_image_url = speed.results.share()
                if speedtest_image_url:
                    await query.message.edit_text(font("⚡ Downloading speedtest image... 📸"))
                    await asyncio.sleep(5)
                    temp_file_path = await download_and_validate_image(speedtest_image_url)
                    if temp_file_path and os.path.exists(temp_file_path):
                        try:
                            await query.message.reply_photo(
                                photo=temp_file_path,
                                caption=replymsg,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=InlineKeyboardMarkup(buttons_after_result)
                            )
                            await query.message.delete()
                        except Exception:
                            await query.message.edit_text(
                                f"📊 **Speedtest Result**\n"
                                f"🖼️ **Image:** [View Result]({speedtest_image_url})\n\n"
                                f"{replymsg}",
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=InlineKeyboardMarkup(buttons_after_result),
                                disable_web_page_preview=False
                            )
                    else:
                        await query.message.edit_text(
                            f"⚠️ **Image Download Failed**\n"
                            f"Speedtest.net image couldn't be downloaded or is invalid.\n\n"
                            f"**Text Result:**\n{replymsg}",
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=InlineKeyboardMarkup(buttons_after_result)
                        )
                else:
                    await query.message.edit_text(
                        f"⚠️ **No Image Generated**\n"
                        f"Speedtest.net did not generate an image URL.\n\n"
                        f"**Text Result:**\n{replymsg}",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup(buttons_after_result)
                    )
            except Exception as img_error:
                await query.message.edit_text(
                    f"⚠️ **Image Mode Failed**\n"
                    f"Error: `{str(img_error)}`\n\n"
                    f"**Text Result:**\n{replymsg}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(buttons_after_result)
                )
        else:
            await query.message.edit_text(
                replymsg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons_after_result)
            )
    except Exception as e:
        await query.message.edit_text(
            f"❌ **Speedtest Failed**\n"
            f"Error: `{str(e)}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(font("❌ Close"), callback_data="speedtest_close", style=ButtonStyle.DANGER)
            ]])
        )
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass

__HELP__ = """
» /speedtest *:* Runs a speedtest and shows the results.  
» Only the OWNER can use this command.  
» After result, you can Refresh or Close.
"""

__MODULE__ = "𝐒ᴘᴇᴇᴅᴛᴇsᴛ🏎️"
