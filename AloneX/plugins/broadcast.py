import asyncio
from pyrogram import filters
from pyrogram.types import *
from pyrogram.errors import FloodWait, PeerIdInvalid, ChatWriteForbidden, ChannelInvalid, UserIsBlocked

from AloneX.db.users import get_all_active_users, update_users_status
from AloneX.db.chats import get_all_chats, update_chats_status
from AloneX import pbot, OWNER_ID, prefix_cmds, font


BROADCAST_CACHE = {}
BROADCAST_DELAY = 0.5
UPDATE_INTERVAL = 5

__module__ = "𝐒ᴜᴅᴏ🛡️"

__help__ = """
*Sudo*

*Description:*  
Superuser commands to manage multiple chats, broadcast messages, and check status.

*Commands:*  
❂ `/gban` – Ban a user from all chats  
❂ `/stats` – Get current status  
❂ `/broadcast_all` – Broadcast to all active users + chats
❂ `/broadcast_users` – Broadcast to active users only
❂ `/broadcast_chats` – Broadcast to active chats only
❂ `/send` – Send a message in a group  
❂ `/echo` – Echo a message
❂ `/speedtest` - check speedtest of server
❂ `/generatlink` - check link of chats
"""

async def send_broadcast(client, chat_id: int, msg: Message):
    try:
        await msg.copy(chat_id)
        await asyncio.sleep(BROADCAST_DELAY)
        return True, False

    except FloodWait as e:
        wait_time = min(e.value, 60)
        await asyncio.sleep(wait_time)
        return await send_broadcast(client, chat_id, msg)

    except (PeerIdInvalid, ChatWriteForbidden, ChannelInvalid, UserIsBlocked):
        return False, True

    except Exception:
        try:
            if msg.text:
                await client.send_message(
                    chat_id, 
                    text=msg.text, 
                    reply_markup=msg.reply_markup,
                    disable_web_page_preview=msg.web_page_preview_disabled,
                )
            elif msg.photo:
                await client.send_photo(
                    chat_id, 
                    photo=msg.photo.file_id,
                    caption=msg.caption or "",
                    reply_markup=msg.reply_markup,
                )
            elif msg.video:
                await client.send_video(
                    chat_id,
                    video=msg.video.file_id,
                    caption=msg.caption or "",
                    reply_markup=msg.reply_markup,
                )
            elif msg.document:
                await client.send_document(
                    chat_id,
                    document=msg.document.file_id,
                    caption=msg.caption or "",
                    reply_markup=msg.reply_markup,
                )
            elif msg.sticker:
                await client.send_sticker(chat_id, msg.sticker.file_id)
            elif msg.animation:
                await client.send_animation(
                    chat_id, 
                    animation=msg.animation.file_id,
                    caption=msg.caption or "",
                    reply_markup=msg.reply_markup,
                )
            elif msg.audio:
                await client.send_audio(
                    chat_id,
                    audio=msg.audio.file_id,
                    caption=msg.caption or "",
                    reply_markup=msg.reply_markup,
                )
            elif msg.voice:
                await client.send_voice(
                    chat_id,
                    voice=msg.voice.file_id,
                    caption=msg.caption or "",
                    reply_markup=msg.reply_markup,
                )
            elif msg.video_note:
                await client.send_video_note(
                    chat_id, 
                    video_note=msg.video_note.file_id
                )
            elif msg.poll:
                await client.send_poll(
                    chat_id,
                    question=msg.poll.question,
                    options=[o.text for o in msg.poll.options],
                    is_anonymous=msg.poll.is_anonymous,
                    type=msg.poll.type,
                    allows_multiple_answers=msg.poll.allows_multiple_answers,
                )
            else:
                await client.forward_messages(chat_id, msg.chat.id, msg.id)
            
            await asyncio.sleep(BROADCAST_DELAY)
            return True, False

        except FloodWait as e:
            wait_time = min(e.value, 60)
            await asyncio.sleep(wait_time)
            return await send_broadcast(client, chat_id, msg)

        except (PeerIdInvalid, ChatWriteForbidden, ChannelInvalid, UserIsBlocked):
            return False, True

        except Exception:
            return False, False


from pyrogram.enums import ButtonStyle

def build_keyboard(mode, preview_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(font("✅ Start"), callback_data=f"broadcast_start:{mode}:{preview_id}", style=ButtonStyle.SUCCESS),
                InlineKeyboardButton(font("❌ Cancel"), callback_data=f"broadcast_cancel:{preview_id}", style=ButtonStyle.DANGER),
            ]
        ]
    )


async def prepare_broadcast(client, message: Message, mode: str):
    if not message.reply_to_message:
        return await message.reply_text(font("⚠️ Reply to a message to broadcast."))

    preview = await message.reply_text(
        f"📢 Broadcast Preview\n\n➤ Mode: `{mode}`\n➤ Confirm to send.",
        reply_markup=build_keyboard(mode, message.reply_to_message.id),
    )

    BROADCAST_CACHE[message.reply_to_message.id] = message.reply_to_message


