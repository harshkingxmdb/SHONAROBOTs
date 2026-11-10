import aiohttp, time, io
from asyncio import sleep
from pyrogram import filters
from pyrogram.enums import ParseMode, ButtonStyle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from AloneX import pbot, prefix_cmds, font

__module__ = '𝐂ʀʏᴘᴛᴏ🪙'
__help__ = '''
❂ `/price <coin>` - Check coin price in USD/INR  
❂ `/price <amount> <from> <to>` - Convert currencies/coins  
❂ `/listcoins` - List supported fiat currencies  
'''

CACHE = {"data": {}, "last": 0}
FIAT = {
    "usd","inr","eur","gbp","jpy","aud","cad","rub","cny","brl","idr",
    "mxn","sar","aed","chf","hkd","sgd","thb","ngn","zar"
}

async def get_id(q: str):
    q = q.lower()
    if q in FIAT:
        return q, "fiat"
    if q in CACHE["data"] and time.time() - CACHE["last"] < 600:
        return CACHE["data"][q], "coin"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.coingecko.com/api/v3/search?query={q}") as r:
                if r.status != 200:
                    return None, None
                res = await r.json()
    except:
        return None, None
    for c in res.get("coins", []):
        if q in [c["symbol"].lower(), c["name"].lower()]:
            CACHE["data"][q] = c["id"]
            CACHE["last"] = time.time()
            return c["id"], "coin"
    return None, None

async def convert_amount(amount: float, from_curr: str, to_curr: str):
    fid, ft = await get_id(from_curr)
    tid, tt = await get_id(to_curr)
    if not fid or not tid:
        return None
    try:
        async with aiohttp.ClientSession() as s:
            if ft == "coin" and tt == "fiat":
                async with s.get(f"https://api.coingecko.com/api/v3/simple/price?ids={fid}&vs_currencies={tid}") as r:
                    rate = (await r.json()).get(fid, {}).get(tid)
            elif ft == "fiat" and tt == "coin":
                async with s.get(f"https://api.coingecko.com/api/v3/simple/price?ids={tid}&vs_currencies={fid}") as r:
                    val = (await r.json()).get(tid, {}).get(fid)
                    rate = 1 / val if val else None
            elif ft == "coin" and tt == "coin":
                async with s.get(f"https://api.coingecko.com/api/v3/simple/price?ids={fid},{tid}&vs_currencies=usd") as r:
                    data = await r.json()
                    fu, tu = data.get(fid, {}).get("usd"), data.get(tid, {}).get("usd")
                    rate = fu / tu if fu and tu else None
            else:  # fiat → fiat
                async with s.get(f"https://api.coingecko.com/api/v3/exchange_rates") as r:
                    data = await r.json()
                    rates = data.get("rates", {})
                    rate = rates.get(tid, {}).get("value") / rates.get(fid, {}).get("value")
    except:
        return None
    return rate * amount if rate else None

async def conversion_card(amount: float, f: str, t: str):
    res = await convert_amount(amount, f, t)
    if res is None:
        return None, f"❌ Conversion not available for {amount} {f.upper()} → {t.upper()}"
    txt = (f"🔄 <b>Conversion</b>\n\n"
           f"{amount} {f.upper()} = <code>{res:.6f}</code> {t.upper()}\n"
           f"🔁 Updated just now")
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton(font("⚙️ Refresh"), callback_data=f"refresh_conv_{amount}_{f}_{t}", style=ButtonStyle.PRIMARY)]
    ])
    return txt, btns

