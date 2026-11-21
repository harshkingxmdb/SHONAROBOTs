__module__ = "𝐐ᴜᴏᴛʟʏ✨"
__help__ = """
*Commands*:
/q
*Description:*
📌 Reply to a message to convert it into a stylish quote sticker.
*Usage:*
❂ `/q [number] [color] [r/reply]` — Quote messages in your preferred style and color
*Available Colors:*
red, blue, green, yellow, pink, purple, white, cream, mint, lavender, grey, black, darkred, darkblue, darkgreen, orange, cyan, magenta, brown, navy, teal, maroon, random
*Examples:*
`/q` — Quote 1 message
`/q 3` — Quote 3 messages
`/q red` — Quote 1 message with red background
`/q 2 blue` — Quote 2 messages with blue background
`/q r` — Quote message WITH reply
`/q 3 r` — Quote 3 messages WITH replies
`/q reply red` — Quote with reply in red background
`/q orange` — Quote with orange background
`/q random` — Quote with random background color
"""

import asyncio
import io
import os
from functools import lru_cache
from random import choice
from PIL import Image, ImageDraw, ImageFont
from telethon import events
from telethon.utils import get_display_name
from AloneX import tbot, prefix_cmds, font

all_col = ["#110022", "#8B0000", "#006400", "#00008B", "#4B0082", "#2F4F4F", "#8B4513", "#483D8B", "#2E8B57", "#B22222", "#FF0000", "#0000FF", "#00FF00", "#FFFF00", "#FF69B4", "#800080", "#FFFFFF", "#FFFDD0", "#98FF98", "#E6E6FA", "#808080", "#FFA500", "#00FFFF", "#FF00FF", "#000080", "#008080", "#800000"]

color_map = {
    "red": "#FF0000", "blue": "#0000FF", "green": "#00FF00", "yellow": "#FFFF00",
    "pink": "#FF69B4", "purple": "#800080", "white": "#FFFFFF", "cream": "#FFFDD0",
    "mint": "#98FF98", "lavender": "#E6E6FA", "grey": "#808080", "black": "#110022",
    "darkred": "#8B0000", "darkblue": "#00008B", "darkgreen": "#006400", "orange": "#FFA500",
    "cyan": "#00FFFF", "magenta": "#FF00FF", "brown": "#8B4513", "navy": "#000080",
    "teal": "#008080", "maroon": "#800000",
}


DEFAULT_BG = "#110022"
NAME_COLORS = ["#FF8A80", "#82B1FF", "#B9F6CA", "#FFE57F", "#EA80FC", "#80DEEA", "#FFAB91"]
FONT_REG = ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf"]
FONT_BOLD = ["DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"]


@lru_cache(maxsize=16)
def _font(size: int, bold: bool = False):
    for path in (FONT_BOLD if bold else FONT_REG):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)       # Pillow >= 10.1 can scale the built-in font
    except TypeError:
        return ImageFont.load_default()


def _is_light(hex_color: str) -> bool:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) > 150


def _wrap(draw, text: str, font_obj, max_w: int):
    lines = []
    for para in (text or " ").split("\n"):
        cur = ""
        for word in para.split(" "):
            cand = f"{cur} {word}" if cur else word
            if draw.textlength(cand, font=font_obj) <= max_w:
                cur = cand
                continue
            if cur:
                lines.append(cur)
            while len(word) > 1 and draw.textlength(word, font=font_obj) > max_w:
                cut = len(word)
                while cut > 1 and draw.textlength(word[:cut], font=font_obj) > max_w:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            cur = word
        lines.append(cur)
    return lines


