from pyrogram import filters, enums
from pyrogram.enums import ButtonStyle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
import asyncio
from datetime import datetime
import pytz
import inspect
from AloneX import pbot, prefix_cmds, font
from AloneX.db.sudo import get_all_sudo_users
from AloneX.db.antinsfw_db import count_antinsfw_enabled
from AloneX.helpers.pyro_utils import no_channel

_IST = pytz.timezone("Asia/Kolkata")

async def _safe_call(module_path: str, attr_path: str = None, call_args: tuple = (), default=None):
    try:
        module = __import__(module_path, fromlist=['*'])
        target = module
        if attr_path:
            for part in attr_path.split('.'):
                target = getattr(target, part)
        result = target(*call_args) if callable(target) else target
        if asyncio.iscoroutine(result) or inspect.isawaitable(result):
            return await result
        return result
    except Exception:
        return default

async def handle_flood_wait(func, *args, max_retries=3, **kwargs):
    delay = 0.005
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except FloodWait as e:
            wait_for = min(getattr(e, 'value', getattr(e, 'wait', 0) or 0), 60)
            await asyncio.sleep(wait_for)
        except Exception:
            if attempt + 1 == max_retries:
                raise
            await asyncio.sleep(delay)
            delay *= 0.005
    return None

async def is_sudo(user_id: int) -> bool:
    try:
        sudo_users = await get_all_sudo_users()
        return user_id in sudo_users
    except Exception:
        return False

