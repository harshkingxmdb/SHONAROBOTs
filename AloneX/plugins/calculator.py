from AloneX import pbot as app, prefix_cmds, font
from pyrogram import filters, types, enums, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ButtonStyle
import re
import math

__module__ = "𝐂ᴀʟᴄᴜʟᴀᴛᴏʀ🧮"

__help__ = """
**Calculator🧮**

**Description:**
Perform calculations directly using the bot with scientific mode.

**Commands:**
❂ `/calc` or `/calculator` – Open interactive calculator
"""

calc_states = {}

def calcExpression(text):
    try:
        if not text.strip():
            return ""
        text = text.replace("×", "*").replace("÷", "/").replace("^", "**")
        return str(float(eval(text)))
    except (SyntaxError, ZeroDivisionError, TypeError, NameError):
        return ""
    except Exception:
        return ""

def calc_btn(uid):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("7", callback_data=f"c|{uid}|7", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("8", callback_data=f"c|{uid}|8", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("9", callback_data=f"c|{uid}|9", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("÷", callback_data=f"c|{uid}|/", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(font("DEL"), callback_data=f"c|{uid}|D", style=ButtonStyle.DANGER),
        ],
        [
            InlineKeyboardButton("4", callback_data=f"c|{uid}|4", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("5", callback_data=f"c|{uid}|5", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("6", callback_data=f"c|{uid}|6", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("×", callback_data=f"c|{uid}|*", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(font("AC"), callback_data=f"c|{uid}|A", style=ButtonStyle.DANGER),
        ],
        [
            InlineKeyboardButton("1", callback_data=f"c|{uid}|1", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("2", callback_data=f"c|{uid}|2", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("3", callback_data=f"c|{uid}|3", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("-", callback_data=f"c|{uid}|-", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton("(", callback_data=f"c|{uid}|(", style=ButtonStyle.SUCCESS),
        ],
        [
            InlineKeyboardButton("0", callback_data=f"c|{uid}|0", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(".", callback_data=f"c|{uid}|.", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton("=", callback_data=f"c|{uid}|=", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton("+", callback_data=f"c|{uid}|+", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(")", callback_data=f"c|{uid}|)", style=ButtonStyle.SUCCESS),
        ],
        [
            InlineKeyboardButton(font("🧮 Scientific"), callback_data=f"c|{uid}|S", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(font("❌ Close"), callback_data=f"c|{uid}|C", style=ButtonStyle.DANGER),
        ],
    ])



@app.on_message(filters.command(["calc", "calculate", "calculator"], prefix_cmds) & ~filters.forwarded, group=25)
async def calculate_handler(client, message):
    if not message.from_user:
        return
    
    uid = message.from_user.id
    calc_states[uid] = {"text": "", "mode": "basic"}
    
    await message.reply_text(
        text="```\n0\n```",
        reply_markup=calc_btn(uid),
        disable_web_page_preview=True,
        quote=True
    )

@app.on_callback_query(filters.regex("^c\\|"))
async def calc_cb(client, query):
    try:
        parts = query.data.split("|")
        uid = int(parts[1])
        data = parts[2]
        
        if query.from_user.id != uid:
            return await query.answer(font("⚠️ This is not your calculator!"), show_alert=True)
        
        if uid not in calc_states:
            calc_states[uid] = {"text": "", "mode": "basic"}
        
        state = calc_states[uid]
        text = state["text"]
        
        if data == "A":
            text = ""
        elif data == "D":
            text = text[:-1] if text else ""
        elif data == "=":
            result = calcExpression(text)
            text = result if result else ""

        elif data == "C":
            await query.message.delete()
            return await query.answer()
        else:
            text += data
        
        state["text"] = text
        markup = sci_btn(uid) if state["mode"] == "scientific" else calc_btn(uid)
        
        try:
            await query.message.edit_text(
                text=f"`{text if text else '0'}`",
                reply_markup=markup,
                disable_web_page_preview=True
            )
        except errors.MessageNotModified:
            pass
        
        await query.answer()
    
    except Exception as e:
        await query.answer(font("Error!"), show_alert=False)
