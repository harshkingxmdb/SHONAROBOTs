import logging
from AloneX.db.logchannel_db import get_log_channel, is_category_enabled, stop_chat_logging
import config
from telegram.error import BadRequest

async def log_action(bot, chat_id: int, category: str, text: str, message_link: str = None):
    # Ensure chat_id is integer
    try:
        chat_id = int(chat_id)
    except:
        return

    # Fetch specific log channel for this group
    log_channel = await get_log_channel(chat_id)

    # Check if category is enabled for logging in this chat
    if not await is_category_enabled(chat_id, category):
        logging.debug(f"[LogAction] Category {category} is disabled for chat {chat_id}")
        return

    # Determine target. Priority: Group-specific log channel > Global Fallback
    target_channel = log_channel
    if not target_channel or target_channel == 0:
        target_channel = config.LOGS_CHANNEL
        logging.debug(f"[LogAction] No specific log channel for {chat_id}, using global fallback: {target_channel}")
    else:
        logging.debug(f"[LogAction] Using specific log channel for {chat_id}: {target_channel}")

    if not target_channel or target_channel == 0:
        logging.debug(f"[LogAction] No target channel available for {chat_id}")
        return

    # Build the log message
    full_log = f"{text}\n\n"
    full_log += f"<b>Category:</b> <code>{category}</code>\n"
    full_log += f"<b>Chat ID:</b> <code>{chat_id}</code>"

    if message_link:
        full_log += f"\n<b>Message Link:</b> <a href='{message_link}'>Click here</a>"

    # Send the log
    try:
        await bot.send_message(
            target_channel,
            full_log,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        logging.info(f"[LogAction] Successfully sent {category} log for {chat_id} to {target_channel}")
    except BadRequest as excp:
        if excp.message == "Chat not found":
            try:
                await bot.send_message(
                    chat_id, "This log channel has been deleted - unsetting."
                )
            except:
                pass
            await stop_chat_logging(chat_id)
        else:
            logging.error(f"[LogAction] BadRequest when sending log to {target_channel}: {excp.message}")
    except Exception as e:
        logging.error(f"[LogAction] Failed to send log to {target_channel} for chat {chat_id}: {e}")
