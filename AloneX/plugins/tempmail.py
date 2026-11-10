import random
import string
import aiohttp
from pyrogram import filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ButtonStyle
from AloneX import pbot as app, font

BASE_URL = "https://api.mail.tm"
DOMAINS_API = f"{BASE_URL}/domains"
ACCOUNTS_API = f"{BASE_URL}/accounts"
TOKEN_API = f"{BASE_URL}/token"
MESSAGES_API = f"{BASE_URL}/messages"

user_sessions = {}

def generate_password():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(12))

def generate_username():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(8))

async def fetch_json(url, method="GET", headers=None, json_data=None):
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            if method == "GET":
                async with session.get(url, headers=headers) as resp:
                    if resp.status in [200, 201]:
                        return await resp.json()
            elif method == "POST":
                async with session.post(url, headers=headers, json=json_data) as resp:
                    if resp.status in [200, 201]:
                        return await resp.json()
    except Exception as e:
        print(f"Error: {e}")
    return None

async def get_domains():
    data = await fetch_json(DOMAINS_API)
    if data and "hydra:member" in data:
        return [domain["domain"] for domain in data["hydra:member"]]
    return ["mail.tm"]

async def create_account(email, password):
    data = {"address": email, "password": password}
    return await fetch_json(ACCOUNTS_API, method="POST", json_data=data)

async def get_token(email, password):
    data = {"address": email, "password": password}
    result = await fetch_json(TOKEN_API, method="POST", json_data=data)
    if result and "token" in result:
        return result["token"]
    return None

async def get_messages(token):
    headers = {"Authorization": f"Bearer {token}"}
    data = await fetch_json(MESSAGES_API, headers=headers)
    if data and "hydra:member" in data:
        return data["hydra:member"]
    return []

async def get_message(token, msg_id):
    headers = {"Authorization": f"Bearer {token}"}
    return await fetch_json(f"{MESSAGES_API}/{msg_id}", headers=headers)

@app.on_message(filters.command("genmail"), group=-111)
async def fakemailgen(client, message: Message):
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    loading = await message.reply_text(font("⏳ Creating temporary email..."))
    
    domains = await get_domains()
    domain = random.choice(domains)
    
    username = generate_username()
    email = f"{username}@{domain}"
    password = generate_password()
    
    account = await create_account(email, password)
    if not account:
        return await loading.edit_text(font("❌ Failed to create account!"))
    
    token = await get_token(email, password)
    if not token:
        return await loading.edit_text(font("❌ Failed to authenticate!"))
    
    user_sessions[email] = {"token": token, "password": password}
    
    await loading.delete()
    await app.send_message(
        user_id,
        text=f"**📬 Temp-Mail Created!**\n📧 **Email**: `{email}`\n🔑 **Password**: `{password}`\n📨 **Mail BOX**: `empty`\n\n♨️ Powered by: @shonaxrobot",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(font("🔁 Refresh"), callback_data=f"tmail_refresh|{email}", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(font("❌ Close"), callback_data=f"tmail_delete|{email}", style=ButtonStyle.DANGER),
        ]])
    )

@app.on_message(filters.command("set"), group=-112)
async def setmailgen(client, message: Message):
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    
    if len(message.command) < 2:
        return await message.reply_text(font("❌ Usage: `/set username`"))
    
    username = message.text.split(None, 1)[1]
    loading = await message.reply_text(font("⏳ Creating custom email..."))
    
    domains = await get_domains()
    domain = random.choice(domains)
    
    email = f"{username}@{domain}"
    password = generate_password()
    
    account = await create_account(email, password)
    if not account:
        return await loading.edit_text(font("❌ Failed to create account! Username might be taken."))
    
    token = await get_token(email, password)
    if not token:
        return await loading.edit_text(font("❌ Failed to authenticate!"))
    
    user_sessions[email] = {"token": token, "password": password}
    
    await loading.delete()
    await app.send_message(
        user_id,
        text=f"**📬 Temp-Mail Created!**\n📧 **Email**: `{email}`\n🔑 **Password**: `{password}`\n📨 **Mail BOX**: `empty`\n\n♨️ Powered by: @shonaxrobot",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(font("🔁 Refresh"), callback_data=f"tmail_refresh|{email}", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(font("❌ Close"), callback_data=f"tmail_delete|{email}", style=ButtonStyle.DANGER),
        ]])
    )

