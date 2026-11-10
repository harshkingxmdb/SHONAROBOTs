import os
import config
import aiohttp
from pyrogram import filters, types, enums
from AloneX import pbot as bot, font
from AloneX.helpers.utils import get_size

# add ptb mime_type here for text documents
EXTENSION = {
    "application/javascript": "js",
    "application/json": "json",
    "text/x-python": "py",
    "text/python": "py",
    "text/html": "html",
    "text/plain": "txt",
    "text/css": "css",
    "text/x-c": "cpp",
}

module = "Gist"

help = (
    "*Commands*:\n"
    "/gist\n\n"
    "/gist <Language: (text/plain)>: reply to text or text document to get Gist URL.\n"
    "(alternative code paster using GitHub Gist Account)\n\n"
    "*Languages*:\n" +
    ''.join(f'{lang},\n' for lang in list(EXTENSION.keys())) +
    "\n*Example*:\n"
    "/gist text/html\n"
    "/gist reply to document\n"
)


@bot.on_message(filters.command('gist') & ~filters.forwarded)
async def gist(_, m: types.Message):
    r = m.reply_to_message
    allowed = (r.document or r.text or r.caption) if r else None
    if not allowed:
        return await m.reply(font("Reply to message text or document ..."))

    msg = await m.reply_text(font("Analyzing Gist ..."))

    content = None
    mime_type = "text/plain"

    if r and r.document and r.document.file_size < 2048000:  # 2MB limit
        try:
            path = await r.download()
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
            os.remove(path)
            mime_type = r.document.mime_type or "text/plain"
        except Exception as e:
            return await msg.edit_text(f"❌ Error processing document: {e}")
    else:
        content = r.text or r.caption
        mime_type = m.text.split()[1] if len(m.text.split()) > 1 else "text/plain"

    if not content:
        return await msg.edit_text(font("❌ *No content found to paste*"), parse_mode="markdown")

    api_url = "https://api.github.com/gists"
    headers = {
        "Authorization": f"Bearer {config.GIST_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    ext = EXTENSION.get(mime_type, 'txt')
    file_name = f"gistfile.{ext}"
    payload = {
        "description": "Gist from Telegram Bot",
        "public": False,
        "files": {
            file_name: {
                "content": str(content)
            }
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, headers=headers, json=payload) as response:
                response_data = await response.json()
                if response.status == 201:
                    files = response_data["files"]
                    paste = files[file_name]
                    gist_url = response_data.get("html_url")
                    raw_url = paste["raw_url"]
                    buttons = types.InlineKeyboardMarkup([[
                        types.InlineKeyboardButton(font("RAW"), url=raw_url, style=enums.ButtonStyle.SUCCESS),
                        types.InlineKeyboardButton(font("URL"), url=gist_url, style=enums.ButtonStyle.SUCCESS)
                    ]])
                    text = (
                        "\n\n"
                        f"Language: ``{paste['language']}``\n"
                        f"Type: ``{paste['type']}``\n"
                        f"Size: ``{get_size(len(content))}``\n"
                    )
                    await msg.edit(text, reply_markup=buttons, parse_mode="markdown")
                else:
                    error_message = response_data.get("message", f"Unknown error: {response.status}")
                    await msg.edit(f"❌ Gist creation failed: {error_message}")
    except Exception as e:
        await msg.edit(f"❌ ERROR: {str(e)}")
