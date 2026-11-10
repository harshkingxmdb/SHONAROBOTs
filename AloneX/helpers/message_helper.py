from AloneX import font
import re
import html
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, constants, MessageEntity

DEFAULT_RULES_BUTTON = "Rules"

MARKDOWN_HELP = """
*Markdown Formatting Guide*

*Basic Formatting:*
• *bold*: wrapping text with '*' will produce bold text
Example: *hello*
• _italic_: wrapping text with '_' will produce italic text
Example: _hello_
• `code`: wrapping text with '`' will produce monospaced text, also known as 'code'
Example: `hello`
• ~strikethrough~: wrapping text with '~' will produce strikethrough text
Example: ~hello~
• __underline__: wrapping text with '__' will produce underlined text
Example: __hello__
• ||spoiler||: wrapping text with '||' will produce spoiler text (hidden)
Example: ||secret||
*Links:*
• [sometext](someURL): creates a link - message shows sometext, tapping opens someURL
Example: [Google](https://google.com)
*Code Blocks:*
Wrapping text with triple backticks (```) will produce code block:
```
code block here
```
For syntax highlighting, specify language:
```python
print("Hello")
```
*Block Quotes:*
• > text: creates a single line quote
Example:
> This is a quote
• **> text
> more text
> hidden||: creates expandable multi-line quote
Example:
**> Line 1
> Line 2
> Line 3
> hidden||
"""