@app.on_callback_query(filters.regex("^tmail_refresh"))
async def refresh_mailbox(_, query: CallbackQuery):
    _, email = query.data.split("|", 1)
    
    if email not in user_sessions:
        return await query.answer(font("❌ Session expired! Generate new email."), show_alert=True)
    
    # Show refreshing message
    try:
        await query.message.edit_text(font("🔄 Refreshing..."))
    except Exception:
        pass
    
    token = user_sessions[email]["token"]
    messages = await get_messages(token)
    
    if not messages:
        await query.message.edit_text(
            f"**📬 Temp-Mail**\n📧 **Email**: `{email}`\n📨 **Mail BOX**: `empty`\n\n♨️ Powered by: @shonaxrobot",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(font("🔁 Refresh"), callback_data=f"tmail_refresh|{email}", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(font("❌ Close"), callback_data=f"tmail_delete|{email}", style=ButtonStyle.DANGER),
            ]])
        )
        await query.answer(font("✅ Refreshed!"))
        return
    
    buttons = []
    for msg in messages[:10]:
        subject = msg.get("subject", "No Subject")[:30]
        buttons.append([
            InlineKeyboardButton(
                f"✉️ {subject}",
                callback_data=f"tmail_mail|{email}|{msg['id']}",
                style=ButtonStyle.PRIMARY
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(font("🔁 Refresh"), callback_data=f"tmail_refresh|{email}", style=ButtonStyle.PRIMARY),
        InlineKeyboardButton(font("❌ Close"), callback_data=f"tmail_delete|{email}", style=ButtonStyle.DANGER)
    ])
    
    await query.message.edit_text(
        f"**📬 Temp-Mail**\n📧 **Email**: `{email}`\n📨 **Mail BOX**: {len(messages)} message(s)\n\n♨️ Powered by: @shonaxrobot",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await query.answer(font("✅ Refreshed!"))

@app.on_callback_query(filters.regex("^tmail_mail"))
async def show_mail(_, query: CallbackQuery):
    _, email, msg_id = query.data.split("|")
    
    if email not in user_sessions:
        return await query.answer(font("❌ Session expired!"), show_alert=True)
    
    await query.answer(font("📧 Loading..."))
    
    token = user_sessions[email]["token"]
    mail = await get_message(token, msg_id)
    
    if not mail:
        return await query.answer(font("❌ Failed to fetch mail!"), show_alert=True)
    
    from_addr = mail.get("from", {}).get("address", "Unknown")
    subject = mail.get("subject", "No Subject")
    date = mail.get("createdAt", "Unknown")
    body = mail.get("text", mail.get("html", "No content"))
    
    if len(body) > 3000:
        body = body[:3000] + "\n\n... (message truncated)"
    
    await query.message.edit_text(
        f"**From:** `{from_addr}`\n**Subject:** `{subject}`\n**Date:** `{date}`\n\n{body}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(font("🔙 Back"), callback_data=f"tmail_refresh|{email}", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(font("❌ Close"), callback_data=f"tmail_delete|{email}", style=ButtonStyle.DANGER)
        ]]),
        disable_web_page_preview=True
    )

@app.on_callback_query(filters.regex("^tmail_delete"))
async def delete_message(_, query: CallbackQuery):
    _, email = query.data.split("|", 1)
    
    if email in user_sessions:
        del user_sessions[email]
    
    await query.message.delete()
    await query.answer(font("🗑️ Deleted!"), show_alert=False)

@app.on_message(filters.command("domains"), group=-113)
async def list_domains(_, message: Message):
    loading = await message.reply_text(font("⏳ Fetching domains..."))
    domains = await get_domains()
    await loading.edit_text(font("📋 **Available Domains:**\n\n") + "\n".join(f"• {d}" for d in domains))

@app.on_message(filters.command(["login", "maillogin"]), group=-114)
async def login_mail(client, message: Message):
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    
    if len(message.command) < 3:
        return await message.reply_text(font("❌ Usage: `/login email@domain.com password`"))
    
    parts = message.text.split(None, 2)
    email = parts[1]
    password = parts[2]
    
    loading = await message.reply_text(font("⏳ Logging in..."))
    
    token = await get_token(email, password)
    if not token:
        return await loading.edit_text(font("❌ Failed to login! Check email and password."))
    
    user_sessions[email] = {"token": token, "password": password}
    
    await loading.delete()
    await app.send_message(
        user_id,
        text=f"**✅ Logged in successfully!**\n📧 **Email**: `{email}`\n📨 Click refresh to check mailbox",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(font("🔁 Refresh"), callback_data=f"tmail_refresh|{email}", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(font("❌ Close"), callback_data=f"tmail_delete|{email}", style=ButtonStyle.DANGER),
        ]])
    )

__help__ = """
**Temporary Email Generator 📧**

Commands:
 ❂ `/genmail` - Generate random temp email
 ❂ `/set <username>` - Create custom temp email
 ❂ `/login <email> <password>` - Login to existing email
 ❂ `/domains` - List available domains
"""
__module__ = '𝐓ᴇᴍᴘ-𝐌ᴀɪʟ📧'