def render_quote(entries, bg_hex: str) -> bytes:
    """Draw the quote as a transparent webp sticker (512 px max), no external API."""
    W, PAD, AV, GAP, R = 512, 16, 44, 12, 28
    bub_x = PAD + AV + 12
    bub_w = W - bub_x - PAD
    text_w = bub_w - 40
    name_f, text_f, rep_f = _font(22, True), _font(24), _font(19)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    light = _is_light(bg_hex)
    text_col = "#111111" if light else "#FFFFFF"
    rep_col = "#444444" if light else "#C8CDD6"

    blocks = []
    for e in entries:
        lines = _wrap(probe, e["text"], text_f, text_w)[:18]
        rep_lines = []
        if e.get("reply"):
            rep_lines = _wrap(probe, f"{e['reply']['name']}: {e['reply']['text']}", rep_f, text_w)[:2]
        h = 14 + 30 + (len(rep_lines) * 24 + 8 if rep_lines else 0) + len(lines) * 32 + 14
        blocks.append((e, lines, rep_lines, max(h, 70)))

    total_h = PAD + sum(b[3] for b in blocks) + GAP * (len(blocks) - 1) + PAD
    img = Image.new("RGBA", (W, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = PAD
    for e, lines, rep_lines, h in blocks:
        # avatar: colored circle with the first letter
        color = NAME_COLORS[e.get("uid", 0) % len(NAME_COLORS)]
        ay = y + 6
        draw.ellipse((PAD, ay, PAD + AV, ay + AV), fill=color)
        initial = (e["name"][:1] or "?").upper()
        iw = draw.textlength(initial, font=name_f)
        draw.text((PAD + (AV - iw) / 2, ay + 8), initial, font=name_f, fill="#111111")

        # bubble in the chosen background color
        draw.rounded_rectangle((bub_x, y, bub_x + bub_w, y + h), radius=R, fill=bg_hex)
        tx, ty = bub_x + 20, y + 14
        name = e["name"]
        while len(name) > 1 and draw.textlength(name, font=name_f) > text_w:
            name = name[:-1]
        if name != e["name"]:
            name = name.rstrip() + "…"
        draw.text((tx, ty), name, font=name_f, fill=color)
        ty += 30
        for rl in rep_lines:
            draw.text((tx, ty), rl, font=rep_f, fill=rep_col)
            ty += 24
        if rep_lines:
            ty += 8
        for line in lines:
            draw.text((tx, ty), line, font=text_f, fill=text_col)
            ty += 32
        y += h + GAP

    if max(img.size) > 512:
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    img.save(out, "WEBP", quality=95)
    return out.getvalue()


def _entry_from_event(ev, name_override=None, uid_override=None, reply=None):
    text = ev.raw_text or ev.message or ""
    if not text and ev.media:
        text = "[Media]"
    return {
        "name": name_override or "Unknown",
        "uid": uid_override or 0,
        "text": text,
        "reply": reply,
    }


async def _sender_of(ev):
    try:
        sender = await ev.get_sender()
        if sender:
            return get_display_name(sender), getattr(sender, "id", 0)
    except Exception:
        pass
    if ev.fwd_from and getattr(ev.fwd_from, "from_name", None):
        return ev.fwd_from.from_name, 0
    return "Deleted Account", 0


async def quote_handler(event):
    if (hasattr(event, 'is_channel') and event.is_channel and not getattr(event, 'is_group', False)) or getattr(event, 'fwd_from', None):
        return

    match = event.pattern_match.group(1).strip() if event.pattern_match.group(1) else ""

    if not event.is_reply:
        await event.reply(font("❂ **Please reply to a message to create a quote.**"))
        return

    msg = await event.reply(font("❂ **Creating quote...**"))
    file_name = f"quote_{os.urandom(4).hex()}.webp"

    try:
        reply = await event.get_reply_message()
        if not reply:
            await msg.edit("❂ **Error: Could not get replied message.**")
            return

        replied_to = None
        reply_ = [reply]
        color_choice = None

        if match:
            spli_ = match.split(maxsplit=1)
            if spli_[0] in ["r", "reply"]:
                try:
                    replied_to = await reply.get_reply_message()
                except Exception:
                    pass
                match = spli_[1] if len(spli_) > 1 else None
            elif spli_[0].isdigit():
                num = int(spli_[0])
                if 1 <= num <= 20:
                    reply_ = []
                    for i in range(num):
                        try:
                            m = await event.client.get_messages(event.chat_id, ids=reply.id + i)
                            if m:
                                reply_.append(m)
                        except Exception:
                            pass
                    if not reply_:
                        reply_ = [reply]
                match = spli_[1] if len(spli_) > 1 else None
            elif spli_[0].lower() in color_map or spli_[0] == "random":
                color_choice = spli_[0].lower()
                match = spli_[1] if len(spli_) > 1 else None

        user = None
        if match:
            match_parts = match.split(maxsplit=1)
            if match_parts[0].startswith("@") or match_parts[0].isdigit():
                try:
                    user = await event.client.get_entity(match_parts[0] if match_parts[0].startswith("@") else int(match_parts[0]))
                except Exception:
                    pass
                match = match_parts[1] if len(match_parts) == 2 else None
            elif match_parts[0].lower() in color_map or match_parts[0] == "random":
                color_choice = match_parts[0].lower()

        if color_choice and color_choice in color_map:
            bg = color_map[color_choice]
        elif color_choice == "random":
            bg = choice(all_col)
        else:
            bg = DEFAULT_BG

        reply_data = None
        if replied_to is not None:
            r_name, _ = await _sender_of(replied_to)
            reply_data = {"name": r_name, "text": replied_to.raw_text or replied_to.message or "[Media]"}

        await msg.edit("❂ **Processing...**")
        entries = []
        for m in reply_:
            if user:
                name, uid = get_display_name(user), getattr(user, "id", 0)
            else:
                name, uid = await _sender_of(m)
            entries.append(_entry_from_event(m, name_override=name, uid_override=uid, reply=reply_data))

        data = await asyncio.to_thread(render_quote, entries, bg)
        with open(file_name, "wb") as fh:
            fh.write(data)

        await msg.edit("❂ **Uploading sticker...**")
        await event.reply(file=file_name)
        await msg.delete()

    except asyncio.TimeoutError:
        try:
            await msg.edit("❂ **Error:** `Timeout while processing. Please try again.`")
        except Exception:
            pass
    except Exception as e:
        try:
            await msg.edit(f"❂ **Error:** `{str(e)[:100]}`")
        except Exception:
            pass
        print(f"Quote error: {e}")
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

if "quotely" not in tbot.handlers_loaded:
    tbot.add_event_handler(quote_handler, events.NewMessage(pattern=f"^{prefix_cmds}q(?: |$)(.*)", incoming=True))
    tbot.handlers_loaded.add("quotely")