async def get_stats_text():
    try:
        current_time = datetime.now(_IST)
        safe_call = _safe_call
        create_task = asyncio.create_task
        keys = [
            "users_count", "active_users", "chats_collection_count",
            "af_chats", "cb_chats", "f_chats", "total_warns", "warn_chats",
            "warn_filters", "warn_filter_chats", "block_triggers", "block_chats",
            "af_files", "af_chats_count", "chatbot_chats", "total_filters",
            "filter_chats", "flood_chats", "antiraid_chats", "approval_summary",
            "greetings_chats", "count_welcome_chats", "count_goodbye_chats",
            "notes_chats", "fsub_chats", "translate_chats", "locks_distinct",
            "riddle_chats", "ignored_users", "afk_users", "rules_chats",
            "reaction_chats", "disabled_items", "disabled_chats", "antinsfw_chats",
        ]
        tasks = [
            create_task(safe_call("AloneX.db.users", "count_users", (), 0)),
            create_task(safe_call("AloneX.db.users", "get_all_active_users", (), [])),
            create_task(safe_call("AloneX.db.chats", "collection.count_documents", ({},), 0)),
            create_task(safe_call("AloneX.db.autofilter", "autofilter.distinct", ("chat_id",), [])),
            create_task(safe_call("AloneX.db.chatbot", "collection.distinct", ("chat_id",), [])),
            create_task(safe_call("AloneX.db.filter", "filters_collection.distinct", ("chat_id",), [])),
            create_task(safe_call("AloneX.db.warn_db", "count_warns", (), 0)),
            create_task(safe_call("AloneX.db.warn_db", "count_chats", (), 0)),
            create_task(safe_call("AloneX.db.warn_db", "count_warn_filters", (), 0)),
            create_task(safe_call("AloneX.db.warn_db", "count_warn_filter_chats", (), 0)),
            create_task(safe_call("AloneX.db.blocklistwords", "count_triggers", (), 0)),
            create_task(safe_call("AloneX.db.blocklistwords", "count_chats", (), 0)),
            create_task(safe_call("AloneX.db.autofilter", "get_files_count", (), 0)),
            create_task(safe_call("AloneX.db.autofilter", "count_chats", (), 0)),
            create_task(safe_call("AloneX.db.chatbot", "count_chats", (), 0)),
            create_task(safe_call("AloneX.db.filter", "count_total_filters", (), 0)),
            create_task(safe_call("AloneX.db.filter", "count_chats", (), 0)),
            create_task(safe_call("AloneX.db.antiflood", "count_chats", (), 0)),
            create_task(safe_call("AloneX.db.antiraid", "count_chats", (), 0)),
            create_task(safe_call("AloneX.db.approval_db", "approvals_summary", (), "0 approved, 0 chats")),
            create_task(safe_call("AloneX.db.greetings", "count_chats", (), None)),
            create_task(safe_call("AloneX.db.greetings", "count_welcome_chats", (), 0)),
            create_task(safe_call("AloneX.db.greetings", "count_goodbye_chats", (), 0)),
            create_task(safe_call("AloneX.db.notes", "count_chats", (), 0)),
            create_task(safe_call("AloneX.db.fsub", "count_chats", (), 0)),
            create_task(safe_call("AloneX.db.translate", "count_chats", (), 0)),
            create_task(safe_call("AloneX.db.locks_db", "locks_collection.distinct", ("chat_id",), [])),
            create_task(safe_call("AloneX.db.riddle", "count_chats", (), 0)),
            create_task(safe_call("AloneX.db.ignore", "count_chats", (), 0)),
            create_task(safe_call("AloneX.db.afk", "count_chats", (), 0)),
            create_task(safe_call("AloneX.db.rules", "count_rules_chats", (), 0)),
            create_task(safe_call("AloneX.db.reaction", "count_chats", (), 0)),
            create_task(safe_call("AloneX.db.disable", "count_disabled_items", (), 0)),
            create_task(safe_call("AloneX.db.disable", "count_chats", (), 0)),
            create_task(count_antinsfw_enabled()),
        ]
        results_list = await asyncio.gather(*tasks, return_exceptions=False)
        results = dict(zip(keys, results_list))
        chats_count = results.get("chats_collection_count") or 0
        if not chats_count:
            unique_chats = set()
            for key in ("af_chats", "cb_chats", "f_chats"):
                vals = results.get(key) or []
                try:
                    unique_chats.update(vals)
                except Exception:
                    pass
            chats_count = len(unique_chats)
        greetings_chats = results.get("greetings_chats")
        if greetings_chats is None:
            welcome = results.get("count_welcome_chats") or 0
            goodbye = results.get("count_goodbye_chats") or 0
            greetings_chats = max(welcome, goodbye)
        locks_list = results.get("locks_distinct") or []
        locks_count = len(locks_list) if hasattr(locks_list, '__len__') else 0
        text = [f"**Cᴜʀʀᴇɴᴛ Sᴛᴀᴛs:**\n"]
        text.append(f"`{(results.get('block_triggers') or 0):,}` ʙʟᴀᴄᴋʟɪsᴛ ᴛʀɪɢɢᴇʀs, ᴀᴄʀᴏss `{(results.get('block_chats') or 0):,}` ᴄʜᴀᴛs.")
        text.append(f"`{(results.get('chatbot_chats') or 0):,}` ᴄʜᴀᴛs ᴇɴᴀʙʟᴇᴅ ᴄʜᴀᴛʙᴏᴛ ғᴇᴀᴛᴜʀᴇ.")
        text.append(f"`{(results.get('total_filters') or 0):,}` ғɪʟᴛᴇʀs, ᴀᴄʀᴏss `{(results.get('filter_chats') or 0):,}` ᴄʜᴀᴛs.")
        text.append(f"`{(results.get('af_files') or 0):,}` ᴀᴜᴛᴏғɪʟᴛᴇʀ ғɪʟᴇs, ᴀᴄʀᴏss `{(results.get('af_chats_count') or 0):,}` ᴄʜᴀᴛs.")
        text.append(f"`{(results.get('flood_chats') or 0):,}` ᴄʜᴀᴛs ᴇɴᴀʙʟᴇᴅ ᴀɴᴛɪғʟᴏᴏᴅ ғᴇᴀᴛᴜʀᴇ.")
        text.append(f"`{(results.get('antiraid_chats') or 0):,}` ᴄʜᴀᴛs ᴇɴᴀʙʟᴇᴅ ᴀɴᴛɪʀᴀɪᴅ ғᴇᴀᴛᴜʀᴇ.")
        text.append(f"`{(results.get('antinsfw_chats') or 0):,}` ᴄʜᴀᴛs ᴇɴᴀʙʟᴇᴅ ᴀɴᴛɪɴsғᴡ ғᴇᴀᴛᴜʀᴇ.")
        text.append(f"`{greetings_chats:,}` ᴄʜᴀᴛs ᴇɴᴀʙʟᴇᴅ ɢʀᴇᴇᴛɪɴɢs ғᴇᴀᴛᴜʀᴇ.")
        text.append(f"`{(results.get('notes_chats') or 0):,}` ᴄʜᴀᴛs ʜᴀᴠᴇ ɴᴏᴛᴇs sᴇᴛ.")
        text.append(f"`{(results.get('fsub_chats') or 0):,}` ᴄʜᴀᴛs ᴇɴᴀʙʟᴇᴅ ғᴏʀᴄᴇsᴜʙsᴄʀɪʙᴇ ғᴇᴀᴛᴜʀᴇ.")
        text.append(f"`{(results.get('translate_chats') or 0):,}` ᴄʜᴀᴛs ᴇɴᴀʙʟᴇᴅ ᴛʀᴀɴsʟᴀᴛɪᴏɴ ғᴇᴀᴛᴜʀᴇ.")
        text.append(f"`{locks_count:,}` ᴄʜᴀᴛs ʜᴀᴠᴇ ʟᴏᴄᴋs sᴇᴛ.")
        text.append(f"`{(results.get('riddle_chats') or 0):,}` ᴄʜᴀᴛs ᴇɴᴀʙʟᴇᴅ ʀɪᴅᴅʟᴇ ғᴇᴀᴛᴜʀᴇ.")
        text.append(f"`{(results.get('ignored_users') or 0):,}` ɪɢɴᴏʀᴇᴅ ᴜsᴇʀs.")
        text.append(f"`{(results.get('afk_users') or 0):,}` ᴀғᴋ ᴜsᴇʀs.")
        text.append(f"`{(results.get('rules_chats') or 0):,}` ᴄʜᴀᴛs ʜᴀᴠᴇ ʀᴜʟᴇs sᴇᴛ.")
        text.append(f"`{(results.get('reaction_chats') or 0):,}` ᴄʜᴀᴛs ᴇɴᴀʙʟᴇᴅ ʀᴇᴀᴄᴛɪᴏɴ ғᴇᴀᴛᴜʀᴇ.")
        text.append(f"`{(results.get('disabled_items') or 0):,}` ᴅɪsᴀʙʟᴇᴅ ɪᴛᴇᴍs, ᴀᴄʀᴏss `{(results.get('disabled_chats') or 0):,}` ᴄʜᴀᴛs.")
        approval_summary = results.get("approval_summary") or "0 approved, 0 chats"
        text.append(f"`{approval_summary}` ᴀᴘᴘʀᴏᴠᴀʟs.")
        text.append(f"`{(results.get('users_count') or 0):,}` ᴜsᴇʀs, ᴀᴄʀᴏss `{chats_count:,}` ᴄʜᴀᴛs.")
        text.append(f"`{len(results.get('active_users') or []):,}` ᴀᴄᴛɪᴠᴇ ʙᴏᴛ ᴜsᴇʀs ɪɴ ᴛʜᴇ ᴘʀɪᴠᴀᴛᴇ.")
        text.append(f"`{(results.get('total_warns') or 0):,}` ᴏᴠᴇʀᴀʟʟ ᴡᴀʀɴs, ᴀᴄʀᴏss `{(results.get('warn_chats') or 0):,}` ᴄʜᴀᴛs.")
        text.append(f"`{(results.get('warn_filters') or 0):,}` ᴡᴀʀɴ ғɪʟᴛᴇʀs, ᴀᴄʀᴏss `{(results.get('warn_filter_chats') or 0):,}` ᴄʜᴀᴛs.")
        ist_time = current_time.strftime("%d/%m/%Y %I:%M:%S %p IST")
        text.append(f"\n⚡ **Lᴀsᴛ Uᴘᴅᴀᴛᴇᴅ:** `{ist_time}`")
        return "\n".join(text)
    except Exception as e:
        return f"**❌ Eʀʀᴏʀ:** `{str(e)}`"

