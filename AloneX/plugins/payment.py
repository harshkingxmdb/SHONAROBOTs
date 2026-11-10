import hashlib
import asyncio
from html import escape
from pyrogram import filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
)
from pyrogram.enums import ParseMode
from AloneX import pbot, OWNER_ID, font
from datetime import datetime
from pyrogram import enums

REFUND_CACHE = {}

def short_key(user_id: int, charge_id: str) -> str:
    return hashlib.sha1(f"{user_id}:{charge_id}".encode()).hexdigest()[:12]

@pbot.on_message(filters.command("pay"), group=426)
async def pay_handler(client, message: Message):
    args = message.text.split()
    amount = 5
    if len(args) > 1 and args[1].isdigit():
        amount = int(args[1])
    elif len(args) > 1:
        return await message.reply(
            "⚠️ Invalid amount. Use like: `/pay 10`",
            parse_mode=ParseMode.MARKDOWN
        )
    try:
        await client.send_invoice(
            chat_id=message.chat.id,
            title="Donate 💝",
            description=(
                f"♻️ 💖 Support our mission and spread smiles! "
                f"Every donation makes a difference. 🌟 "
                f"Click to contribute and make an impact! 🙏✨ {amount} ⭐ via Telegram Stars."
            ),
            provider_token="",
            currency="XTR",
            payload="star_payment",
            prices=[LabeledPrice(label="♻️ Donation", amount=amount)],
        )
    except Exception as e:
        await message.reply(
            f"❌ Failed to send invoice:\n<code>{escape(str(e))}</code>",
            parse_mode=ParseMode.HTML
        )

@pbot.on_message(filters.command("stars"), group=426)
async def stars_balance(client, message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text(font("🚫 This command is owner-only!"))
    try:
        balance = await client.get_stars_balance()
        await message.reply_text(
            f"⭐ <b>Current Stars Balance</b>\n\n"
            f"💰 {balance} Stars",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(font("🔄 Refresh"), callback_data="refresh_stars", style=enums.ButtonStyle.PRIMARY)
            ]])
        )
    except Exception as e:
        await message.reply_text(
            f"❌ Could not fetch stars balance:\n<code>{escape(str(e))}</code>",
            parse_mode=ParseMode.HTML
        )

@pbot.on_callback_query(filters.regex(r"refresh_stars"))
async def refresh_stars(_, cb):
    if cb.from_user.id != OWNER_ID:
        return await cb.answer(font("🚫 Only owner can refresh!"), show_alert=True)
    await cb.answer(font("🔁 Refreshing..."))
    try:
        balance = await cb._client.get_stars_balance()
        refreshed_at = datetime.now().strftime("%H:%M:%S")
        final_message = (
            f"⭐ <b>Current Stars Balance</b>\n\n"
            f"💰 {balance} Stars\n"
            f"⏰ Last refreshed: <i>{refreshed_at}</i>"
        )
        current_text = cb.message.text or ""
        if final_message.strip() != current_text.strip():
            try:
                await cb.message.edit_text(
                    "⚙️ Refreshing Stars balance...",
                    parse_mode=enums.ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(font("🔄 Refresh"), callback_data="refresh_stars", style=enums.ButtonStyle.PRIMARY)
                    ]])
                )
                await asyncio.sleep(1)
            except Exception:
                pass
            try:
                old_balance = 0
                if "💰" in current_text:
                    try:
                        old_balance_text = current_text.split("💰")[1].split("Stars")[0].strip()
                        old_balance = int(old_balance_text)
                    except (ValueError, IndexError):
                        old_balance = 0
                if abs(balance - old_balance) > 0 and abs(balance - old_balance) <= 100:
                    step = 1 if balance >= old_balance else -1
                    animation_range = list(range(old_balance, balance + step, step))
                    if len(animation_range) > 20:
                        nth = len(animation_range) // 20
                        animation_range = animation_range[::nth] + [balance]
                    for i, b in enumerate(animation_range):
                        try:
                            await cb.message.edit_text(
                                f"⭐ <b>Current Stars Balance</b>\n\n"
                                f"💰 {b} Stars\n"
                                f"⏰ Last refreshed: <i>{refreshed_at}</i>",
                                parse_mode=enums.ParseMode.HTML,
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton(font("🔄 Refresh"), callback_data="refresh_stars", style=enums.ButtonStyle.PRIMARY)
                                ]])
                            )
                            if i < len(animation_range) - 1:
                                await asyncio.sleep(0.05)
                        except Exception as e:
                            if "MESSAGE_NOT_MODIFIED" in str(e):
                                break
                            print(f"Animation step error: {e}")
                            break
                else:
                    await cb.message.edit_text(
                        final_message,
                        parse_mode=enums.ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(font("🔄 Refresh"), callback_data="refresh_stars", style=enums.ButtonStyle.PRIMARY)
                        ]])
                    )
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e):
                    print(f"Animation error: {e}")
                try:
                    await cb.message.edit_text(
                        final_message,
                        parse_mode=enums.ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(font("🔄 Refresh"), callback_data="refresh_stars", style=enums.ButtonStyle.PRIMARY)
                        ]])
                    )
                except Exception:
                    pass
        else:
            await cb.answer(font("✅ Already up to date!"), show_alert=False)
    except Exception as e:
        try:
            await cb.message.edit_text(
                f"❌ Refresh failed:\n<code>{escape(str(e))}</code>",
                parse_mode=enums.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(font("🔄 Refresh"), callback_data="refresh_stars", style=enums.ButtonStyle.PRIMARY)
                ]])
            )
        except Exception:
            await cb.answer(f"❌ Refresh failed: {str(e)}", show_alert=True)

