import re
from AloneX.helpers.data.fonts import Fonts

def apply_custom_font(text: str) -> str:
    if not text:
        return ""

    # regex to find segments outside of HTML tags
    # this will help avoid styling HTML tags like <b>, <i>, <code>, etc.
    segments = re.split(r'(<[^>]+>)', text)

    styled_segments = []
    for segment in segments:
        if segment.startswith('<') and segment.endswith('>'):
            # This is an HTML tag, don't style it
            styled_segments.append(segment)
        else:
            # Style the content segment
            styled_text = ""
            for char in segment:
                if char.isupper():
                    styled_text += Fonts.serief(char)
                elif char.islower():
                    styled_text += Fonts.smallcap(char)
                else:
                    styled_text += char
            styled_segments.append(styled_text)

    return "".join(styled_segments)
