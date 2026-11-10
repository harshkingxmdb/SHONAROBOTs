from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery, ChatAdministratorRights
from pyrogram.enums import ChatMemberStatus, MessageEntityType, ChatType
from AloneX import pbot as app, prefix_cmds, font

perm_cache = {}
title_cache = {}
waiting_for_title = {}

PERMISSIONS = [
    ("can_manage_chat", "Manage Chat"),
    ("can_delete_messages", "Delete Messages"),
    ("can_manage_video_chats", "Manage Video Chats"),
    ("can_restrict_members", "Restrict Members"),
    ("can_promote_members", "Promote Members"),
    ("can_change_info", "Change Info"),
    ("can_invite_users", "Invite Users"),
    ("can_pin_messages", "Pin Messages"),
  #  ("can_manage_topics", "Edit Member Tags"),
    ("can_post_stories", "Post Stories"),
    ("can_edit_stories", "Edit Stories of Others"),
    ("can_delete_stories", "Delete Stories of Others"),
    ("is_anonymous", "Anonymous"),
]

def cache_key(chat_id: int, user_id: int) -> str:
    return f"{chat_id}:{user_id}"

async def extract_user_pyro(message: Message):
    if message.reply_to_message:
        return message.reply_to_message.from_user.id if message.reply_to_message.from_user else None
    if message.text and message.entities:
        for entity in message.entities:
            if entity.type == MessageEntityType.TEXT_MENTION:
                return entity.user.id
            elif entity.type == MessageEntityType.MENTION:
                username = message.text[entity.offset:entity.offset + entity.length].lstrip('@')
                try:
                    user = await app.get_users(username)
                    return user.id
                except:
                    continue
    if message.command and len(message.command) > 1:
        arg = message.command[1]
        arg = arg.lstrip('@')
        if arg.isdigit():
            return int(arg)
        try:
            user = await app.get_users(arg)
            return user.id
        except:
            pass
    return None

async def get_current_perms(chat_id: int, user_id: int):
    try:
        member = await app.get_chat_member(chat_id, user_id)
        if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER) and member.privileges:
            perms = {}
            for key, _ in PERMISSIONS:
                perms[key] = getattr(member.privileges, key, False)
            return perms
    except:
        pass
    return {key: True if key == "can_manage_video_chats" else False for key, _ in PERMISSIONS}
    
from pyrogram.enums import ButtonStyle

def build_keyboard(chat_id: int, user_id: int, perms: dict, has_title: bool = False):
    buttons = []
    for i in range(0, len(PERMISSIONS), 2):
        row = []
        for j in range(2):
            if i + j < len(PERMISSIONS):
                key, label = PERMISSIONS[i + j]
                icon = "✅" if perms.get(key, False) else "❌"
                style = ButtonStyle.SUCCESS if perms.get(key, False) else ButtonStyle.DANGER
                row.append(InlineKeyboardButton(f"{icon} {label}", callback_data=f"ap|t|{key}|{chat_id}|{user_id}", style=style))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(f"{'📝' if has_title else '➕'} Edit Custom Title", callback_data=f"ap|title|{chat_id}|{user_id}", style=ButtonStyle.PRIMARY)])
    buttons.append([
        InlineKeyboardButton(font("⚡ Full Rights"), callback_data=f"ap|full|{chat_id}|{user_id}", style=ButtonStyle.SUCCESS),
        InlineKeyboardButton(font("🔄 Reset"), callback_data=f"ap|reset|{chat_id}|{user_id}", style=ButtonStyle.PRIMARY)
    ])
    buttons.append([InlineKeyboardButton(font("🔧 Manage in DM"), callback_data=f"ap|manage|{chat_id}|{user_id}", style=ButtonStyle.PRIMARY)])
    buttons.append([
        InlineKeyboardButton(font("✅ Promote"), callback_data=f"ap|promote|{chat_id}|{user_id}", style=ButtonStyle.SUCCESS),
        InlineKeyboardButton(font("❌ Close"), callback_data=f"ap|close|{chat_id}|{user_id}", style=ButtonStyle.DANGER)
    ])
    return InlineKeyboardMarkup(buttons)