@pbot.on_message(filters.command("broadcast_users", prefix_cmds) & filters.user(OWNER_ID), group=22)
async def handle_users(client, message):
    await prepare_broadcast(client, message, "users")


@pbot.on_message(filters.command("broadcast_chats", prefix_cmds) & filters.user(OWNER_ID), group=23)
async def handle_chats(client, message):
    await prepare_broadcast(client, message, "chats")


@pbot.on_message(filters.command("broadcast_all", prefix_cmds) & filters.user(OWNER_ID), group=24)
async def handle_all(client, message):
    await prepare_broadcast(client, message, "all")


@pbot.on_callback_query(filters.regex(r"^broadcast_start:(.+?):(\d+)$"))
async def confirm_broadcast(client, query: CallbackQuery):
    if query.from_user.id != OWNER_ID:
        return await query.answer(font("⛔ Not allowed."), show_alert=True)

    mode, preview_id = query.data.split(":")[1:]
    preview_id = int(preview_id)

    await query.message.edit_text(font("🚀 Broadcast started..."))

    msg = BROADCAST_CACHE.pop(preview_id, None)
    if not msg:
        return await query.message.reply_text(font("⚠️ Original message not found."))

    if mode == "users":
        targets = await get_all_active_users()
        label = "Users"
    elif mode == "chats":
        targets = await get_all_chats()
        label = "Chats"
    else:
        users = await get_all_active_users()
        chats = await get_all_chats()
        all_targets = users + chats
        targets = []
        seen = set()
        for target in all_targets:
            if target not in seen:
                targets.append(target)
                seen.add(target)
        label = "Users + Chats"

    sent, failed = 0, 0
    total = len(targets)
    failed_users = []
    failed_chats = []

    status = await msg.reply_text(
        f"🚀 Broadcasting to {label}...\n\n✅ Sent: {sent}\n❌ Failed: {failed}\n📦 Total: {total}\n⏱️ Progress: 0%",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(font("❌ Stop"), callback_data="broadcast_stop", style=ButtonStyle.DANGER)]]
        ),
    )

    BROADCAST_CACHE["cancel_flag"] = False

    for i, target_id in enumerate(targets, start=1):
        if BROADCAST_CACHE.get("cancel_flag"):
            break

        success, should_deactivate = await send_broadcast(client, target_id, msg)
        
        if success:
            sent += 1
        else:
            failed += 1
            if should_deactivate:
                if str(target_id).startswith("-"):
                    failed_chats.append(target_id)
                else:
                    failed_users.append(target_id)

        if i % UPDATE_INTERVAL == 0 or i == total:
            progress = int((i / total) * 100)
            try:
                await status.edit_text(
                    f"🚀 Broadcasting to {label}...\n\n✅ Sent: {sent}\n❌ Failed: {failed}\n📦 Total: {total}\n⏱️ Progress: {progress}%",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton(font("❌ Stop"), callback_data="broadcast_stop", style=ButtonStyle.DANGER)]]
                    ),
                )
            except:
                pass

    if failed_users:
        await update_users_status(failed_users, status=False)
    
    if failed_chats:
        await update_chats_status(failed_chats, status=False)

    try:
        await status.edit_text(
            f"✅ Broadcast Finished!\n\n📦 Total: {total}\n✅ Sent: {sent}\n❌ Failed: {failed}\n\n🗑️ Cleaned: {len(failed_users)} users, {len(failed_chats)} chats"
        )
    except:
        pass

    if mode == "users":
        await msg.reply_text(f"✅ Broadcast sent to {sent} users.\n🗑️ Removed {len(failed_users)} inactive users.")
    elif mode == "chats":
        await msg.reply_text(f"✅ Broadcast sent to {sent} chats.\n🗑️ Removed {len(failed_chats)} inactive chats.")
    else:
        await msg.reply_text(
            f"✅ Broadcast completed!\n\n"
            f"📤 Sent: {sent}\n"
            f"❌ Failed: {failed}\n\n"
            f"🗑️ Cleaned:\n"
            f"  • {len(failed_users)} inactive users\n"
            f"  • {len(failed_chats)} inactive chats"
        )


@pbot.on_callback_query(filters.regex("^broadcast_cancel:(\\d+)$"))
async def cancel_broadcast(_, query: CallbackQuery):
    if query.from_user.id != OWNER_ID:
        return await query.answer(font("⛔ Not allowed."), show_alert=True)

    preview_id = int(query.data.split(":")[1])
    BROADCAST_CACHE.pop(preview_id, None)
    await query.message.edit_text(font("❌ Broadcast Cancelled."))


@pbot.on_callback_query(filters.regex("^broadcast_stop$"))
async def stop_broadcast(_, query: CallbackQuery):
    if query.from_user.id != OWNER_ID:
        return await query.answer(font("⛔ Not allowed."), show_alert=True)

    BROADCAST_CACHE["cancel_flag"] = True
    await query.message.edit_text(font("🛑 Broadcast Stopped midway."))
