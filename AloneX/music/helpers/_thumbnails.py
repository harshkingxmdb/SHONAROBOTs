# Now-playing thumbnail — "label design":
#   • full-width blurred background made from the song's own cover
#   • square cover in the middle
#   • dark-red band at the bottom with a dotted line on its top edge
#   • song name (big, left of the cover) + SINGER / DURATION / VIEWS (right)

import os
import re

import aiohttp
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from AloneX.music import config, logger
from AloneX.music.helpers import Track

HERE = os.path.dirname(os.path.abspath(__file__))

# optional: drop a condensed bold font (Bebas Neue / Oswald-Bold / Anton) into
# AloneX/helpers/ and it is picked up automatically for the exact look.
_CONDENSED = ["BebasNeue-Regular.ttf", "Oswald-Bold.ttf", "Anton-Regular.ttf"]


class Thumbnail:
    def __init__(self):
        self.width = 1280
        self.height = 720
        self.ss = 2  # supersampling: drawn at 2x, then shrunk = smooth edges

        # ---- layout (1280x720 space) ----
        self.band_top = 535
        self.band_color = (107, 17, 20)
        self.cover_size = 402
        self.cover_x = 431          # cover is centred horizontally
        self.cover_y = 254
        self.title_right = 414      # title is right-aligned to this x
        self.title_left = 40
        self.title_center_y = 596
        self.info_x = 847
        self.info_right = 1235

        # ---- fonts ----
        self.title_font_path = os.path.join(HERE, "Raleway-Bold.ttf")
        self.title_squeeze = 0.84   # fake "condensed" look for Raleway
        for name in _CONDENSED:
            p = os.path.join(HERE, name)
            if os.path.exists(p):
                self.title_font_path, self.title_squeeze = p, 1.0
                break
        self.value_font_path = self.title_font_path
        self.value_squeeze = 0.92 if self.title_squeeze != 1.0 else 1.0
        self.label_font_path = os.path.join(HERE, "Inter-Light.ttf")

    # ---------------- helpers ----------------

    async def save_thumb(self, output_path: str, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"thumbnail download failed ({resp.status})")
                with open(output_path, "wb") as f:
                    f.write(await resp.read())
        return output_path

    @staticmethod
    def clean_title(title: str) -> str:
        t = re.sub(r"[\(\[].*?[\)\]]", "", title or "")   # (Official Video) [4K] ...
        t = re.sub(r"[\(\[].*$", "", t)                   # cut-off bracket
        t = re.split(r"\s[|•]\s|\s-\s(?=official)", t, flags=re.I)[0]
        t = re.sub(r"\s+", " ", t).strip(" -|•")
        return (t or title or "Unknown").upper()

    @staticmethod
    def _trim_bars(img: Image.Image) -> Image.Image:
        """Removes the black letter-box bars YouTube thumbnails sometimes have."""
        mask = img.convert("L").point(lambda p: 255 if p > 14 else 0)
        box = mask.getbbox()
        if box:
            w, h = box[2] - box[0], box[3] - box[1]
            if w * h > 0.45 * img.width * img.height:
                return img.crop(box)
        return img

    @staticmethod
    def _cover_fit(img: Image.Image, w: int, h: int) -> Image.Image:
        """Scales + centre-crops `img` so it fully covers w x h."""
        scale = max(w / img.width, h / img.height)
        nw, nh = max(int(img.width * scale), w), max(int(img.height * scale), h)
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left, top = (nw - w) // 2, (nh - h) // 2
        return img.crop((left, top, left + w, top + h))

    def _font(self, path: str, size: float) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(path, max(int(round(size * self.ss)), 1))

    def _text_w(self, text: str, font, squeeze: float) -> float:
        return font.getlength(text) * squeeze / self.ss

    def _draw_text(self, canvas, text, font, fill, x, baseline, squeeze=1.0, align="left", stroke=0):
        """Draws text with its baseline at `baseline` (1280-space coords).
        align='left' -> x is the left edge, 'right' -> x is the right edge."""
        if not text:
            return
        ss, pad = self.ss, 4
        l, t, r, b = font.getbbox(text, anchor="ls", stroke_width=stroke)
        tmp = Image.new("RGBA", (int(r - l) + pad * 2, int(b - t) + pad * 2), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text(
            (pad - l, pad - t), text, font=font, fill=fill, anchor="ls",
            stroke_width=stroke, stroke_fill=fill,
        )
        if squeeze != 1.0:
            tmp = tmp.resize((max(int(tmp.width * squeeze), 1), tmp.height), Image.Resampling.LANCZOS)

        ink_left = pad * squeeze
        ink_w = (r - l) * squeeze
        px = x * ss - ink_left if align == "left" else x * ss - (ink_left + ink_w)
        py = baseline * ss - (pad - t)
        canvas.alpha_composite(tmp, (int(round(px)), int(round(py))))

    def _layout_title(self, title: str):
        """Fits the title into <=2 lines. Returns (size, [lines])."""
        max_w = self.title_right - self.title_left
        words = title.split()
        for size in range(60, 33, -2):
            font = self._font(self.title_font_path, size)
            if self._text_w(title, font, self.title_squeeze) <= max_w:
                return size, [title]
            # greedy wrap into two lines
            lines, cur = [], ""
            for w in words:
                trial = f"{cur} {w}".strip()
                if self._text_w(trial, font, self.title_squeeze) <= max_w or not cur:
                    cur = trial
                else:
                    lines.append(cur)
                    cur = w
            lines.append(cur)
            if len(lines) <= 2 and all(
                self._text_w(ln, font, self.title_squeeze) <= max_w for ln in lines
            ):
                return size, lines

        # still too long: hard-trim at the smallest size
        size = 34
        font = self._font(self.title_font_path, size)
        text = title
        while len(text) > 1 and self._text_w(text + "…", font, self.title_squeeze) > max_w:
            text = text[:-1]
        return size, [text.rstrip() + "…"]

    def _trim(self, text, font, squeeze, max_w):
        if self._text_w(text, font, squeeze) <= max_w:
            return text
        while len(text) > 1 and self._text_w(text + "…", font, squeeze) > max_w:
            text = text[:-1]
        return text.rstrip() + "…"

    def info_rows(self, song: Track) -> list[tuple[str, str]]:
        """Right-hand side rows. YouTube only gives us the channel, length and
        views — if a track ever carries `music` / `lyrics` they are shown instead."""
        singer = re.sub(r"\s*-\s*Topic$|VEVO$", "", song.channel_name or "", flags=re.I).strip()
        music, lyrics = getattr(song, "music", None), getattr(song, "lyrics", None)
        if music or lyrics:
            return [("Singer", singer or "Unknown"), ("Music", music or "-"), ("Lyrics", lyrics or "-")]
        return [
            ("Singer", singer or "Unknown"),
            ("Duration", str(song.duration or "-")),
            ("Views", str(song.view_count or "-")),
        ]

    # ---------------- renderer (pure PIL, no network) ----------------

    def render(self, cover: Image.Image, title: str, rows: list[tuple[str, str]]) -> Image.Image:
        ss, W, H = self.ss, self.width, self.height
        cover = self._trim_bars(cover.convert("RGB"))

        # 1) blurred full-bleed background
        bg = self._cover_fit(cover, W * ss, H * ss)
        bg = bg.filter(ImageFilter.GaussianBlur(7 * ss)).convert("RGBA")

        # 2) bottom band + dotted line on its top edge
        d = ImageDraw.Draw(bg)
        d.rectangle((0, self.band_top * ss, W * ss, H * ss), fill=self.band_color + (255,))
        x = 1
        while x < W:
            d.rectangle(
                (x * ss, (self.band_top - 5) * ss, (x + 2) * ss - 1, (self.band_top + 1) * ss),
                fill=(255, 255, 255, 235),
            )
            x += 6

        # 3) square cover in the middle (+ soft shadow)
        side = self.cover_size * ss
        sq = self._cover_fit(cover, side, side).convert("RGBA")
        cx, cy = self.cover_x * ss, self.cover_y * ss
        shadow = Image.new("RGBA", (side + 80 * ss, side + 80 * ss), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rectangle(
            (40 * ss, 44 * ss, 40 * ss + side, 44 * ss + side), fill=(0, 0, 0, 120)
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(14 * ss))
        bg.alpha_composite(shadow, (cx - 40 * ss, cy - 40 * ss))
        bg.alpha_composite(sq, (cx, cy))

        # 4) song name — right-aligned, big, white
        size, lines = self._layout_title(title)
        tfont = self._font(self.title_font_path, size)
        cap = size * 0.71
        pitch = size * 1.02
        block = (len(lines) - 1) * pitch + cap
        first = self.title_center_y - block / 2 + cap
        for i, line in enumerate(lines):
            self._draw_text(
                bg, line, tfont, (255, 255, 255, 255),
                self.title_right, first + i * pitch,
                squeeze=self.title_squeeze, align="right",
                stroke=self.ss if self.title_squeeze != 1.0 else 0,  # bolder look
            )

        # 5) SINGER / ... rows on the right
        lfont = self._font(self.label_font_path, 16)
        vfont = self._font(self.value_font_path, 22)
        max_w = self.info_right - self.info_x
        for i, (label, value) in enumerate(rows[:3]):
            dy = i * 39.2
            self._draw_text(
                bg, label.upper(), lfont, (240, 222, 222, 255),
                self.info_x, 552 + dy,
            )
            self._draw_text(
                bg, self._trim(value.upper(), vfont, self.value_squeeze, max_w),
                vfont, (255, 255, 255, 255), self.info_x, 572 + dy,
                squeeze=self.value_squeeze,
            )

        return bg.convert("RGB").resize((W, H), Image.Resampling.LANCZOS)

    # ---------------- main generator ----------------

    async def generate(self, song: Track) -> str:
        try:
            os.makedirs("cache", exist_ok=True)
            temp = f"cache/raw_{song.id}.jpg"
            # new file name (_label) => thumbnails cached by the OLD design are
            # never reused, no need to clear the cache folder by hand.
            output = f"cache/{song.id}_label.png"

            if os.path.exists(output):
                return output

            await self.save_thumb(temp, song.thumbnail)
            # `with` closes the file handle; leaving it open leaks one fd per thumbnail
            with Image.open(temp) as cover:
                img = self.render(cover, self.clean_title(song.title), self.info_rows(song))
            img.save(output, quality=95)
            logger.info(f"[Thumbnail] label design generated: {output}")

            try:
                os.remove(temp)
            except Exception:
                pass
            return output

        except Exception as e:
            import traceback

            print(f"[Thumbnail Error] {e}")
            traceback.print_exc()
            return config.DEFAULT_THUMB