def build_manage_keyboard(chat_id: int, user_id: int, perms: dict, has_title: bool = False):
    buttons = []
    for i in range(0, len(PERMISSIONS), 2):
        row = []
        for j in range(2):
            if i + j < len(PERMISSIONS):
                key, label = PERMISSIONS[i + j]
                icon = "✅" if perms.get(key, False) else "❌"
                style = ButtonStyle.SUCCESS if perms.get(key, False) else ButtonStyle.DANGER
                row.append(InlineKeyboardButton(f"{icon} {label}", callback_data=f"mg|t|{key}|{chat_id}|{user_id}", style=style))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(f"{'📝' if has_title else '➕'} Edit Custom Title", callback_data=f"mg|title|{chat_id}|{user_id}", style=ButtonStyle.PRIMARY)])
    buttons.append([
        InlineKeyboardButton(font("⚡ Full Rights"), callback_data=f"mg|full|{chat_id}|{user_id}", style=ButtonStyle.SUCCESS),
        InlineKeyboardButton(font("🔄 Reset"), callback_data=f"mg|reset|{chat_id}|{user_id}", style=ButtonStyle.PRIMARY)
    ])
    buttons.append([
        InlineKeyboardButton(font("✅ Apply"), callback_data=f"mg|apply|{chat_id}|{user_id}", style=ButtonStyle.SUCCESS),
        InlineKeyboardButton(font("❌ Cancel"), callback_data=f"mg|cancel|{chat_id}|{user_id}", style=ButtonStyle.DANGER)
    ])
    return InlineKeyboardMarkup(buttons)

async def check_bot_perms(chat_id: int):
    try:
        bot = await app.get_chat_member(chat_id, "me")
        if bot.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return False, "I'm not admin in this chat", None
        if not bot.privileges or not bot.privileges.can_promote_members:
            return False, "I don't have Add Admins permission", None
        return True, "", bot
    except Exception as e:
        return False, f"Error: {str(e)}", None

async def check_user_perms(chat_id: int, user_id: int, invoker_id: int):
    """Check if invoker has permission to promote/demote the target user"""
    try:
        # Get chat info
        chat = await app.get_chat(chat_id)
        
        # Get invoker member info
        invoker = await app.get_chat_member(chat_id, invoker_id)
        
        # Only owner and admins with can_promote_members can use this
        if invoker.status == ChatMemberStatus.OWNER:
            pass  # Owner can do anything
        elif invoker.status == ChatMemberStatus.ADMINISTRATOR:
            if not invoker.privileges or not invoker.privileges.can_promote_members:
                return False, "You don't have permission to promote members"
        else:
            return False, "You must be admin to use this"
        
        # Get target member info
        target = await app.get_chat_member(chat_id, user_id)
        
        # Check if target is owner
        if target.status == ChatMemberStatus.OWNER:
            return False, "Cannot modify owner permissions"
        
        # If target is admin and invoker is not owner (in channels/supergroups)
        if target.status == ChatMemberStatus.ADMINISTRATOR and invoker.status != ChatMemberStatus.OWNER:
            # In channels, only owner can modify other admins
            if chat.type == ChatType.CHANNEL:
                return False, "Only owner can modify admin permissions in channels"
        
        return True, ""
    except Exception as e:
        return False, f"Error checking permissions: {str(e)}"

async def get_user_details(user_id: int):
    try:
        user = await app.get_users(user_id)
        return user, f"@{user.username}" if user.username else "No username"
    except:
        return None, "Unknown"

async def safe_promote(chat_id: int, user_id: int, privileges: ChatAdministratorRights, title: str = None):
    """Safely promote user with proper error handling"""
    try:
        # Check if user is already admin
        try:
            member = await app.get_chat_member(chat_id, user_id)
            is_admin = member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
        except:
            is_admin = False
        
        # Get chat type
        try:
            chat = await app.get_chat(chat_id)
            is_channel = chat.type == ChatType.CHANNEL
        except:
            is_channel = False
        
        # If user is already admin, we need to update privileges
        if is_admin:
            # For channels, we use a different method
            if is_channel:
                try:
                    # First demote then promote with new permissions
                    await app.promote_chat_member(
                        chat_id, 
                        user_id,
                        privileges=ChatAdministratorRights()
                    )
                    await app.promote_chat_member(
                        chat_id, 
                        user_id,
                        privileges=privileges
                    )
                except Exception as e:
                    # If still fails, return error
                    return False, f"Failed to update admin: {str(e)}"
            else:
                # For groups, direct update should work
                await app.promote_chat_member(
                    chat_id, 
                    user_id,
                    privileges=privileges
                )
        else:
            # New promotion
            await app.promote_chat_member(
                chat_id, 
                user_id,
                privileges=privileges
            )
        
        # Set title if provided
        if title:
            try:
                await app.set_administrator_title(chat_id, user_id, title)
            except Exception as e:
                return True, f"Promoted but failed to set title: {str(e)}"
        
        return True, "updated" if is_admin else "promoted"
        
    except Exception as e:
        error_msg = str(e).lower()
        
        if "chat_admin_required" in error_msg:
            return False, "I need to be admin with promote members permission"
        elif "user_creator" in error_msg:
            return False, "Cannot modify owner permissions"
        elif "user_not_participant" in error_msg:
            return False, "User is not a member of this chat"
        elif "right_forbidden" in error_msg:
            return False, "I don't have permission to assign these rights"
        else:
            return False, f"Failed: {str(e)}"