@pbot.on_message(filters.command("stats", prefix_cmds), group=-329)
@no_channel
async def bot_stats(_, message):
    if not message.from_user:
        return await message.reply_text(font("❌ Unable to identify user. This command cannot be used by channels or anonymous admins."))
    if not await is_sudo(message.from_user.id):
        return await message.reply_text(font("❌ Access denied! Only sudo users can use this."))
    msg = None
    try:
        msg = await handle_flood_wait(message.reply_text, "**⏳ Lᴏᴀᴅɪɴɢ sᴛᴀᴛs...**", parse_mode=enums.ParseMode.MARKDOWN)
        if not msg:
            return
        text = await get_stats_text()
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(font("✪ Refresh ✪"), callback_data="refresh_stats_cb", style=ButtonStyle.SUCCESS)]])
        await handle_flood_wait(msg.edit_text, text, reply_markup=keyboard, parse_mode=enums.ParseMode.MARKDOWN)
    except FloodWait as e:
        await asyncio.sleep(min(getattr(e, "value", 0), 60))
        try:
            if msg:
                await handle_flood_wait(msg.edit_text, f"**⏳ Rᴀᴛᴇ ʟɪᴍɪᴛᴇᴅ, ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ {getattr(e,'value',0)} sᴇᴄᴏɴᴅs**", parse_mode=enums.ParseMode.MARKDOWN)
            else:
                await handle_flood_wait(message.reply_text, f"**⏳ Rᴀᴛᴇ ʟɪᴍɪᴛᴇᴅ, ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ {getattr(e,'value',0)} sᴇᴄᴏɴᴅs**", parse_mode=enums.ParseMode.MARKDOWN)
        except:
            pass
    except Exception as e:
        err = f"**❌ Fᴀɪʟᴇᴅ:** `{str(e)}`"
        try:
            if msg:
                await handle_flood_wait(msg.edit_text, err, parse_mode=enums.ParseMode.MARKDOWN)
            else:
                await handle_flood_wait(message.reply_text, err, parse_mode=enums.ParseMode.MARKDOWN)
        except:
            pass