class MessageHelper:
    @staticmethod
    def entities_to_markdown(text: str, entities) -> str:
        if not text or not entities:
            return text
        
        try:
            sorted_entities = sorted(entities, key=lambda e: e.offset, reverse=True)
            
            for entity in sorted_entities:
                try:
                    start = entity.offset
                    end = entity.offset + entity.length
                    
                    if start < 0 or end > len(text):
                        continue
                        
                    entity_text = text[start:end]
                    
                    if entity.type == 'bold':
                        replacement = f"*{entity_text}*"
                    elif entity.type == 'italic':
                        replacement = f"_{entity_text}_"
                    elif entity.type == 'underline':
                        replacement = f"__{entity_text}__"
                    elif entity.type == 'strikethrough':
                        replacement = f"~{entity_text}~"
                    elif entity.type == 'code':
                        replacement = f"`{entity_text}`"
                    elif entity.type == 'pre':
                        language = entity.language if hasattr(entity, 'language') and entity.language else ''
                        if language:
                            replacement = f"```{language}\n{entity_text}\n```"
                        else:
                            replacement = f"```\n{entity_text}\n```"
                    elif entity.type == 'text_link':
                        url = entity.url if hasattr(entity, 'url') else ''
                        replacement = f"[{entity_text}]({url})"
                    elif entity.type == 'spoiler':
                        replacement = f"||{entity_text}||"
                    elif entity.type == 'blockquote':
                        lines = entity_text.split('\n')
                        replacement = '\n'.join([f"> {line}" for line in lines])
                    elif entity.type == 'text_mention':
                        user_id = entity.user.id if hasattr(entity, 'user') and entity.user else ''
                        replacement = f"[{entity_text}](tg://user?id={user_id})"
                    else:
                        replacement = entity_text
                    
                    text = text[:start] + replacement + text[end:]
                except Exception as e:
                    print(f"[entities_to_markdown] Error processing entity: {e}")
                    continue
            
            return text
        except Exception as e:
            print(f"[entities_to_markdown] Error: {e}")
            return text

    @staticmethod
    def convert_markdown_to_html(text: str) -> str:
        if not text:
            return text

        try:
            preserved = {}
            counter = [0]

            def preserve(content, prefix):
                key = f"<<<{prefix}_{counter[0]}>>>"
                counter[0] += 1
                preserved[key] = content
                return key

            temp_mentions = {}
            mention_counter = [0]
            def preserve_mention(match):
                key = f"<<<MENTION_{mention_counter[0]}>>>"
                mention_counter[0] += 1
                temp_mentions[key] = match.group(0)
                return key

            text = re.sub(r'<a href="tg://user\?id=\d+">.*?</a>', preserve_mention, text)

            text = re.sub(r'```(\w+)?\n?([\s\S]*?)```', lambda m: preserve(m.group(0), 'CODEBLOCK'), text)
            text = re.sub(r'`([^`\n]+?)`', lambda m: preserve(m.group(0), 'INLINECODE'), text)
            text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: preserve(m.group(0), 'LINK'), text)
            text = re.sub(r'\*\*>[\s\S]*?>?\|\|', lambda m: preserve(m.group(0), 'EXPQUOTE'), text)
            text = re.sub(r'^>\s*.+$', lambda m: preserve(m.group(0), 'REGQUOTE'), text, flags=re.MULTILINE)
            
            spoiler_map = {}
            for match in re.finditer(r'\|\|([^\|]+?)\|\|', text):
                key = f"<<<SPOILER_{counter[0]}>>>"
                counter[0] += 1
                spoiler_map[key] = match.group(1)
                text = text.replace(match.group(0), key, 1)

            text = html.escape(text)

            for key, mention in temp_mentions.items():
                text = text.replace(html.escape(key), mention)

            text = re.sub(r'(?<![a-zA-Z0-9])__([^_\n]+?)__(?![a-zA-Z0-9])', r'<u>\1</u>', text)
            text = re.sub(r'(?<![a-zA-Z0-9\*])\*(?!\*)([^\*\n]+?)\*(?![a-zA-Z0-9\*])', r'<b>\1</b>', text)
            text = re.sub(r'(?<![a-zA-Z0-9~])~([^~\n]+?)~(?![a-zA-Z0-9~])', r'<s>\1</s>', text)
            text = re.sub(r'(?<![a-zA-Z0-9_])_([^_\n]+?)_(?![a-zA-Z0-9_])', r'<i>\1</i>', text)
            
            for key, spoiler_content in spoiler_map.items():
                escaped_key = html.escape(key)
                text = text.replace(escaped_key, f'<tg-spoiler>{spoiler_content}</tg-spoiler>')

            for key, original in preserved.items():
                if 'SPOILER_' in key:
                    continue

                escaped_key = html.escape(key)

                if 'LINK_' in key:
                    match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', original)
                    if match:
                        link_text = html.escape(match.group(1))
                        link_url = html.escape(match.group(2))
                        text = text.replace(escaped_key, f'<a href="{link_url}">{link_text}</a>')
                    else:
                        text = text.replace(escaped_key, original)

                elif 'EXPQUOTE_' in key:
                    content = original.replace('**>', '').replace('>||', '').replace('||', '')
                    lines = []
                    for line in content.strip().split('\n'):
                        line = line.strip()
                        if line.startswith('>'):
                            line = line[1:].strip()
                        if line:
                            lines.append(html.escape(line))
                    if lines:
                        text = text.replace(escaped_key, '<blockquote expandable>' + '\n'.join(lines) + '</blockquote>')
                    else:
                        text = text.replace(escaped_key, '')

                elif 'REGQUOTE_' in key:
                    content = original.strip()
                    if content.startswith('>'):
                        content = content[1:].strip()
                    text = text.replace(escaped_key, f'<blockquote>{html.escape(content)}</blockquote>')

                elif 'CODEBLOCK_' in key:
                    match = re.match(r'```(\w+)?\n?([\s\S]*?)```', original)
                    if match:
                        language = match.group(1)
                        code = match.group(2).strip()
                        
                        if language:
                            text = text.replace(escaped_key, f'<pre><code class="language-{html.escape(language)}">{html.escape(code)}</code></pre>')
                        else:
                            text = text.replace(escaped_key, f'<pre><code>{html.escape(code)}</code></pre>')
                    else:
                        code_content = original[3:-3].strip()
                        text = text.replace(escaped_key, f'<pre><code>{html.escape(code_content)}</code></pre>')

                elif 'INLINECODE_' in key:
                    code = original[1:-1]
                    text = text.replace(escaped_key, f'<code>{html.escape(code)}</code>')

            return text.strip()
        except Exception as e:
            print(f"[convert_markdown_to_html] Error: {e}")
            return text

    @staticmethod
    def dict_to_keyboard(data: Dict) -> Optional[InlineKeyboardMarkup]:
        if not data or 'inline_keyboard' not in data:
            return None
        try:
            keyboard = [
                [InlineKeyboardButton(**button) for button in row]
                for row in data['inline_keyboard']
            ]
            return InlineKeyboardMarkup(keyboard)
        except Exception as e:
            print(f"[dict_to_keyboard] Error: {e}")
            return None

    @staticmethod
    def parse_buttons_from_text(text: str) -> Tuple[str, Optional[Dict], bool, bool, int]:
        if not text:
            return text, None, False, False, -1

        try:
            has_rules_placeholder = '{rules}' in text
            has_rules_same = '{rules:same}' in text
            
            rules_position = -1
            if has_rules_same:
                rules_position = text.find('{rules:same}')
                text = text.replace('{rules:same}', '')
            elif has_rules_placeholder:
                rules_position = text.find('{rules}')
                text = text.replace('{rules}', '')

            button_pattern = r'\[([^\]]+)\]\(buttonurl://([^\)]+)\)'
            button_matches = list(re.finditer(button_pattern, text))
            
            rules_target_row = -1
            
            if has_rules_same and rules_position != -1 and button_matches:
                first_button_idx = None
                for idx, match in enumerate(button_matches):
                    if match.start() > rules_position:
                        first_button_idx = idx
                        break
                
                if first_button_idx is not None:
                    if first_button_idx == 0:
                        rules_target_row = 0
                    else:
                        row_count = 0
                        
                        for i in range(first_button_idx):
                            if i == 0:
                                row_count = 0
                            else:
                                prev_button_data = button_matches[i-1].group(2).strip()
                                is_prev_same = prev_button_data.endswith(':same')
                                if not is_prev_same:
                                    row_count += 1
                        
                        rules_target_row = row_count
            
            buttons = []
            current_row = []
            
            for idx, match in enumerate(button_matches):
                button_text = match.group(1).strip()
                button_data = match.group(2).strip()

                is_same_line = button_data.endswith(':same')
                button_url = button_data.replace(':same', '').strip()

                button = {'text': button_text, 'url': button_url}

                if is_same_line and current_row:
                    current_row.append(button)
                else:
                    if current_row:
                        buttons.append(current_row)
                    current_row = [button]

            if current_row:
                buttons.append(current_row)

            clean_text = re.sub(button_pattern, '', text)
            clean_text = re.sub(r'\n\s*\n+', '\n\n', clean_text).strip()

            keyboard_data = {'inline_keyboard': buttons} if buttons else None

            return clean_text, keyboard_data, has_rules_placeholder or has_rules_same, has_rules_same, rules_target_row

        except Exception as e:
            print(f"[parse_buttons_from_text] Error: {e}")
            return text, None, False, False, -1

    @staticmethod
    async def add_rules_button(keyboard_data: Optional[Dict], chat_id: int, bot_username: str, rules_button_text: str = None, same_line: bool = False, target_row: int = -1) -> Dict:
        try:
            button_text = rules_button_text or DEFAULT_RULES_BUTTON

            rules_button = {
                'text': button_text,
                'url': f"https://t.me/{bot_username}?start=rules_{chat_id}"
            }

            if not keyboard_data or 'inline_keyboard' not in keyboard_data:
                keyboard_data = {'inline_keyboard': [[rules_button]]}
                return keyboard_data

            if same_line and target_row >= 0:
                if target_row < len(keyboard_data['inline_keyboard']):
                    keyboard_data['inline_keyboard'][target_row].append(rules_button)
                else:
                    if keyboard_data['inline_keyboard']:
                        keyboard_data['inline_keyboard'][-1].append(rules_button)
                    else:
                        keyboard_data['inline_keyboard'].append([rules_button])
            elif same_line:
                if keyboard_data['inline_keyboard']:
                    keyboard_data['inline_keyboard'][-1].append(rules_button)
                else:
                    keyboard_data['inline_keyboard'].append([rules_button])
            else:
                keyboard_data['inline_keyboard'].append([rules_button])

            return keyboard_data
        except Exception as e:
            print(f"[add_rules_button] Error: {e}")
            return keyboard_data or {'inline_keyboard': []}

    @staticmethod
    async def convert_fillings(text: str, user, chat, context=None) -> Tuple[str, Dict]:
        if not text:
            return "", {}

        send_options = {
            'disable_web_page_preview': True,
            'disable_notification': False,
            'protect_content': False
        }

        try:
            current_time = datetime.now()

            member_count = "Unknown"
            try:
                if hasattr(chat, 'get_member_count'):
                    member_count = str(await chat.get_member_count())
                elif hasattr(chat, 'get_members_count'):
                    member_count = str(await chat.get_members_count())
                elif context and hasattr(context.bot, 'get_chat_member_count'):
                    member_count = str(await context.bot.get_chat_member_count(chat.id))
            except Exception as e:
                print(f"[convert_fillings] Error getting member count: {e}")
                member_count = "N/A"

            option_pattern = r'\{(preview|preview:top|nonotif|protect|mediaspoiler)\}'
            matches = re.findall(option_pattern, text)
            
            for match in matches:
                if match == 'preview':
                    send_options['disable_web_page_preview'] = False
                elif match == 'preview:top':
                    send_options['disable_web_page_preview'] = False
                    send_options['show_above_text'] = True
                elif match == 'nonotif':
                    send_options['disable_notification'] = True
                elif match == 'protect':
                    send_options['protect_content'] = True
                elif match == 'mediaspoiler':
                    send_options['has_spoiler'] = True
            
            text = re.sub(option_pattern, '', text)

            user_first_name = html.escape(user.first_name or "User")
            user_last_name = html.escape(user.last_name or "")
            user_full_name = html.escape(user.full_name or user.first_name or "User")
            user_mention = f'<a href="tg://user?id={user.id}">{user_first_name}</a>\u200b'
            username_display = (f"@{html.escape(user.username)}\u200b") if user.username else user_mention
            chat_title = html.escape(chat.title or "Chat")

            replacements = {
                '{first}': user_first_name,
                '{last}': user_last_name,
                '{fullname}': user_full_name,
                '{username}': username_display,
                '{mention}': user_mention,
                '{id}': str(user.id),
                '{chatname}': chat_title,
                '{chat_id}': str(chat.id),
                '{name}': user_full_name,
                '{user_id}': str(user.id),
                '{chat}': chat_title,
                '{first_name}': user_first_name,
                '{count}': member_count,
                '{date}': current_time.strftime("%Y-%m-%d"),
                '{time}': current_time.strftime("%H:%M:%S"),
            }

            text = MessageHelper.convert_markdown_to_html(text)

            for placeholder, replacement in replacements.items():
                text = text.replace(placeholder, str(replacement))
            
            text = text.strip()
            return text, send_options

        except Exception as e:
            print(f"[convert_fillings] Error: {e}")
            return text, send_options

    @staticmethod
    def get_media_info(bot, message) -> Tuple[Optional[str], Optional[str], Optional[callable]]:
        try:
            media_types = {
                'photo': (message.photo, bot.send_photo),
                'animation': (message.animation, bot.send_animation),
                'document': (message.document, bot.send_document),
                'sticker': (message.sticker, bot.send_sticker),
                'audio': (message.audio, bot.send_audio),
                'video': (message.video, bot.send_video),
                'voice': (message.voice, bot.send_voice),
                'video_note': (message.video_note, bot.send_video_note)
            }

            for media_type, (media_obj, send_method) in media_types.items():
                if media_obj:
                    if media_type == 'photo':
                        return media_type, media_obj[-1].file_id, send_method
                    else:
                        return media_type, media_obj.file_id, send_method

            return None, None, None
        except Exception as e:
            print(f"[get_media_info] Error: {e}")
            return None, None, None
            
    @staticmethod
    def get_send_method(bot, file_type: str):
        file_type = file_type.lower()
        types = {
            'photo': bot.send_photo,
            'video': bot.send_video,
            'audio': bot.send_audio,
            'text': bot.send_message,
            'document': bot.send_document,
            'animation': bot.send_animation,
            'sticker': bot.send_sticker,
            'voice': bot.send_voice,
            'video_note': bot.send_video_note
        }
        return types.get(file_type, bot.send_message)

    @staticmethod
    def validate_time(time_str: str) -> Optional[int]:
        try:
            time_val = int(time_str)
            if time_val < 5:
                return None
            if time_val > 86400:
                return None
            return time_val
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def cleanup_temp_data(temp_dict: dict, chat_id: int, timeout: int = 600):
        try:
            if chat_id in temp_dict:
                data = temp_dict[chat_id]
                if 'timestamp' in data:
                    if datetime.now().timestamp() - data['timestamp'] > timeout:
                        del temp_dict[chat_id]
        except Exception as e:
            print(f"[cleanup_temp_data] Error: {e}")
    
    @staticmethod
    def parse_random_content(text: str) -> str:
        if not text or '%%%' not in text:
            return text
        
        try:
            options = [opt.strip() for opt in text.split('%%%') if opt.strip()]
            if options:
                import random
                return random.choice(options)
            return text
        except Exception as e:
            print(f"[parse_random_content] Error: {e}")
            return text
    
    @staticmethod
    async def send_message(bot, chat_id: int, data: Dict, user, chat, context, rules_button_text: str = None):
        try:
            text = data.get('text')
            file_type = data.get('file_type', 'text')
            file_id = data.get('file_id')
            keyboard_data = data.get('keyboard')
            has_rules_button = data.get('has_rules_button', False)
            has_rules_same = data.get('has_rules_same', False)
            rules_target_row = data.get('rules_target_row', -1)
            
            text = MessageHelper.parse_random_content(text)
            
            send_options = {}
            if text:
                text, send_options = await MessageHelper.convert_fillings(text, user, chat, context)
            
            if has_rules_button:
                if not rules_button_text:
                    rules_button_text = DEFAULT_RULES_BUTTON
                
                keyboard_data = await MessageHelper.add_rules_button(
                    keyboard_data, 
                    chat_id, 
                    context.bot.username,
                    rules_button_text,
                    same_line=has_rules_same,
                    target_row=rules_target_row
                )
            
            keyboard = MessageHelper.dict_to_keyboard(keyboard_data) if keyboard_data else None
            
            method = MessageHelper.get_send_method(bot, file_type)
            
            use_markdownv2 = bool(re.search(r'\|\|[^\|]+\|\|', text or ''))
            
            send_kwargs = {
                'reply_markup': keyboard,
                'parse_mode': constants.ParseMode.MARKDOWN_V2 if use_markdownv2 else constants.ParseMode.HTML
            }
            
            if use_markdownv2 and text:
                escape_chars = r'_*[]()~`>#+=|{}.!-'
                spoilers = re.findall(r'\|\|[^\|]+\|\|', text)
                for i, spoiler in enumerate(spoilers):
                    text = text.replace(spoiler, f'<<<SPOILER_{i}>>>')
                
                for char in escape_chars:
                    text = text.replace(char, f'\\{char}')
                
                for i, spoiler in enumerate(spoilers):
                    text = text.replace(f'<<<SPOILER_{i}>>>', spoiler)
            
            if file_type == "text":
                send_kwargs.update(send_options)
                return await method(chat_id, text=text, **send_kwargs)
            else:
                media_allowed_options = ['disable_notification', 'protect_content', 'has_spoiler']
                for key in media_allowed_options:
                    if key in send_options:
                        send_kwargs[key] = send_options[key]
                
                return await method(chat_id, file_id, caption=text, **send_kwargs)
                
        except Exception as e:
            print(f"[send_message] Error: {e}")
            return None
    
    @staticmethod
    def create_setup_buttons(button_type: str, chat_id: int) -> InlineKeyboardMarkup:
        prefix = 'wel' if button_type == 'welcome' else 'gb'
        
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(font('👀 Preview'), callback_data=f'{prefix}_chk#{chat_id}'),
                InlineKeyboardButton(font('✅ Confirm'), callback_data=f'{prefix}_verify#{chat_id}')
            ],
            [InlineKeyboardButton(font('❌ Cancel'), callback_data=f'{prefix}_cancel#{chat_id}')]
        ])
    
    @staticmethod
    def get_help_text() -> str:
        return """
❂ *Greetings Module* — Welcome and farewell messages for your group.

❂ *Commands*:
❂ `/setwelcome` — Reply to a message or type directly to set welcome.  
❂ `/clearwelcome` — Remove the current welcome message.  
❂ `/getwelcome` — Show the current welcome message.  
❂ `/setwelcometime <sec>` — Set auto-delete timer for welcome messages.
❂ `/welcome <on|off>` — Enable or disable welcome messages.
❂ `/setgoodbye` — Reply to a message or type directly to set goodbye.  
❂ `/cleargoodbye` — Remove the current goodbye message.  
❂ `/getgoodbye` — Show the current goodbye message.  
❂ `/setgoodbyetime <sec>` — Set auto-delete timer for goodbye messages.
❂ `/goodbye <on|off>` — Enable or disable goodbye messages.
"""
    
    @staticmethod
    def get_formatting_help() -> str:
        return MARKDOWN_HELP
    
    @staticmethod
    def get_fillings_help() -> str:
        return """
*Available Fillings:*

*User Info:*
• `{first}` — User's first name
• `{last}` — User's last name  
• `{fullname}` — User's full name
• `{username}` — @username or mention
• `{mention}` — Mention user
• `{id}` — User's ID

*Chat Info:*
• `{chatname}` — Chat name
• `{chat_id}` — Chat ID
• `{count}` — Member count
• `{date}` — Current date (YYYY-MM-DD)
• `{time}` — Current time (HH:MM:SS)

*Buttons:*
• `{rules}` — Add rules button (new row)
• `{rules:same}` — Rules button (same row)

*Options:*
• `{preview}` — Enable link previews
• `{preview:top}` — Preview above text
• `{nonotif}` — No notification
• `{protect}` — Prevent forward/screenshot
• `{mediaspoiler}` — Mark media as spoiler

*Examples:*
• `Welcome *{first}*! {rules}`
• `_Hello_ {mention} to {chatname}`
• `Filter triggered by {username}`
"""
    
    @staticmethod
    def get_buttons_help() -> str:
        return """
*Button Syntax:*

*Simple Button:*
`[Google](buttonurl://google.com)`
Creates button "Google" → google.com

*Same Line Buttons:*
`[Google](buttonurl://google.com)
[Bing](buttonurl://bing.com:same)`
Use `:same` for same row

*Note Buttons:*
`[My Note](buttonurl://#note_name)`
Links to saved note

*Complete Example:*
```
*Welcome to our group!*

[Rules](buttonurl://example.com/rules)
[Support](buttonurl://t.me/support:same)
[Notes](buttonurl://#help)
```
"""
    
    @staticmethod
    def get_random_content_help() -> str:
        return """
*Random Content:*

Use `%%%` to separate random variants.

*Example:*
```
Hello {first}!
%%%
Welcome {mention}!
%%%
Hey there {username}!
```

Each time randomly picks one variant!

*Works in:*
• Welcome messages
• Goodbye messages
• Filters
• Notes
• Anywhere!
"""
