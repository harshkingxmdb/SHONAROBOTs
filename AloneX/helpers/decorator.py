import config
import asyncio
import secrets
from functools import wraps
from typing import Union, Callable, Any, Optional, Set, Tuple
from telegram import Update, constants, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatMemberStatus
from telegram.ext import PrefixHandler, CommandHandler, CallbackQueryHandler, MessageHandler, ChatMemberHandler, ContextTypes
from telegram.error import Forbidden, RetryAfter, TimedOut, NetworkError, BadRequest
from AloneX import app, DEV_LIST, SUDO_USERS, BOT_ID, BOT_USERNAME, PREFIX, PREMIUM_USERS, font
import pyrogram
from telegram.helpers import mention_html
from AloneX.db.disable import get_disabled
from pyrogram import Client, enums
from pyrogram.types import Message
from AloneX.db.sudo import get_all_sudo_users
from AloneX.helpers.utils import extract_user
from AloneX.helpers.mod_helper import check_mod_permission_fast
from AloneX.db import (
    mod, blocklistwords, cleancommand_db, cleanservice_db,
    disable, federation_db, translate, rules, filter as filter_db,
    antiraid, warn_db, greetings, locks_db, notes, connection_db
)
import time

class UltraCache:
    __slots__=('d','t','m','_loop')
    def __init__(self,m=100000,t=604800):self.d={};self.t=t;self.m=m;self._loop=None
    def _get_time(self):
        if self._loop is None:
            try:self._loop=asyncio.get_running_loop()
            except:return time.time()
        try:return self._loop.time()
        except:return time.time()
    def get(self,k):
        if k in self.d:
            v,e=self.d[k]
            if self._get_time()<e:return v
            del self.d[k]
        return None
    def __setitem__(self,k,v):
        if len(self.d)>=self.m:
            rm=sorted(self.d.items(),key=lambda x:x[1][1])[:self.m//10]
            for r,_ in rm:del self.d[r]
        self.d[k]=(v,self._get_time()+self.t)
    def __getitem__(self,k):return self.get(k)

disabled_cache=UltraCache(200000,0.5)
member_cache=UltraCache(200000,0.5)
sudo_cache=UltraCache(50000,0.5)
chat_type_cache=UltraCache(100000,300)
user_admin_cache=UltraCache(100000,0.5)
permission_cache=UltraCache(100000,0.5)
DISABLEABLE_CMDS={}
SPAM_USERS={}

_owner_id=config.OWNER_ID if isinstance(config.OWNER_ID,int) else config.OWNER_ID[0]
_owner_ids_set=frozenset({config.OWNER_ID} if isinstance(config.OWNER_ID,int) else set(config.OWNER_ID))
_dev_set=frozenset(config.DEV_LIST)
_sudo_set=frozenset(config.SUDO_USERS)
_support_set=frozenset(config.SUPPORT_USERS)
_whitelist_set=frozenset(config.WHITELIST_USERS)
_premium_set=frozenset(PREMIUM_USERS)
protected_ids=_owner_ids_set|_dev_set|_sudo_set|_support_set|_whitelist_set
OWNER_IDS=list(_owner_ids_set)
ALLOWED_USERS=_owner_ids_set|_dev_set|_sudo_set|_support_set|_whitelist_set
_db_sudo_users=set()
_all_sudo_combined=set(_sudo_set)
_sudo_refresh_lock=asyncio.Lock()
_last_sudo_refresh=0

async def refresh_sudo_users():
    global _db_sudo_users,_all_sudo_combined,_last_sudo_refresh
    ct=time.time()
    if ct-_last_sudo_refresh<0.5:return
    async with _sudo_refresh_lock:
        if time.time()-_last_sudo_refresh<0.5:return
        try:
            db=await get_all_sudo_users()
            _db_sudo_users=set(db)
            _all_sudo_combined=_sudo_set|_db_sudo_users
            _last_sudo_refresh=time.time()
        except:_all_sudo_combined=set(_sudo_set)

async def get_allowed_users():
    ck="allowed_v3"
    c=sudo_cache.get(ck)
    if c is not None:return c
    u=set(ALLOWED_USERS)
    try:
        if not _db_sudo_users:await refresh_sudo_users()
        u=u|_db_sudo_users
    except:pass
    sudo_cache[ck]=u
    return u

async def is_sudo_user_db(uid:int)->bool:
    if uid in _sudo_set:return True
    ck=f"s_{uid}"
    c=sudo_cache.get(ck)
    if c is not None:return c
    if not _db_sudo_users:await refresh_sudo_users()
    r=uid in _all_sudo_combined
    sudo_cache[ck]=r
    return r

async def get_disabled_cached(cid:int):
    c=disabled_cache.get(cid)
    if c is not None:return c
    r=await get_disabled(cid)
    disabled_cache[cid]=r
    return r

async def get_member_cached(bot,cid:int,uid:int):
    k=(cid,uid)
    c=member_cache.get(k)
    if c is not None:return c
    r=await bot.get_chat_member(cid,uid)
    member_cache[k]=r
    return r

async def check_user_admin_cached(bot,cid:int,uid:int)->bool:
    k=(cid,uid,'a')
    c=user_admin_cache.get(k)
    if c is not None:return c
    try:
        m=await get_member_cached(bot,cid,uid)
        ia=m.status in(ChatMemberStatus.ADMINISTRATOR,ChatMemberStatus.OWNER)
        user_admin_cache[k]=ia
        return ia
    except:return False

async def get_effective_chat_id(update: Update):
    user = update.effective_user
    chat = update.effective_chat
    if user and chat and chat.type == constants.ChatType.PRIVATE:
        conn = await connection_db.get_connected_chat(user.id)
        if conn:
            return conn
    return chat.id if chat else None

async def get_effective_chat_id_pyro(update: Union[Message, pyrogram.types.CallbackQuery]):
    if isinstance(update, pyrogram.types.CallbackQuery):
        user = update.from_user
        chat = update.message.chat if update.message else None
    else:
        user = update.from_user
        chat = update.chat

    if user and chat and chat.type == enums.ChatType.PRIVATE:
        conn = await connection_db.get_connected_chat(user.id)
        if conn:
            return conn
    return chat.id if chat else None

def loggable(func):
    @wraps(func)
    async def log_action(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        result = await func(update, context, *args, **kwargs)
        chat = update.effective_chat
        message = update.effective_message
        if result and chat:
            from AloneX.helpers.log_helper import log_action as send_log
            datetime_fmt = "%H:%M - %d-%m-%Y"
            event_stamp = f"\n\n<b>Event Stamp</b>: <code>{datetime.now().strftime(datetime_fmt)}</code>"

            link = ""
            if message and message.chat.type == constants.ChatType.SUPERGROUP and message.chat.username:
                link = f'\n<b>Link:</b> <a href="https://t.me/{message.chat.username}/{message.message_id}">click here</a>'

            # We don't have a fixed category here, so we'll use "admin" as default for decorators
            await send_log(context.bot, chat.id, "admin", result + event_stamp + link)
        return result
    return log_action

def gloggable(func):
    @wraps(func)
    async def glog_action(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        result = await func(update, context, *args, **kwargs)
        chat = update.effective_chat
        message = update.effective_message
        if result and chat:
            from AloneX.helpers.log_helper import log_action as send_log
            datetime_fmt = "%H:%M - %d-%m-%Y"
            event_stamp = f"\n\n<b>Event Stamp</b>: <code>{datetime.now().strftime(datetime_fmt)}</code>"

            link = ""
            if message and message.chat.type == constants.ChatType.SUPERGROUP and message.chat.username:
                link = f'\n<b>Link:</b> <a href="https://t.me/{message.chat.username}/{message.message_id}">click here</a>'

            # gloggable usually implies global logging, but we follow log_action logic
            await send_log(context.bot, chat.id, "admin", result + event_stamp + link)
        return result
    return glog_action

def only_premium(func):
    @wraps(func)
    async def wrapper(client,*args,**kwargs):
        try:
            if isinstance(client,Update):u=client.effective_user;m=client.effective_message
            elif isinstance(client,pyrogram.Client):m=args[0];u=m.from_user
            else:return await func(client,*args,**kwargs)
            uid=u.id
            if uid in protected_ids:return await func(client,*args,**kwargs)
            if uid not in _premium_set:
                try:await m.reply_text("⚠️ This command only works for 'AloneX Premium' users!")
                except:pass
                return
            return await func(client,*args,**kwargs)
        except:return
    return wrapper

def flood_safe(func):
    @wraps(func)
    async def wrapper(update,context,*args,**kwargs):
        try:return await func(update,context,*args,**kwargs)
        except RetryAfter as e:await asyncio.sleep(e.retry_after);return await wrapper(update,context,*args,**kwargs)
        except(TimedOut,NetworkError):await asyncio.sleep(2);return await wrapper(update,context,*args,**kwargs)
        except:return
    return wrapper


def no_self_action(func):
    @wraps(func)
    async def wrapper(update,context,*args,**kwargs):
        try:
            if update.message and update.message.reply_to_message:
                t=update.message.reply_to_message.from_user
                if t and t.id==context.bot.id:
                    asyncio.create_task(update.message.reply_text("**🤦 You are dumb! I won't ban/mute/warn myself.**"))
                    return
            return await func(update,context,*args,**kwargs)
        except:return
    return wrapper

def no_admin_action(func):
    @wraps(func)
    async def wrapper(update:Update,context,*args,**kwargs):
        try:
            if update.message and update.message.reply_to_message:
                t=update.message.reply_to_message.from_user;c=update.effective_chat
                if await check_user_admin_cached(context.bot,c.id,t.id):
                    asyncio.create_task(update.message.reply_text("**⚠️ I can't perform this action on an admin/owner!**",parse_mode='Markdown'))
                    return
            return await func(update,context,*args,**kwargs)
        except:return
    return wrapper

def disableable(name:str|list[str]=None):
    def decorator(func):
        cn=name if isinstance(name,list)else[name or func.__name__.lower()]
        for cmd in cn:DISABLEABLE_CMDS[cmd]="✅"
        @wraps(func)
        async def wrapper(*args,**kwargs):
            try:
                update_obj=None
                chat_obj=None
                if len(args)>=2:
                    if hasattr(args[0],'effective_message') and hasattr(args[0],'effective_chat'):
                        update_obj=args[0]
                        chat_obj=update_obj.effective_chat
                    elif hasattr(args[1],'chat'):
                        message=args[1]
                        chat_obj=message.chat
                elif len(args)==1:
                    if hasattr(args[0],'effective_message') and hasattr(args[0],'effective_chat'):
                        update_obj=args[0]
                        chat_obj=update_obj.effective_chat
                if "update" in kwargs:
                    update_obj=kwargs["update"]
                    if hasattr(update_obj,'effective_chat'):
                        chat_obj=update_obj.effective_chat
                if not chat_obj and update_obj and hasattr(update_obj,'effective_chat'):
                    chat_obj=update_obj.effective_chat
                if chat_obj:
                    ctk=(chat_obj.id,'t')
                    ct=chat_type_cache.get(ctk)
                    if ct is None:
                        ct=getattr(chat_obj,'type',None)
                        if ct:chat_type_cache[ctk]=ct
                    is_private=False
                    if ct:
                        if hasattr(constants,'ChatType') and hasattr(constants.ChatType,'PRIVATE'):
                            try:is_private=(ct==constants.ChatType.PRIVATE)
                            except:is_private=(str(ct).lower()=="private")
                        else:is_private=(str(ct).lower()=="private")
                    if not is_private:
                        d=await get_disabled_cached(chat_obj.id)
                        if any(cmd in d for cmd in cn):
                            for cmd in cn:DISABLEABLE_CMDS[cmd]="❌"
                            return
                        for cmd in cn:DISABLEABLE_CMDS[cmd]="✅"
                return await func(*args,**kwargs)
            except:return
        return wrapper
    return decorator

def unavailable(func):
    @wraps(func)
    async def wrapper(client,*args,**kwargs):
        try:
            if isinstance(client,Update):u=client.effective_user;m=client.effective_message
            elif isinstance(client,pyrogram.Client):m=args[0];u=m.from_user
            else:return await func(client,*args,**kwargs)
            if u.id not in _dev_set:
                asyncio.create_task(m.reply_text("⚠️ This command is temporarily unavailable for everyone!"))
                return
            return await func(client,*args,**kwargs)
        except:return
    return wrapper

def protect_sudos(func):
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        try:
            from AloneX import pbot
            m = update.effective_message
            if not m:return await func(update, context, *args, **kwargs)
            tuid = None
            if m.reply_to_message and m.reply_to_message.from_user:
                tuid = m.reply_to_message.from_user.id
            elif m.text and len(m.text.split()) > 1:
                arg = m.text.split()[1]
                if arg.isdigit():tuid = int(arg)
                elif arg.startswith('@') or True:
                    clean = arg.lstrip('@')
                    try:
                        user = await pbot.get_users(clean)
                        tuid = user.id
                    except:
                        try:
                            user = await context.bot.get_chat(arg)
                            tuid = user.id
                        except:pass
            if tuid:
                if tuid in protected_ids or await is_sudo_user_db(tuid):
                    mn = mention_html(tuid, "this protected user")
                    asyncio.create_task(m.reply_text(f"⚠️ You cannot perform this action on {mn}!",parse_mode="HTML"))
                    return
            return await func(update, context, *args, **kwargs)
        except:return
    return wrapper


def spam_control(func):
    @wraps(func)
    async def wrapper(client,*args,**kwargs):
        try:
            if hasattr(client,"send"):m=args[0];u=getattr(m,"from_user",None)
            elif hasattr(client,"bot"):update=client;m=update.effective_message;u=update.effective_user
            else:return await func(client,*args,**kwargs)
            if not u or not getattr(u,"id",None):return await func(client,*args,**kwargs)
            uid=u.id
            if uid in SPAM_USERS:
                asyncio.create_task(m.reply_text("⚠️ Wait! Don't spam commands!"))
                return
            SPAM_USERS[uid]=True
            try:return await func(client,*args,**kwargs)
            finally:SPAM_USERS.pop(uid,None)
        except:return
    return wrapper

prefix_cmds = ['!', '?', '$', '/', '\\', '.', '*', '-', '&', '#', ',']

def Command(command, filters=None, block=False, group=-999):
    def decorator(func):
        if PREFIX:
            def convert(cmd: Union[str, list]):
                if isinstance(cmd, tuple):cmd = list(cmd)
                if not isinstance(cmd, (str, list)):return
                cmds = [cmd] if isinstance(cmd, str) else cmd
                return [f"{c}{BOT_USERNAME}" for c in cmds] + cmds
            handler = PrefixHandler(prefix=prefix_cmds,command=convert(command),callback=func,filters=filters,block=block)
        else:
            handler = CommandHandler(command=command,callback=func,filters=filters,block=block)
        app.add_handler(handler, group=group) 
        return func
    return decorator
    
def Callbacks(pattern, block=True, group=0):
    def decorator(func):
        handler = CallbackQueryHandler(callback=func, pattern=pattern, block=block)
        app.add_handler(handler, group=group)
        return func
    return decorator

def Messages(filters=None,group=0,block=False):
    def decorator(func):
        handler=MessageHandler(callback=func,filters=filters,block=block)
        app.add_handler(handler,group=group)
        return func
    return decorator

def ChatMembers(chat_member_types=-1,group=0,block=False):
    def decorator(func):
        handler=ChatMemberHandler(callback=func,chat_member_types=chat_member_types,block=block)
        app.add_handler(handler,group=group)
        return func
    return decorator

def only_private(func):
    @wraps(func)
    async def wrapper(update,context):
        try:
            msg=update.effective_message;cid=msg.chat.id;ctk=(cid,'t');ct=chat_type_cache.get(ctk)
            if ct is None:ct=msg.chat.type;chat_type_cache[ctk]=ct
            if ct!=constants.ChatType.PRIVATE:
                asyncio.create_task(msg.reply_text("This command only works in private chats!"))
                return
            return await func(update,context)
        except:return
    return wrapper

def with_args(value:int=1):
    def decorator(func):
        @wraps(func)
        async def wrapper(update,context):
            try:
                args=context.args
                if len(args)!=value:
                    asyncio.create_task(update.effective_message.reply_text(f"🙋‍♂️ Please provide exactly {value} argument(s)."))
                else:return await func(update,context)
            except:return
        return wrapper
    return decorator

def devs_only(func):
    @wraps(func)
    async def wrapper(update,context,*args,**kwargs):
        try:
            m=update.effective_message
            if m.from_user and m.from_user.id in _dev_set:return await func(update,context,*args,**kwargs)
            asyncio.create_task(m.reply_text("🚫 Only Devs can use this command."))
            return
        except:return
    return wrapper

def sudos_only(func):
    @wraps(func)
    async def wrapper(update,context,*args,**kwargs):
        try:
            m=update.effective_message;u=m.from_user;txt=(m.text or"").split()[0].lower().lstrip("/!");uid=u.id
            if uid==_owner_id or uid in _sudo_set or uid in _dev_set or await is_sudo_user_db(uid):return await func(update,context,*args,**kwargs)
            asyncio.create_task(m.reply_text(f"🚫 Only Sudo users can use the `{txt}` command.",parse_mode=constants.ParseMode.MARKDOWN))
            return
        except:return
    return wrapper

def owner_only(func):
    @wraps(func)
    async def wrapper(update,context,*args,**kwargs):
        try:
            u=update.effective_user
            if not u or u.id!=_owner_id:
                asyncio.create_task(update.effective_message.reply_text("❌ Only the Owner can use this command."))
                return
            return await func(update,context,*args,**kwargs)
        except:return
    return wrapper

def support_only(func):
    @wraps(func)
    async def wrapper(update:Update,context:ContextTypes.DEFAULT_TYPE,*args,**kwargs):
        try:
            u=update.effective_user
            if not u or u.id not in _support_set:
                asyncio.create_task(update.effective_message.reply_text("❌ Only Support users can use this command."))
                return
            return await func(update,context,*args,**kwargs)
        except:return
    return wrapper

def whitelist_only(func):
    @wraps(func)
    async def wrapper(update:Update,context:ContextTypes.DEFAULT_TYPE,*args,**kwargs):
        try:
            u=update.effective_user
            if not u or u.id not in _whitelist_set:
                asyncio.create_task(update.effective_message.reply_text("❌ Only Whitelisted users can use this command."))
                return
            return await func(update,context,*args,**kwargs)
        except:return
    return wrapper

def only_users(users:list=[]):
    def decorator(func):
        @wraps(func)
        async def wrapper(update,context):
            try:
                u=update.effective_user
                if u.id in users:return await func(update,context)
                return
            except:return
        return wrapper
    return decorator

def only_groups(func):
    @wraps(func)
    async def wrapper(*args,**kwargs):
        try:
            if not args:return await func(*args,**kwargs)
            first=args[0]
            if isinstance(first,Update)or hasattr(first,"effective_message"):
                update:Update=first
                context=args[1]if len(args)>1 else kwargs.get("context")
                msg=update.effective_message
                if not msg:return await func(*args,**kwargs)
                chat=msg.chat
                if not chat:return await func(*args,**kwargs)
                cid=chat.id
                ctk=(cid,'og')
                cached=chat_type_cache.get(ctk)
                if cached is not None:
                    if not cached:
                        asyncio.create_task(msg.reply_text("❌ <b>This command only works in groups!</b>",parse_mode="HTML"))
                        return
                    return await func(*args,**kwargs)
                is_group=False
                try:
                    if hasattr(constants,'ChatType'):
                        is_group=chat.type in(constants.ChatType.GROUP,constants.ChatType.SUPERGROUP)
                    else:
                        ct_str=str(chat.type).lower()
                        is_group=any(x in ct_str for x in['group','supergroup'])
                except:
                    try:
                        ct_str=str(chat.type).lower()
                        is_group='group'in ct_str
                    except:
                        is_group=cid<0
                chat_type_cache[ctk]=is_group
                if not is_group:
                    if chat.type == constants.ChatType.PRIVATE:
                        conn = await connection_db.get_connected_chat(update.effective_user.id)
                        if conn:
                            return await func(*args,**kwargs)
                    asyncio.create_task(msg.reply_text("❌ <b>This command only works in groups!</b>",parse_mode="HTML"))
                    return
                return await func(*args,**kwargs)
            if len(args)>=2 and hasattr(args[1],"chat"):
                client:Client=first
                message:Message=args[1]
                chat=getattr(message,"chat",None)
                if not chat:return await func(*args,**kwargs)
                cid=chat.id
                ctk=(cid,'og')
                cached=chat_type_cache.get(ctk)
                if cached is not None:
                    if not cached:
                        try:asyncio.create_task(message.reply_text("❌ <b>This command only works in groups!</b>"))
                        except:pass
                        return
                    return await func(*args,**kwargs)
                is_group=False
                try:
                    if hasattr(enums,'ChatType'):
                        is_group=chat.type in(enums.ChatType.GROUP,enums.ChatType.SUPERGROUP)
                    else:
                        ct_str=str(chat.type).lower()
                        is_group=any(x in ct_str for x in['group','supergroup'])
                except:
                    try:
                        ct_str=str(chat.type).lower()
                        is_group='group'in ct_str
                    except:
                        is_group=cid<0
                chat_type_cache[ctk]=is_group
                if not is_group:
                    if chat.type == enums.ChatType.PRIVATE:
                        conn = await connection_db.get_connected_chat(message.from_user.id)
                        if conn:
                            return await func(*args,**kwargs)
                    try:asyncio.create_task(message.reply_text("❌ <b>This command only works in groups!</b>"))
                    except:pass
                    return
                return await func(*args,**kwargs)
            return await func(*args,**kwargs)
        except:return await func(*args,**kwargs)
    return wrapper                                            

                                   

def send_action(action):
    def decorator(func):
        @wraps(func)
        async def command_func(update,context,*args,**kwargs):
            asyncio.create_task(context.bot.send_chat_action(chat_id=update.effective_chat.id,action=action))
            return await func(update,context,*args,**kwargs)
        return command_func
    return decorator

def RestrictedCallback(func):
    @wraps(func)
    async def wrapper(update:Update,context:ContextTypes.DEFAULT_TYPE,*args,**kwargs):
        try:
            q=update.callback_query;uid=q.from_user.id;allowed=await get_allowed_users()
            if uid not in allowed:
                asyncio.create_task(q.answer("⛔ This button isn't for you!",show_alert=True))
                return
            return await func(update,context,*args,**kwargs)
        except:return
    return wrapper

def group_owner_only(func):
    @wraps(func)
    async def wrapper(update:Update,context:ContextTypes.DEFAULT_TYPE,*args,**kwargs):
        try:
            chat=update.effective_chat;u=update.effective_user;m=await get_member_cached(context.bot,chat.id,u.id)
            if m.status!=ChatMemberStatus.OWNER:
                asyncio.create_task(update.effective_message.reply_text("🚫 This command is only for the group owner!"))
                return
            return await func(update,context,*args,**kwargs)
        except:return
    return wrapper

PERMISSION_MAP = {
    'ban': 'can_restrict_members',
    'restrict': 'can_restrict_members',
    'kick': 'can_restrict_members',
    'mute': 'can_restrict_members',
    'warn': 'can_restrict_members',
    'unban': 'can_restrict_members',
    'unmute': 'can_restrict_members',
    'promote': 'can_promote_members',
    'demote': 'can_promote_members',
    'invite': 'can_invite_users',
    'pin': 'can_pin_messages',
    'unpin': 'can_pin_messages',
    'delete': 'can_delete_messages',
    'manage': 'can_manage_chat',
}

ANON_VERIFICATIONS = {}

def user_admin(func):
    @wraps(func)
    async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        chat = update.effective_chat
        user = update.effective_user
        if not user or not chat:
            return
        if user.id in protected_ids:
            return await func(update, context, *args, **kwargs)
        if chat.type == constants.ChatType.PRIVATE:
            return await func(update, context, *args, **kwargs)
        member = await get_member_cached(context.bot, chat.id, user.id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await func(update, context, *args, **kwargs)
        await update.effective_message.reply_text(font("❌ You must be an admin to use this command!"))
    return is_admin

def admin_check(permission:str=None,protect_target:bool=True,check_mods:bool=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(update,context,*args,**kwargs):
            try:
                chat=update.effective_chat;u=update.effective_user;m=update.effective_message
                if not m or not chat:return
                cid = await get_effective_chat_id(update)
                is_callback = getattr(update,'callback_query',None) is not None
                if getattr(m,'sender_chat',None) and not is_callback:
                    token=secrets.token_urlsafe(16)
                    ANON_VERIFICATIONS[token]={'cid':cid,'func':func,'context':context,'args':args,'kwargs':kwargs,'permission':permission,'protect_target':protect_target,'original_update':update,'check_mods':check_mods}
                    kb=InlineKeyboardMarkup([[InlineKeyboardButton(font("Click here to prove admin"),callback_data=f"anon_verify:{token}")]])
                    try:await m.reply_text("It looks like you're anonymous. Tap this button to confirm your identity.",reply_markup=kb)
                    except:pass
                    return
                uid=u.id if u else None
                q=None
                action_name=permission or "perform this action"
                if is_callback:
                    q=update.callback_query
                    callback_data=q.data
                    if "_" in callback_data:
                        action_name=callback_data.split("_")[0]
                    def send_response(txt):
                        asyncio.create_task(q.answer(txt,show_alert=True))
                else:
                    def send_response(txt):
                        asyncio.create_task(m.reply_text(txt))
                ctk=(cid,'t');ct=chat_type_cache.get(ctk)
                if ct is None:ct=chat.type;chat_type_cache[ctk]=ct
                if ct==constants.ChatType.PRIVATE and cid == chat.id:return await func(update,context,*args,**kwargs)
                if uid==1087968824:return await func(update,context,*args,**kwargs)
                try:
                    bm = await get_member_cached(context.bot, cid, context.bot.id)
                    if bm.status not in [constants.ChatMemberStatus.ADMINISTRATOR, constants.ChatMemberStatus.OWNER]:
                        send_response("❌ I'm not an admin in this chat.")
                        return
                    if permission:
                        actual_perm = PERMISSION_MAP.get(permission, permission)
                        if not getattr(bm, actual_perm, False):
                            send_response(f"❌ I'm missing the `{permission}` permission.")
                            return
                except Forbidden:
                    send_response("❌ I don't have access to this chat anymore.")
                    return
                except BadRequest as e:
                    if "Chat_admin_required" in str(e):
                        send_response("❌ I need to be an admin to check permissions.")
                        return
                    raise
                try:
                    um = await get_member_cached(context.bot, cid, uid)
                    is_user_sudo = await is_sudo_user_db(uid)
                    if um.status == constants.ChatMemberStatus.OWNER or uid in _dev_set or is_user_sudo:
                        pass
                    elif um.status == constants.ChatMemberStatus.ADMINISTRATOR:
                        allowed = False
                        if permission:
                            actual_user_perm = PERMISSION_MAP.get(permission, permission)
                            if getattr(um, actual_user_perm, False):
                                allowed = True
                            elif check_mods:
                                has_mod_perm = await check_mod_permission_fast(cid, uid, permission, chat)
                                if has_mod_perm:
                                    allowed = True
                        else:
                            allowed = True
                        
                        if not allowed:
                            if check_mods:
                                send_response(f"❌ You don't have permission to {action_name}!")
                            else:
                                send_response(f"❌ You are missing the `{permission}` permission.")
                            return
                    else:
                        if check_mods:
                            has_mod_perm = await check_mod_permission_fast(cid, uid, permission, chat)
                            if not has_mod_perm:
                                send_response(f"❌ You are not an admin and don't have mod permission!")
                                return
                        else:
                            send_response("❌ You are not an admin in this chat.")
                            return
                except:
                    if check_mods:
                        has_mod_perm = await check_mod_permission_fast(cid, uid, permission, chat)
                        if not has_mod_perm:
                            send_response(f"❌ You don't have permission to {action_name}!")
                            return
                    else:
                        send_response("❌ Failed to verify admin status!")
                        return
                if protect_target:
                    tuid=None;tu=None
                    try:
                        tuid=await extract_user(m,self=False)
                        if tuid:
                            try:tm=await get_member_cached(context.bot,cid,tuid);tu=tm.user
                            except:
                                try:tu=await context.bot.get_chat(tuid)
                                except:pass
                    except:pass
                    is_target_sudo=await is_sudo_user_db(tuid)if tuid else False
                    if tuid and(tuid in _dev_set or is_target_sudo):send_response("❌ You cannot apply this command to protected users.");return
                    if tu:
                        try:
                            tm=await get_member_cached(context.bot,cid,tuid)
                            if tm.status==constants.ChatMemberStatus.OWNER:send_response("❌ You cannot apply this command to the chat owner.");return
                        except:pass
                return await func(update,context,*args,**kwargs)
            except Exception as e:print(e);return
        return wrapper
    return decorator

def mod_permission(permission: str = None, protect_target: bool = True):
    return admin_check(permission=permission, protect_target=protect_target, check_mods=True)

@Callbacks(r"^anon_verify:")
async def handle_anon_verification(update:Update,context:ContextTypes.DEFAULT_TYPE):
    try:
        q=update.callback_query;await q.answer()
        token=q.data.split(":",1)[1]
        if token not in ANON_VERIFICATIONS:
            try:await q.edit_message_text("❌ Verification expired or invalid!")
            except:pass
            return
        vdata=ANON_VERIFICATIONS.pop(token)
        cid=vdata['cid'];uid=q.from_user.id
        if q.message.chat.id!=cid:
            await q.answer("❌ Wrong chat!",show_alert=True)
            return
        check_mods=vdata.get('check_mods',True)
        perm=vdata.get('permission')
        try:
            bm = await get_member_cached(context.bot, cid, context.bot.id)
            if bm.status not in [constants.ChatMemberStatus.ADMINISTRATOR, constants.ChatMemberStatus.OWNER]:
                try:await q.edit_message_text("❌ I'm not an admin in this chat!")
                except:pass
                return
            if perm:
                actual_perm = PERMISSION_MAP.get(perm, perm)
                if not getattr(bm, actual_perm, False):
                    try:await q.edit_message_text(f"❌ I'm missing the `{perm}` permission!")
                    except:pass
                    return
        except:
            try:await q.edit_message_text("❌ Failed to verify bot permissions!")
            except:pass
            return
        try:
            um = await get_member_cached(context.bot, cid, uid)
            is_user_sudo = await is_sudo_user_db(uid)
            if um.status == constants.ChatMemberStatus.OWNER or uid in _dev_set or is_user_sudo:
                pass
            elif um.status == constants.ChatMemberStatus.ADMINISTRATOR:
                allowed = False
                if perm:
                    actual_user_perm = PERMISSION_MAP.get(perm, perm)
                    if getattr(um, actual_user_perm, False):
                        allowed = True
                    elif check_mods:
                        has_mod_perm = await check_mod_permission_fast(cid, uid, perm, q.message.chat)
                        if has_mod_perm:
                            allowed = True
                else:
                    allowed = True
                
                if not allowed:
                    if check_mods:
                        try:await q.edit_message_text(f"❌ You don't have permission to {perm}!")
                        except:pass
                    else:
                        try:await q.edit_message_text(f"❌ You are missing the `{perm}` permission!")
                        except:pass
                    return
            else:
                if check_mods:
                    has_mod_perm = await check_mod_permission_fast(cid, uid, perm, q.message.chat)
                    if not has_mod_perm:
                        try:await q.edit_message_text("❌ You are not an admin and don't have mod permission!")
                        except:pass
                        return
                else:
                    try:await q.edit_message_text("❌ You are not an admin in this chat!")
                    except:pass
                    return
        except:
            if check_mods:
                has_mod_perm = await check_mod_permission_fast(cid, uid, perm, q.message.chat)
                if not has_mod_perm:
                    try:await q.edit_message_text(f"❌ You don't have permission to {perm}!")
                    except:pass
                    return
            else:
                try:await q.edit_message_text("❌ Failed to verify admin status!")
                except:pass
                return
        try:await q.message.delete()
        except:pass
        func=vdata['func'];ctx=vdata['context'];args=vdata['args'];kwargs=vdata['kwargs'];orig_update=vdata['original_update']
        class FakeUpdate:
            def __init__(self,orig_update,new_user):
                self.effective_chat=orig_update.effective_chat
                self.effective_message=orig_update.effective_message
                self.effective_user=new_user
                self.callback_query=None
                self.message=orig_update.effective_message
                self._chat_member=None
                self._my_chat_member=None
            def __getattr__(self,name):
                try:return getattr(self._orig_update,name)
                except:return None
        fake_update=FakeUpdate(orig_update,q.from_user)
        await func(fake_update,ctx,*args,**kwargs)
    except Exception as e:
        print(e)