@pbot.on_callback_query(filters.regex(r"^refresh_stats_cb$"))
async def refresh_stats_cb(_, query):
    if not query.from_user:
        return await query.answer(font("❌ Unable to identify user."), show_alert=True)
    if not await is_sudo(query.from_user.id):
        return await query.answer(font("❌ Access denied!"), show_alert=True)
    temp_kb = InlineKeyboardMarkup([[InlineKeyboardButton(font("✪ Refresh ✪"), callback_data="refresh_stats_cb", style=ButtonStyle.SUCCESS)]])
    try:
        await query.message.edit_text(font("⚡ **🖥️ ᴜᴘᴅᴀᴛɪɴɢ ʟᴀᴛᴇꜱᴛ ᴅᴀᴛᴀ...**"), reply_markup=temp_kb, parse_mode=enums.ParseMode.MARKDOWN)
        text = await get_stats_text()
        await query.edit_message_text(text, reply_markup=temp_kb, parse_mode=enums.ParseMode.MARKDOWN)
        await query.answer(font("✅ Stats refreshed!"), show_alert=False)
    except FloodWait as e:
        await query.answer(f"⏳ Rate limited! Please wait {getattr(e,'value',0)} seconds", show_alert=True)
    except Exception as e:
        try:
            await query.message.edit_text(f"**❌ Eʀʀᴏʀ:** `{str(e)}`", parse_mode=enums.ParseMode.MARKDOWN)
        except:
            await query.answer(font("❌ Refresh failed!"), show_alert=True)