@pbot.on_message(filters.command("price", prefix_cmds) & ~filters.forwarded, group=29)
async def price(_, m: Message):
    if len(m.command) < 2:
        return await m.reply(
            "❌ Usage:\n/price btc\n/price 10 usd btc",
            parse_mode=ParseMode.HTML
        )
    args = m.command[1:]
    # conversion mode
    if args[0].replace(".", "", 1).isdigit() and len(args) >= 3:
        amt = float(args[0])
        f, t = args[1].lower(), args[2].lower()
        card, btns = await conversion_card(amt, f, t)
        return await m.reply(card, reply_markup=btns, parse_mode=ParseMode.HTML)
    # price card mode
    cid, typ = await get_id(args[0])
    if not cid or typ == "fiat":
        return await m.reply(f"❌ Coin not found: <code>{args[0]}</code>", parse_mode=ParseMode.HTML)
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cid}&vs_currencies=usd,inr") as r:
                data = await r.json()
    except:
        return await m.reply("❌ Couldn't connect.", parse_mode=ParseMode.HTML)
    usd, inr = data.get(cid, {}).get("usd"), data.get(cid, {}).get("inr")
    if usd is None:
        return await m.reply(font("❌ Price unavailable."), parse_mode=ParseMode.HTML)
    name = cid.replace("-", " ").title()
    txt = (f"📊 <b>{name} Price Info</b>\n\n"
           f"💵 USD: <code>${usd}</code>\n"
           f"🇮🇳 INR: <code>₹{inr}</code>\n🔁 Updated just now")
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton(font("⚙️ Refresh"), callback_data=f"refresh_crypto_{args[0]}", style=ButtonStyle.PRIMARY),
         InlineKeyboardButton(font("📈 Chart"), url=f"https://www.coingecko.com/en/coins/{cid}", style=ButtonStyle.SUCCESS)]
    ])
    await m.reply(txt, reply_markup=btns, parse_mode=ParseMode.HTML)

@pbot.on_message(filters.command("listcoin", prefix_cmds) & ~filters.forwarded, group=30)
async def listcoins(_, m: Message):
    txt = "💱 <b>Supported Fiat Currencies</b>\n\n"
    txt += ", ".join(sorted([c.upper() for c in FIAT]))
    await m.reply(txt, parse_mode=ParseMode.HTML)

@pbot.on_callback_query(filters.regex(r"refresh_conv_(.+)"))
async def refresh_conv(_, cb: CallbackQuery):
    data = cb.matches[0].group(1).split("_")
    amount, f, t = float(data[0]), data[1], data[2]
    await cb.answer(font("🔁 Refreshing..."))
    await cb.message.edit_text(
        f"⚙️ Refreshing {amount} {f.upper()} → {t.upper()}...",
        parse_mode=ParseMode.HTML
    )
    await sleep(1)
    card, btns = await conversion_card(amount, f, t)
    if not card:
        return await cb.message.edit_text(font("❌ Conversion failed."), parse_mode=ParseMode.HTML)
    await cb.message.edit_text(card, reply_markup=btns, parse_mode=ParseMode.HTML)

@pbot.on_callback_query(filters.regex(r"refresh_crypto_(.+)"))
async def refresh_price(_, cb: CallbackQuery):
    q = cb.matches[0].group(1).lower()
    await cb.answer(font("🔁 Refreshing..."))
    await cb.message.edit_text(f"⚙️ Refreshing {q.upper()}...", parse_mode=ParseMode.HTML)
    await sleep(1)
    cid, typ = await get_id(q)
    if not cid or typ == "fiat":
        return await cb.message.edit_text(f"❌ Coin not found: <code>{q}</code>", parse_mode=ParseMode.HTML)
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.coingecko.com/api/v3/simple/price?ids={cid}&vs_currencies=usd,inr") as r:
                data = await r.json()
    except:
        return await cb.message.edit_text("❌ Couldn't connect.", parse_mode=ParseMode.HTML)
    usd, inr = data.get(cid, {}).get("usd"), data.get(cid, {}).get("inr")
    txt = (f"📊 <b>{cid.replace('-', ' ').title()} Price Info</b>\n\n"
           f"💵 USD: <code>${usd}</code>\n"
           f"🇮🇳 INR: <code>₹{inr}</code>\n🔁 Updated just now")
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton(font("⚙️ Refresh"), callback_data=f"refresh_crypto_{q}", style=ButtonStyle.PRIMARY),
         InlineKeyboardButton(font("📈 Chart"), url=f"https://www.coingecko.com/en/coins/{cid}", style=ButtonStyle.SUCCESS)]
    ])
    await cb.message.edit_text(txt, reply_markup=btns, parse_mode=ParseMode.HTML)