@pbot.on_pre_checkout_query()
async def pre_checkout_handler(client, query: PreCheckoutQuery):
    try:
        print(f"[✅ PreCheckout received from] {query.from_user.id}")
        await query.answer(ok=True)
    except Exception as e:
        print(f"[❌ PreCheckout Error] {e}")

@pbot.on_message(filters.successful_payment, group=426)
async def successful_payment(client, message: Message):
    payment = message.successful_payment
    user = message.from_user
    safe_name = escape(user.first_name or "User")
    html_mention = f'<a href="tg://user?id={user.id}">{safe_name}</a>'
    key = short_key(user.id, payment.telegram_payment_charge_id)
    REFUND_CACHE[key] = (user.id, payment.telegram_payment_charge_id)
    await message.reply(
        (
            "✅ <b>Payment Successful!</b>\n"
            f"Thanks {html_mention}!\n"
            f"💳 {payment.total_amount} {escape(payment.currency)}\n"
            f"🧾 Charge ID: <code>{escape(payment.telegram_payment_charge_id)}</code>"
        ),
        parse_mode=ParseMode.HTML,
    )
    try:
        await client.send_message(
            OWNER_ID,
            (
                "💰 <b>New Payment Received!</b>\n"
                f"👤 From: {html_mention} [{user.id}]\n"
                f"⭐ Amount: {payment.total_amount} {escape(payment.currency)}\n"
                f"🧾 Charge ID: <code>{escape(payment.telegram_payment_charge_id)}</code>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(font("💸 Refund"), callback_data=f"refund|{key}", style=enums.ButtonStyle.DANGER)
            ]])
        )
        print(f"[✅ Refund Button Sent] for {user.id}")
    except Exception as e:
        print(f"[❌ Refund Notify Error] {e}")

@pbot.on_callback_query(filters.regex(r"^refund\|"))
async def refund_callback(client, query: CallbackQuery):
    if query.from_user.id != OWNER_ID:
        return await query.answer(font("🚫 Only the bot owner can refund!"), show_alert=True)
    try:
        _, key = query.data.split("|", 1)
        if key not in REFUND_CACHE:
            return await query.answer(font("❌ Refund data expired!"), show_alert=True)
        user_id, charge_id = REFUND_CACHE.pop(key)
        await client.refund_star_payment(
            user_id=user_id,
            telegram_payment_charge_id=charge_id
        )
        await query.message.edit_text(font("✅ Refund successful!"), parse_mode=ParseMode.HTML)
    except Exception as e:
        await query.message.edit_text(
            f"❌ Refund failed:\n<code>{escape(str(e))}</code>",
            parse_mode=ParseMode.HTML
        )
