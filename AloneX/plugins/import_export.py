import json
import os
import asyncio
from typing import List, Optional
from datetime import datetime
from cachetools import TTLCache

from pyrogram import filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from AloneX import pbot, font, LOGGER
import config
from AloneX.helpers.decorator import only_groups
from AloneX.helpers.pyro_utils import is_admin
from AloneX.db import (
    mod, antiflood, blocklistwords, cleancommand_db, cleanservice_db,
    disable, federation_db, filter as filter_db, greetings, locks_db,
    notes, rules, translate, warn_db, antiraid, approval_db,
    antitag_db, joinmute_db, antiforward_db, mediadelete_db,
    ghost_db, nightmode_db, chatbot, logchannel_db, connection_db
)

# Rate limiting: 1 export/import per 5 minutes per chat
rate_limit = TTLCache(maxsize=1000, ttl=300)

SUPPORTED_CATEGORIES = {
    "admin": "Admin roles (mods)",
    "antiflood": "Anti-flood settings",
    "blocklists": "Blacklisted words",
    "clean_command": "Clean command settings",
    "clean_service": "Clean service settings",
    "disabled": "Disabled commands",
    "filters": "Chat filters",
    "greetings": "Welcome and Goodbye settings",
    "locks": "Chat locks",
    "notes": "Saved notes",
    "rules": "Chat rules",
    "translations": "Translation settings",
    "warns": "Warning system settings",
    "federations": "Federation settings",
    "antiraid": "Anti-raid settings",
    "approvals": "Approved users",
    "antitag": "Anti-tag limit",
    "joinmute": "Join-mute duration",
    "antiforward": "Anti-forward status",
    "mediadelete": "Media auto-delete settings",
    "ghost": "Ghost mode status",
    "nightmode": "Night mode settings",
    "chatbot": "Chatbot status",
    "logchannel": "Log channel settings",
    "pins": "Pinned message service cleanup",
    "reports": "User reporting settings"
}

async def get_chat_creator(chat_id: int) -> int:
    try:
        async for member in pbot.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
            if member.status == enums.ChatMemberStatus.OWNER:
                return member.user.id
    except Exception:
        pass
    return 0

