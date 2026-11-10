import config
from functools import lru_cache
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ButtonStyle
from AloneX import MODULE, font

@lru_cache(maxsize=256)
def _font_cached(text):
    return font(text)

def arrange_buttons(buttons_list, columns=2):
    arranged = []
    for i in range(0, len(buttons_list), columns):
        arranged.append(buttons_list[i:i+columns])
    return arranged

def dict_to_keyboard(data):
    keyboard = [[InlineKeyboardButton(**button) for button in row] for row in data['inline_keyboard']]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

_MODULE_SORTED = None
_MODULE_BUTTONS_CACHE = {}

def _get_sorted_modules():
    global _MODULE_SORTED
    if _MODULE_SORTED is None:
        _MODULE_SORTED = sorted(MODULE.items(), key=lambda x: x[0])
    return _MODULE_SORTED

@lru_cache(maxsize=128)
def help_keyboard_data(user_id: int, rows: int = 10, columns: int = 3):
    modules = _get_sorted_modules()
    pages = []
    page = []
    row = []
    for i, (module_name, module_help) in enumerate(modules):
        button = InlineKeyboardButton(text=_font_cached(module_name.capitalize()), callback_data=f"help_{module_name}_{user_id}", style=ButtonStyle.SUCCESS)
        row.append(button)
        if len(row) == columns:
            page.append(row)
            row = []
        if len(page) == rows:
            pages.append(page)
            page = []
    if row:
        page.append(row)
    if page:
        pages.append(page)
    return pages

@lru_cache(maxsize=128)
def help_button(user_id):
    buttons = []
    row = []
    sorted_modules = _get_sorted_modules()
    for i, (module, help) in enumerate(sorted_modules):
        button = InlineKeyboardButton(text=_font_cached(module.capitalize()), callback_data=f"help_{module}_{user_id}", style=ButtonStyle.SUCCESS)
        row.append(button)
        if (i+1) % 3 == 0 or i == len(sorted_modules) - 1:
            buttons.append(row)
            row = []
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def get_help_button(message, user):
    cache_key = f"{user.id}_{config.BTN_ROWS}_{config.BTN_COLUMNS}"
    if cache_key in _MODULE_BUTTONS_CACHE:
        return _MODULE_BUTTONS_CACHE[cache_key]
    
    buttons = help_keyboard_data(user_id=user.id, rows=config.BTN_ROWS, columns=config.BTN_COLUMNS)
    if not buttons:
        return None
    
    page_number = 0
    current_page = [row[:] for row in buttons[page_number]]
    nav_buttons = []
    
    if len(buttons) > 1:
        nav_buttons.append(InlineKeyboardButton(_font_cached("❌ Close"), callback_data=f"delete#{user.id}", style=ButtonStyle.DANGER))
        nav_buttons.append(InlineKeyboardButton(_font_cached("➡️ Next"), callback_data=f"helpcq_next#{user.id}#{page_number}", style=ButtonStyle.PRIMARY))
    else:
        nav_buttons.append(InlineKeyboardButton(_font_cached("❌ Close"), callback_data=f"delete#{user.id}", style=ButtonStyle.DANGER))
    
    current_page.append(nav_buttons)
    current_page.append([InlineKeyboardButton(font("🔄 Back"), callback_data=f"back_{user.id}", style=ButtonStyle.PRIMARY)])
    
    result = InlineKeyboardMarkup(inline_keyboard=current_page)
    _MODULE_BUTTONS_CACHE[cache_key] = result
    return result