@app.on_message(filters.command(["admin"], prefix_cmds) & filters.group & ~filters.via_bot & ~filters.forwarded, group=-622)
async def open_admin_panel(_, message: Message):
    if not message.from_user or message.sender_chat:
        return
    
    # Check bot permissions
    success, error_msg, bot_member = await check_bot_perms(message.chat.id)
    if not success:
        return await message.reply(f"❌ I have no power - {error_msg}")
    
    # Extract target user
    user_id = await extract_user_pyro(message)
    if not user_id:
        return await message.reply(font("❌ Reply to user or mention them or provide user ID"))
    
    # Get user details
    user, username = await get_user_details(user_id)
    if not user:
        return await message.reply(font("❌ User not found"))
    
    if user.is_bot:
        return await message.reply(font("❌ Cannot promote bots"))
    
    if user_id == message.from_user.id:
        return await message.reply(font("❌ Cannot promote yourself"))
    
    # Check if invoker has permission to promote this user
    can_promote, perm_error = await check_user_perms(message.chat.id, user_id, message.from_user.id)
    if not can_promote:
        return await message.reply(f"❌ {perm_error}")
    
    # Cache permissions
    key = cache_key(message.chat.id, user_id)
    current_perms = await get_current_perms(message.chat.id, user_id)
    perm_cache[key] = current_perms
    
    # Check and cache title
    try:
        member = await app.get_chat_member(message.chat.id, user_id)
        if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            current_title = member.custom_title if hasattr(member, 'custom_title') and member.custom_title else None
            title_cache[key] = current_title
    except:
        title_cache.pop(key, None)
    
    await message.reply(
        f"🔧 Admin Panel\n\n"
        f"👤 User: {user.mention}\n"
        f"🆔 ID: {user_id}\n"
        f"📝 Username: {username}\n\n"
        f"Toggle permissions:",
        reply_markup=build_keyboard(message.chat.id, user_id, perm_cache[key], title_cache.get(key) is not None)
    )