@pbot.on_message(filters.command("export") & ~filters.forwarded)
@only_groups
async def export_chat_data(client, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.chat.type == enums.ChatType.PRIVATE:
        chat_id = await connection_db.get_connected_chat(user_id) or chat_id

    if not await is_admin(chat_id, user_id):
        return await message.reply_text(font("❌ You must be an administrator to export chat settings."))

    if chat_id in rate_limit:
        return await message.reply_text(font("⏳ This command is rate limited. Please try again later."))

    args = message.text.split()[1:]
    categories = [cat.lower() for cat in args] if args else list(SUPPORTED_CATEGORIES.keys())

    # Filter valid categories
    categories = [cat for cat in categories if cat in SUPPORTED_CATEGORIES]
    if not categories:
        return await message.reply_text(font(f"❌ No valid categories specified. Supported: {', '.join(SUPPORTED_CATEGORIES.keys())}"))

    m = await message.reply_text(font("🔄 Exporting chat data..."))
    data = {"chat_id": chat_id, "exported_at": str(datetime.now()), "categories": {}}

    try:
        if "admin" in categories:
            mods = await mod.get_all_mods(chat_id)
            for m in mods:
                m.pop("_id", None)
            data["categories"]["admin"] = mods

        if "antiflood" in categories:
            data["categories"]["antiflood"] = await antiflood.get_flood_config(chat_id)

        if "blocklists" in categories:
            data["categories"]["blocklists"] = {
                "words": await blocklistwords.get_words(chat_id),
                "mode": await blocklistwords.get_mode(chat_id)
            }

        if "clean_command" in categories:
            data["categories"]["clean_command"] = await cleancommand_db.get_clean_type(chat_id)

        if "clean_service" in categories:
            data["categories"]["clean_service"] = list(await cleanservice_db.get_clean_settings(chat_id))

        if "disabled" in categories:
            data["categories"]["disabled"] = await disable.get_disabled(chat_id)

        if "filters" in categories:
            filters_list = await filter_db.get_filters(chat_id)
            # Remove MongoDB ObjectIds and other non-serializable stuff
            for f in filters_list:
                f.pop("_id", None)
                if isinstance(f.get("added_on"), datetime):
                    f["added_on"] = f["added_on"].isoformat()
            data["categories"]["filters"] = filters_list

        if "greetings" in categories:
            data["categories"]["greetings"] = {
                "welcome": await greetings.get_welcome(chat_id),
                "welcome_status": await greetings.get_welcome_status(chat_id),
                "welcome_time": await greetings.get_welcome_time(chat_id),
                "clean_welcome": await greetings.get_clean_welcome(chat_id),
                "goodbye": await greetings.get_goodbye(chat_id),
                "goodbye_status": await greetings.get_goodbye_status(chat_id),
                "goodbye_time": await greetings.get_goodbye_time(chat_id),
                "clean_goodbye": await greetings.get_clean_goodbye(chat_id)
            }
            # Clean up MongoDB data
            for k in ["welcome", "goodbye"]:
                if data["categories"]["greetings"][k]:
                    data["categories"]["greetings"][k].pop("_id", None)

        if "locks" in categories:
            data["categories"]["locks"] = {
                "locked": await locks_db.get_locks(chat_id),
                "lockwarn": await locks_db.get_lockwarn(chat_id),
                "adminlock": await locks_db.get_adminlock(chat_id)
            }

        if "notes" in categories:
            saved_notes = await notes.get_notes_by_chat(chat_id)
            for n in saved_notes:
                n.pop("_id", None)
            data["categories"]["notes"] = saved_notes

        if "rules" in categories:
            data["categories"]["rules"] = {
                "rules": await rules.get_rules(chat_id),
                "private": await rules.get_private_rules(chat_id),
                "button": await rules.get_rules_button(chat_id)
            }

        if "translations" in categories:
            trans = await translate.get_chat(chat_id)
            if trans:
                trans.pop("_id", None)
            data["categories"]["translations"] = trans

        if "warns" in categories:
            data["categories"]["warns"] = {
                "filters": await warn_db.get_warn_filters(chat_id),
                "limit": await warn_db.get_warn_limit(chat_id),
                "action": await warn_db.get_warn_action(chat_id),
                "strong": await warn_db.get_strong_warn(chat_id)
            }
            for f in data["categories"]["warns"]["filters"]:
                f.pop("_id", None)

        if "federations" in categories:
            data["categories"]["federations"] = {
                "fed_id": await federation_db.get_chat_fed(chat_id),
                "quiet": await federation_db.is_quiet_fed(chat_id)
            }

        if "antiraid" in categories:
            raid = await antiraid.get_antiraid_config(chat_id)
            if raid:
                raid.pop("_id", None)
                if isinstance(raid.get("enabled_until"), datetime):
                    raid["enabled_until"] = raid["enabled_until"].isoformat()
            data["categories"]["antiraid"] = raid

        if "approvals" in categories:
            data["categories"]["approvals"] = await approval_db.get_all_approved_users(chat_id)

        if "antitag" in categories:
            data["categories"]["antitag"] = await antitag_db.get_antitag_limit(chat_id)

        if "joinmute" in categories:
            data["categories"]["joinmute"] = await joinmute_db.get_joinmute_duration(chat_id)

        if "antiforward" in categories:
            data["categories"]["antiforward"] = await antiforward_db.is_antiforward_enabled(chat_id)

        if "mediadelete" in categories:
            data["categories"]["mediadelete"] = await mediadelete_db.get_media_delete_settings(chat_id)

        if "ghost" in categories:
            data["categories"]["ghost"] = await ghost_db.is_ghost_enabled(chat_id)

        if "nightmode" in categories:
            nm = await nightmode_db.get_nightmode_data(chat_id)
            if nm:
                nm.pop("_id", None)
            data["categories"]["nightmode"] = nm

        if "chatbot" in categories:
            data["categories"]["chatbot"] = chat_id in chatbot.CHAT_IDS

        if "pins" in categories:
            clean_settings = await cleanservice_db.get_clean_settings(chat_id)
            data["categories"]["pins"] = "pin" in clean_settings

        if "reports" in categories:
            # We don't have report settings yet, but adding for completeness
            data["categories"]["reports"] = True

        if "logchannel" in categories:
            log_id = await logchannel_db.get_log_channel(chat_id)
            disabled_cats = []
            res = await logchannel_db.db.find_one({"chat_id": chat_id})
            if res:
                disabled_cats = res.get("disabled_categories", [])
            data["categories"]["logchannel"] = {
                "log_channel_id": log_id,
                "disabled_categories": disabled_cats
            }

        file_name = f"export_{chat_id}.json"
        with open(file_name, "w") as f:
            json.dump(data, f, indent=4)

        await message.reply_document(
            document=file_name,
            caption=font(f"✅ Chat configuration exported.\n\nCategories: {', '.join(categories)}")
        )
        await m.delete()
        os.remove(file_name)
        rate_limit[chat_id] = True

    except Exception as e:
        LOGGER.error(f"Export error: {e}")
        await m.edit_text(font(f"❌ An error occurred during export: {e}"))

@pbot.on_message(filters.command("import") & ~filters.forwarded)
@only_groups
async def import_chat_data(client, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.chat.type == enums.ChatType.PRIVATE:
        chat_id = await connection_db.get_connected_chat(user_id) or chat_id

    creator_id = await get_chat_creator(chat_id)
    if user_id != creator_id and user_id not in [config.OWNER_ID]:
        return await message.reply_text(font("❌ Only the group creator can import chat settings for security reasons."))

    if chat_id in rate_limit:
        return await message.reply_text(font("⏳ This command is rate limited. Please try again later."))

    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text(font("❌ Please reply to an export JSON file to import settings."))

    if not message.reply_to_message.document.file_name.endswith(".json"):
        return await message.reply_text(font("❌ Invalid file format. Please reply to a .json export file."))

    args = message.text.split()[1:]
    target_categories = [cat.lower() for cat in args] if args else []

    m = await message.reply_text(font("🔄 Downloading and importing chat data..."))

    try:
        file_path = await message.reply_to_message.download()
        with open(file_path, "r") as f:
            data = json.load(f)
        os.remove(file_path)

        if "categories" not in data:
            return await m.edit_text(font("❌ Invalid export file structure."))

        imported = []
        cats = data["categories"]

        for cat_name, cat_data in cats.items():
            if target_categories and cat_name not in target_categories:
                continue

            try:
                if cat_name == "admin":
                    for mod_data in cat_data:
                        await mod.add_mod_role(chat_id, mod_data["user_id"], mod_data["role"])

                elif cat_name == "antiflood":
                    if "limit" in cat_data: await antiflood.set_flood_limit(chat_id, cat_data["limit"])
                    if "timer" in cat_data: await antiflood.set_flood_timer(chat_id, cat_data["timer"]["count"], cat_data["timer"]["seconds"])
                    if "action" in cat_data: await antiflood.set_flood_action(chat_id, cat_data["action"]["type"], cat_data["action"].get("duration"))
                    if "clear" in cat_data: await antiflood.set_flood_clear(chat_id, cat_data["clear"])

                elif cat_name == "blocklists":
                    for word in cat_data.get("words", []):
                        await blocklistwords.add_word(chat_id, word)
                    if "mode" in cat_data: await blocklistwords.update_mode(chat_id, cat_data["mode"])

                elif cat_name == "clean_command":
                    if cat_data: await cleancommand_db.set_clean_type(chat_id, cat_data)

                elif cat_name == "clean_service":
                    await cleanservice_db.save_clean_settings(chat_id, set(cat_data))

                elif cat_name == "disabled":
                    for cmd in cat_data:
                        await disable.disable_cmd(chat_id, cmd)

                elif cat_name == "filters":
                    for f in cat_data:
                        if "caption" in f:
                            await filter_db.add_filter_with_caption(chat_id, f["trigger"], f["reply_type"], f["reply_data"], user_id, f["caption"], f.get("buttons"))
                        else:
                            await filter_db.add_filter(chat_id, f["trigger"], f["reply_type"], f["reply_data"], user_id, f.get("buttons"))

                elif cat_name == "greetings":
                    w = cat_data.get("welcome")
                    if w:
                        await greetings.set_welcome(chat_id, w.get("file_id"), w.get("file_type"), w.get("text"), w.get("keyboard"), w.get("has_rules_button", False), w.get("has_rules_same", False), w.get("rules_target_row", -1))
                    if "welcome_status" in cat_data: await greetings.set_welcome_status(chat_id, cat_data["welcome_status"])
                    if "welcome_time" in cat_data and cat_data["welcome_time"]: await greetings.set_welcome_time(chat_id, cat_data["welcome_time"])
                    if "clean_welcome" in cat_data: await greetings.set_clean_welcome(chat_id, cat_data["clean_welcome"])

                    g = cat_data.get("goodbye")
                    if g:
                        await greetings.set_goodbye(chat_id, g.get("file_id"), g.get("file_type"), g.get("text"), g.get("keyboard"), g.get("has_rules_button", False), g.get("has_rules_same", False), g.get("rules_target_row", -1))
                    if "goodbye_status" in cat_data: await greetings.set_goodbye_status(chat_id, cat_data["goodbye_status"])
                    if "goodbye_time" in cat_data and cat_data["goodbye_time"]: await greetings.set_goodbye_time(chat_id, cat_data["goodbye_time"])
                    if "clean_goodbye" in cat_data: await greetings.set_clean_goodbye(chat_id, cat_data["clean_goodbye"])

                elif cat_name == "locks":
                    for lock in cat_data.get("locked", []):
                        await locks_db.update_lock(chat_id, lock)
                    if "lockwarn" in cat_data: await locks_db.set_lockwarn(chat_id, cat_data["lockwarn"])
                    if "adminlock" in cat_data: await locks_db.set_adminlock(chat_id, cat_data["adminlock"])

                elif cat_name == "notes":
                    for note in cat_data:
                        await notes.save_note(chat_id, note["tag"], note["type"], note["text"], note.get("file_id"))

                elif cat_name == "rules":
                    await rules.set_rules(chat_id, cat_data.get("rules") or "", None)
                    if "private" in cat_data: await rules.set_private_rules(chat_id, cat_data["private"])
                    if "button" in cat_data: await rules.set_rules_button(chat_id, cat_data["button"])

                elif cat_name == "translations":
                    if cat_data and "lang" in cat_data:
                        await translate.add_chat(chat_id, cat_data["lang"])

                elif cat_name == "warns":
                    for f in cat_data.get("filters", []):
                        await warn_db.add_warn_filter(chat_id, f["keyword"], f["reply"])
                    if "limit" in cat_data: await warn_db.set_warn_limit(chat_id, cat_data["limit"])
                    if "action" in cat_data: await warn_db.set_warn_action(chat_id, cat_data["action"])
                    if "strong" in cat_data: await warn_db.set_strong_warn(chat_id, cat_data["strong"])

                elif cat_name == "federations":
                    if "fed_id" in cat_data and cat_data["fed_id"]:
                        await federation_db.join_fed(chat_id, cat_data["fed_id"])
                    if "quiet" in cat_data:
                        await federation_db.set_quiet_fed(chat_id, cat_data["quiet"])

                elif cat_name == "antiraid":
                    if "enabled_until" in cat_data and cat_data["enabled_until"]:
                        until = datetime.fromisoformat(cat_data["enabled_until"])
                        await antiraid.enable_antiraid(chat_id, until)
                    if "raid_time" in cat_data: await antiraid.set_raid_time(chat_id, cat_data["raid_time"])
                    if "ban_time" in cat_data: await antiraid.set_ban_time(chat_id, cat_data["ban_time"])
                    if "auto_trigger" in cat_data: await antiraid.set_auto_trigger(chat_id, cat_data["auto_trigger"])

                elif cat_name == "approvals":
                    for uid in cat_data:
                        await approval_db.approve_user(chat_id, uid)

                elif cat_name == "antitag":
                    await antitag_db.set_antitag_limit(chat_id, cat_data)

                elif cat_name == "joinmute":
                    await joinmute_db.set_joinmute_duration(chat_id, cat_data)

                elif cat_name == "antiforward":
                    await antiforward_db.set_antiforward_status(chat_id, cat_data)

                elif cat_name == "mediadelete":
                    if "enabled" in cat_data: await mediadelete_db.set_media_delete_state(chat_id, cat_data["enabled"])
                    if "delay" in cat_data: await mediadelete_db.set_media_delete_delay(chat_id, cat_data["delay"])

                elif cat_name == "ghost":
                    await ghost_db.set_ghost(chat_id, cat_data)

                elif cat_name == "nightmode":
                    if cat_data:
                        await nightmode_db.add_nightmode(chat_id, cat_data.get("close_hour"), cat_data.get("open_hour"))
                        if not cat_data.get("nightmode"):
                            await nightmode_db.rm_nightmode(chat_id)

                elif cat_name == "chatbot":
                    if cat_data: await chatbot.add_chat(chat_id)
                    else: await chatbot.remove_chat(chat_id)

                elif cat_name == "logchannel":
                    if cat_data.get("log_channel_id"):
                        await logchannel_db.set_log_channel(chat_id, int(cat_data["log_channel_id"]))
                    for lcat in cat_data.get("disabled_categories", []):
                        await logchannel_db.disable_log_category(chat_id, lcat)

                elif cat_name == "pins":
                    current = await cleanservice_db.get_clean_settings(chat_id)
                    if cat_data:
                        current.add("pin")
                    else:
                        current.discard("pin")
                    await cleanservice_db.save_clean_settings(chat_id, current)

                imported.append(cat_name)
            except Exception as ie:
                LOGGER.error(f"Error importing {cat_name}: {ie}")

        await m.edit_text(font(f"✅ Successfully imported settings for: {', '.join(imported)}"))
        rate_limit[chat_id] = True

    except Exception as e:
        LOGGER.error(f"Import error: {e}")
        await m.edit_text(font(f"❌ An error occurred during import: {e}"))

@pbot.on_message(filters.command("reset") & ~filters.forwarded)
@only_groups
async def reset_chat_data(client, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.chat.type == enums.ChatType.PRIVATE:
        chat_id = await connection_db.get_connected_chat(user_id) or chat_id

    creator_id = await get_chat_creator(chat_id)
    if user_id != creator_id and user_id not in [config.OWNER_ID]:
        return await message.reply_text(font("❌ Only the group creator can reset chat settings."))

    m = await message.reply_text(font("🔄 Resetting all chat settings..."))

    try:
        from AloneX.db import (
            reaction, antinsfw_db, join_request, riddle, couple
        )
        await mod.remove_all_mods(chat_id)
        await antiflood.reset_chat(chat_id)
        await blocklistwords.reset_chat_blocklist(chat_id)
        await cleancommand_db.reset_chat_cleancommand(chat_id)
        await cleanservice_db.reset_chat_cleanservice(chat_id)
        await disable.enable_all_cmds(chat_id)
        await filter_db.reset_chat_filters(chat_id)
        await greetings.clear_welcome(chat_id)
        await greetings.clear_goodbye(chat_id)
        await locks_db.reset_all_locks(chat_id)
        await notes.delete_all_notes(chat_id)
        await rules.reset_rules(chat_id)
        await rules.reset_rules_button(chat_id)
        await translate.remove_chat(chat_id)
        await federation_db.leave_fed(chat_id)
        await warn_db.reset_chat_warns(chat_id)
        await antiraid.reset_chat_antiraid(chat_id)
        await approval_db.remove_all_approved_users(chat_id)
        await antitag_db.set_antitag_limit(chat_id, 0)
        await joinmute_db.set_joinmute_duration(chat_id, 0)
        await antiforward_db.set_antiforward_status(chat_id, False)
        await mediadelete_db.delete_all_media_delete(chat_id)
        await ghost_db.set_ghost(chat_id, True) # Default is enabled
        await nightmode_db.reset_chat_nightmode(chat_id)
        await chatbot.reset_chat_chatbot(chat_id)
        await logchannel_db.unset_log_channel(chat_id)

        # New modules
        await reaction.reset_chat_reaction(chat_id)
        await antinsfw_db.reset_chat_antinsfw(chat_id)
        await join_request.reset_chat_join_request(chat_id)
        await riddle.reset_chat_riddle(chat_id)
        await couple.reset_chat_couple(chat_id)

        await m.edit_text(font("✅ All chat settings have been reset to default."))

    except Exception as e:
        LOGGER.error(f"Reset error: {e}")
        await m.edit_text(font(f"❌ An error occurred during reset: {e}"))

__mod_name__ = "𝐈ᴍᴘᴏʀᴛ/𝐄xᴘᴏʀᴛ🛠"
__help__ = """
**Import/Export Settings**

Copy your chat configuration across groups easily!

• /export: Generate a JSON file containing all your chat settings.
• /export <categories>: Export only specific categories (e.g., `/export notes filters`).
• /import: Import settings from a replied export file (Creator only).
• /import <categories>: Import only specific categories from the file.
• /reset: Reset all chat settings to default (Creator only).

**Supported Categories:**
admin, antiflood, blocklists, clean_command, clean_service, disabled, filters, greetings, locks, notes, rules, translations, warns, federations, antiraid, approvals, antitag, joinmute, antiforward, mediadelete, ghost, nightmode, chatbot, logchannel, pins, reports.

**Note:** This command is rate-limited to 1 use per 5 minutes per chat.
"""
