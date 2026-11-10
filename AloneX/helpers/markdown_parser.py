import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Optional, Tuple, Dict, List

def parse_buttons_from_text(text: str) -> Tuple[str, Optional[Dict]]:
    """
    Parse inline buttons from text using buttonurl syntax
    
    Supported formats:
    - [Button Text](buttonurl://url)
    - [Button1](buttonurl://url1)[Button2](buttonurl://url2:same)
    - Multiple rows without :same
    
    Returns:
        Tuple of (clean_text, keyboard_dict)
    """
    if not text:
        return text, None
    
    try:
        button_pattern = r'\[([^\]]+)\]\(buttonurl://([^\)]+)\)'
        buttons = []
        current_row = []
        
        for match in re.finditer(button_pattern, text):
            button_text = match.group(1).strip()
            button_data = match.group(2).strip()
            
            # Check if button should be on same line
            is_same_line = button_data.endswith(':same')
            button_url = button_data.replace(':same', '').strip()
            
            button = {'text': button_text, 'url': button_url}
            
            if is_same_line and current_row:
                current_row.append(button)
            else:
                if current_row:
                    buttons.append(current_row)
                current_row = [button]
        
        # Add last row
        if current_row:
            buttons.append(current_row)
        
        # Remove button syntax from text
        clean_text = re.sub(button_pattern, '', text)
        # Clean up extra newlines
        clean_text = re.sub(r'\n\s*\n+', '\n\n', clean_text).strip()
        
        keyboard_data = {'inline_keyboard': buttons} if buttons else None
        
        return clean_text, keyboard_data
        
    except Exception as e:
        print(f"Error parsing buttons: {e}")
        return text, None


def dict_to_keyboard(data: Optional[Dict]) -> Optional[InlineKeyboardMarkup]:
    """
    Convert dictionary to InlineKeyboardMarkup
    
    Args:
        data: Dictionary with 'inline_keyboard' key containing button data
        
    Returns:
        InlineKeyboardMarkup or None
    """
    if not data or 'inline_keyboard' not in data:
        return None
    
    try:
        keyboard = [
            [InlineKeyboardButton(**button) for button in row] 
            for row in data['inline_keyboard']
        ]
        return InlineKeyboardMarkup(keyboard)
    except Exception as e:
        print(f"Error converting dict to keyboard: {e}")
        return None


def keyboard_to_dict(markup: InlineKeyboardMarkup) -> Optional[Dict]:
    """
    Convert InlineKeyboardMarkup to dictionary
    
    Args:
        markup: InlineKeyboardMarkup object
        
    Returns:
        Dictionary representation or None
    """
    if not markup:
        return None
    
    try:
        return markup.to_dict()
    except Exception as e:
        print(f"Error converting keyboard to dict: {e}")
        return None


def format_buttons_help() -> str:
    """Return formatted help text for button syntax"""
    return (
        "*Button Syntax:*\n"
        "• Single button: `[Text](buttonurl://url)`\n"
        "• Same line: `[Btn1](buttonurl://url1:same)[Btn2](buttonurl://url2)`\n"
        "• Multiple rows: Just add buttons without `:same`\n\n"
        "*Examples:*\n"
        "```\n"
        "[Visit Site](buttonurl://https://example.com)\n"
        "[Help](buttonurl://t.me/support:same)[Donate](buttonurl://paypal.me/user)\n"
        "```"
    )


def validate_button_url(url: str) -> bool:
    """
    Validate if URL is properly formatted
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False
    
    # Basic URL validation
    url_pattern = re.compile(
        r'^(https?://)?'  # Optional protocol
        r'([a-zA-Z0-9.-]+)'  # Domain
        r'(\.[a-zA-Z]{2,})'  # TLD
        r'(/.*)?$',  # Optional path
        re.IGNORECASE
    )
    
    return bool(url_pattern.match(url))


def extract_button_count(text: str) -> int:
    """
    Count how many buttons are in the text
    
    Args:
        text: Text containing button syntax
        
    Returns:
        Number of buttons found
    """
    if not text:
        return 0
    
    button_pattern = r'\[([^\]]+)\]\(buttonurl://([^\)]+)\)'
    return len(re.findall(button_pattern, text))


def has_buttons(text: str) -> bool:
    """
    Check if text contains button syntax
    
    Args:
        text: Text to check
        
    Returns:
        True if buttons found, False otherwise
    """
    return extract_button_count(text) > 0