@app.on_callback_query(filters.regex(r"^ap\|"), group=-622)
async def handle_callback(_, query: CallbackQuery):
    try:
        parts = query.data.split("|")
        action = parts[1]
        chat_id = int(parts[-2])
        user_id = int(parts[-1])
        key = cache_key(chat_id, user_id)
        perms = perm_cache.get(key, {})
        current_title = title_cache.get(key)
    except:
        return await query.answer(font("❌ Invalid data"), show_alert=True)
    
    # Check if invoker still has permission
    can_promote, perm_error = await check_user_perms(chat_id, user_id, query.from_user.id)
    if not can_promote:
        return await query.answer(f"❌ {perm_error}", show_alert=True)
    
    if action == "t":
        perm_key = parts[2]
        perms[perm_key] = not perms.get(perm_key, False)
        perm_cache[key] = perms
        try:
            await query.message.edit_reply_markup(build_keyboard(chat_id, user_id, perms, current_title is not None))
        except:
            pass
        await query.answer(f"{'✅ Enabled' if perms[perm_key] else '❌ Disabled'}")
        
    elif action == "title":
        waiting_for_title[query.from_user.id] = key
        await query.answer(font("📝 Send admin title in group (max 16 chars)"), show_alert=True)
        
    elif action == "full":
        for perm_key, _ in PERMISSIONS:
            perms[perm_key] = True
        perm_cache[key] = perms
        try:
            await query.message.edit_reply_markup(build_keyboard(chat_id, user_id, perms, current_title is not None))
        except:
            pass
        await query.answer(font("⚡ Full rights enabled"))
        
    elif action == "reset":
        perms = {perm_key: True if perm_key == "can_invite_users" else False for perm_key, _ in PERMISSIONS}
        perm_cache[key] = perms
        try:
            await query.message.edit_reply_markup(build_keyboard(chat_id, user_id, perms, current_title is not None))
        except:
            pass
        await query.answer(font("🔄 Reset to default"))
        
    elif action == "manage":
        bot_username = (await app.get_me()).username
        dm_button = InlineKeyboardMarkup([[InlineKeyboardButton(font("📱 Open in DM"), url=f"https://t.me/{bot_username}?start=manage_{chat_id}_{user_id}", style=ButtonStyle.PRIMARY)]])
        try:
            await query.message.edit_text(
                f"🔧 Manage Admin Rights\n\n"
                f"🆔 User: {user_id}\n"
                f"💬 Chat: {chat_id}\n\n"
                f"Click button to manage in DM:",
                reply_markup=dm_button
            )
            await query.answer(font("Click button to open DM"))
        except:
            await query.answer(font("❌ Error"), show_alert=True)
            
    elif action == "close":
        perm_cache.pop(key, None)
        title_cache.pop(key, None)
        waiting_for_title.pop(query.from_user.id, None)
        try:
            await query.message.delete()
        except:
            pass
            
    elif action == "promote":
        # Check bot permissions
        success, error_msg, bot_member = await check_bot_perms(chat_id)
        if not success:
            return await query.message.edit_text(f"❌ I have no power - {error_msg}")
        
        # Check if bot has all required permissions
        missing = []
        for perm_key in perms:
            if perms[perm_key]:
                if not getattr(bot_member.privileges, perm_key, False):
                    missing.append(perm_key.replace("can_", "").replace("_", " ").title())
        
        if missing:
            missing_text = "\n• ".join(missing)
            return await query.message.edit_text(f"❌ I don't have these permissions:\n• {missing_text}")
        
        # Create privileges object
        try:
            privileges = ChatAdministratorRights(**perms)
        except Exception as e:
            return await query.message.edit_text(f"❌ Invalid permissions: {str(e)}")
        
        # Promote user
        success, result = await safe_promote(chat_id, user_id, privileges, current_title)
        
        if success:
            # Clear cache
            perm_cache.pop(key, None)
            title_cache.pop(key, None)
            waiting_for_title.pop(query.from_user.id, None)
            
            title_text = f" with title '{current_title}'" if current_title else ""
            await query.message.edit_text(f"✅ User {result}{title_text}")
        else:
            await query.message.edit_text(f"❌ {result}")

@app.on_callback_query(filters.regex(r"^mg\|"), group=-622)
async def handle_manage_callback(_, query: CallbackQuery):
    try:
        parts = query.data.split("|")
        action = parts[1]
        chat_id = int(parts[-2])
        user_id = int(parts[-1])
        key = cache_key(chat_id, user_id)
        perms = perm_cache.get(key, {})
        current_title = title_cache.get(key)
    except:
        return await query.answer(font("❌ Invalid data"), show_alert=True)
    
    # Check if invoker still has permission
    can_promote, perm_error = await check_user_perms(chat_id, user_id, query.from_user.id)
    if not can_promote:
        return await query.answer(f"❌ {perm_error}", show_alert=True)
    
    if action == "t":
        perm_key = parts[2]
        perms[perm_key] = not perms.get(perm_key, False)
        perm_cache[key] = perms
        try:
            await query.message.edit_reply_markup(build_manage_keyboard(chat_id, user_id, perms, current_title is not None))
        except:
            pass
        await query.answer(f"{'✅ Enabled' if perms[perm_key] else '❌ Disabled'}")
        
    elif action == "title":
        waiting_for_title[query.from_user.id] = key
        await query.answer(font("📝 Send admin title in DM (max 16 chars)"), show_alert=True)
        
    elif action == "full":
        for perm_key, _ in PERMISSIONS:
            perms[perm_key] = True
        perm_cache[key] = perms
        try:
            await query.message.edit_reply_markup(build_manage_keyboard(chat_id, user_id, perms, current_title is not None))
        except:
            pass
        await query.answer(font("⚡ Full rights enabled"))
        
    elif action == "reset":
        perms = {perm_key: True if perm_key == "can_invite_users" else False for perm_key, _ in PERMISSIONS}
        perm_cache[key] = perms
        try:
            await query.message.edit_reply_markup(build_manage_keyboard(chat_id, user_id, perms, current_title is not None))
        except:
            pass
        await query.answer(font("🔄 Reset to default"))
        
    elif action == "apply":
        # Check bot permissions
        success, error_msg, bot_member = await check_bot_perms(chat_id)
        if not success:
            return await query.message.edit_text(f"❌ I have no power - {error_msg}")
        
        # Check if bot has all required permissions
        missing = []
        for perm_key in perms:
            if perms[perm_key]:
                if not getattr(bot_member.privileges, perm_key, False):
                    missing.append(perm_key.replace("can_", "").replace("_", " ").title())
        
        if missing:
            missing_text = "\n• ".join(missing)
            return await query.message.edit_text(f"❌ I don't have these permissions:\n• {missing_text}")
        
        # Create privileges object
        try:
            privileges = ChatAdministratorRights(**perms)
        except Exception as e:
            return await query.message.edit_text(f"❌ Invalid permissions: {str(e)}")
        
        # Promote user
        success, result = await safe_promote(chat_id, user_id, privileges, current_title)
        
        if success:
            # Clear cache
            perm_cache.pop(key, None)
            title_cache.pop(key, None)
            waiting_for_title.pop(query.from_user.id, None)
            
            title_text = f" with title '{current_title}'" if current_title else ""
            await query.message.edit_text(f"✅ User {result}{title_text}")
        else:
            await query.message.edit_text(f"❌ {result}")
            
    elif action == "cancel":
        perm_cache.pop(key, None)
        title_cache.pop(key, None)
        waiting_for_title.pop(query.from_user.id, None)
        try:
            await query.message.delete()
            await query.answer(font("❌ Cancelled"))
        except:
            pass

async def handle_admin_deeplink(message, args):
    if args.startswith("manage_"):
        try:
            parts = args.split("_")
            chat_id = int(parts[1])
            user_id = int(parts[2])
            
            # Check if invoker has permission
            can_promote, perm_error = await check_user_perms(chat_id, user_id, message.from_user.id)
            if not can_promote:
                return await message.reply(f"❌ {perm_error}")
            
            key = cache_key(chat_id, user_id)
            if key not in perm_cache:
                current_perms = await get_current_perms(chat_id, user_id)
                perm_cache[key] = current_perms
                try:
                    member = await app.get_chat_member(chat_id, user_id)
                    if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                        current_title = member.custom_title if hasattr(member, 'custom_title') and member.custom_title else None
                        title_cache[key] = current_title
                except:
                    title_cache.pop(key, None)
            
            perms = perm_cache.get(key, {})
            current_title = title_cache.get(key)
            user, username = await get_user_details(user_id)
            
            try:
                chat = await app.get_chat(chat_id)
                chat_name = chat.title or f"Chat {chat_id}"
            except:
                chat_name = f"Chat {chat_id}"
            
            await message.reply(
                f"🔧 Manage Admin Rights\n\n"
                f"👤 User: {user.mention if user else user_id}\n"
                f"🆔 ID: {user_id}\n"
                f"💬 Chat: {chat_name}\n"
                f"📝 Username: {username}\n\n"
                f"Toggle permissions:",
                reply_markup=build_manage_keyboard(chat_id, user_id, perms, current_title is not None)
            )
            return True
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")
            return True
    return False

@app.on_message(filters.text & filters.group & ~filters.via_bot & ~filters.forwarded, group=-622)
async def capture_title_group(_, message: Message):
    if not message.from_user or message.sender_chat:
        return
    user_id = message.from_user.id
    if user_id not in waiting_for_title:
        return
    
    key = waiting_for_title.pop(user_id)
    title = message.text.strip()
    
    if len(title) > 16:
        return await message.reply(font("❌ Title must be 16 chars max"))
    
    title_cache[key] = title
    
    try:
        chat_id, target_user_id = map(int, key.split(":"))
        perms = perm_cache.get(key, {})
        await message.reply(
            f"✅ Title set: {title}",
            reply_markup=build_keyboard(chat_id, target_user_id, perms, True)
        )
    except:
        await message.reply(f"✅ Title saved: {title}")

@app.on_message(filters.text & filters.private, group=-622)
async def capture_title_dm(_, message: Message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    if user_id not in waiting_for_title:
        return
    
    key = waiting_for_title.pop(user_id)
    title = message.text.strip()
    
    if len(title) > 16:
        return await message.reply(font("❌ Title must be 16 chars max"))
    
    title_cache[key] = title
    
    try:
        chat_id, target_user_id = map(int, key.split(":"))
        perms = perm_cache.get(key, {})
        await message.reply(
            f"✅ Title set: {title}",
            reply_markup=build_manage_keyboard(chat_id, target_user_id, perms, True)
        )
    except:
        await message.reply(f"✅ Title saved: {title}")
