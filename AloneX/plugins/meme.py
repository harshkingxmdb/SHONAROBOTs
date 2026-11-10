import os, textwrap, tempfile, cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
from pyrogram import filters
from pyrogram.types import Message
from AloneX import pbot, font
from lottie import importers, exporters
import asyncio
from concurrent.futures import ThreadPoolExecutor


if os.name == "nt":
    DEFAULT_FONT = "arial.ttf"
else:
    DEFAULT_FONT = "AloneX/Extra/default.ttf"

COLOR_MAP = {
    "red": (255, 0, 0), "blue": (0, 128, 255), "green": (0, 163, 27),
    "yellow": (255, 255, 0), "white": (255, 255, 255), "black": (0, 0, 0),
    "pink": (255, 105, 180), "purple": (138, 43, 226), "cyan": (0, 255, 255)
}

def draw_on_frame(pil_img, top_text, bottom_text, color):
    """Draw meme text with classic impact font style (black outline, white/colored fill)"""
    i_width, i_height = pil_img.size
    
    # Font size calculation
    m_font = ImageFont.truetype(DEFAULT_FONT, int((70 / 640) * i_width))
    
    draw = ImageDraw.Draw(pil_img)
    current_h, pad = 10, 5

    # Draw top text with classic meme style
    if top_text:
        for u_text in textwrap.wrap(top_text.upper(), width=15):
            bbox = draw.textbbox((0, 0), u_text, font=m_font)
            u_width = bbox[2] - bbox[0]
            u_height = bbox[3] - bbox[1]

            x_pos = (i_width - u_width) / 2
            y_pos = int((current_h / 640) * i_width)

            # Black outline (4 directions)
            draw.text(xy=(x_pos - 2, y_pos), text=u_text, font=m_font, fill=(0, 0, 0))
            draw.text(xy=(x_pos + 2, y_pos), text=u_text, font=m_font, fill=(0, 0, 0))
            draw.text(xy=(x_pos, y_pos - 2), text=u_text, font=m_font, fill=(0, 0, 0))
            draw.text(xy=(x_pos, y_pos + 2), text=u_text, font=m_font, fill=(0, 0, 0))

            # Main text with color
            draw.text(xy=(x_pos, y_pos), text=u_text, font=m_font, fill=color)

            current_h += u_height + pad

    # Draw bottom text with classic meme style
    if bottom_text:
        for l_text in textwrap.wrap(bottom_text.upper(), width=15):
            bbox = draw.textbbox((0, 0), l_text, font=m_font)
            u_width = bbox[2] - bbox[0]
            u_height = bbox[3] - bbox[1]

            x_pos = (i_width - u_width) / 2
            y_pos = i_height - u_height - int((20 / 640) * i_width)

            # Black outline (4 directions)
            draw.text(xy=(x_pos - 2, y_pos), text=l_text, font=m_font, fill=(0, 0, 0))
            draw.text(xy=(x_pos + 2, y_pos), text=l_text, font=m_font, fill=(0, 0, 0))
            draw.text(xy=(x_pos, y_pos - 2), text=l_text, font=m_font, fill=(0, 0, 0))
            draw.text(xy=(x_pos, y_pos + 2), text=l_text, font=m_font, fill=(0, 0, 0))

            # Main text with color
            draw.text(xy=(x_pos, y_pos), text=l_text, font=m_font, fill=color)

            current_h += u_height + pad

    return pil_img

async def process_static(path, top, bottom, color):
    def process_sync():
        img = Image.open(path).convert("RGB")
        if img.width > 512 or img.height > 512:
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        img = draw_on_frame(img, top, bottom, color)
        out = "meme_sticker.webp"
        img.save(out, "WEBP", quality=85, optimize=False)
        return out
    
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=4) as executor:
        result = await loop.run_in_executor(executor, process_sync)
    return result

async def process_video(path, top, bottom, color):
    def process_sync():
        tmp_out = "temp.mp4"
        final_out = "meme_sticker.webm"

        cap = cv2.VideoCapture(path)
        fps = min(cap.get(cv2.CAP_PROP_FPS) or 25, 10)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w, h = int(cap.get(3)), int(cap.get(4))
        
        target_size = 320
        if w > target_size or h > target_size:
            scale = min(target_size/w, target_size/h)
            w, h = int(w * scale), int(h * scale)
        
        # Ensure dimensions are even numbers
        w = w if w % 2 == 0 else w - 1
        h = h if h % 2 == 0 else h - 1
        
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(tmp_out, fourcc, fps, (w, h))

        frame_count = 0
        skip_frames = max(1, total_frames // 50)
        processed_frames = 0
        
        while True:
            ret, frame = cap.read()
            if not ret: 
                break
                
            frame_count += 1
            if frame_count % skip_frames != 0:
                continue
                
            if frame.shape[1] != w or frame.shape[0] != h:
                frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)
                
            pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            pil_img = draw_on_frame(pil_img, top, bottom, color)
            writer.write(cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR))
            processed_frames += 1

        cap.release()
        writer.release()
        
        if processed_frames == 0:
            if os.path.exists(tmp_out):
                os.remove(tmp_out)
            raise Exception("No frames were processed")
        
        # Better FFmpeg command
        cmd = (
            f"ffmpeg -y -i {tmp_out} "
            f"-c:v libvpx-vp9 "
            f"-pix_fmt yuv420p "
            f"-b:v 400k "
            f"-crf 35 "
            f"-quality realtime "
            f"-speed 8 "
            f"-tile-columns 1 "
            f"-tile-rows 1 "
            f"-frame-parallel 1 "
            f"-threads 4 "
            f"-auto-alt-ref 0 "
            f"-lag-in-frames 0 "
            f"-an "
            f"-vf scale=320:320:force_original_aspect_ratio=decrease "
            f"{final_out} 2>&1"
        )
        
        os.system(cmd)
        
        if os.path.exists(tmp_out):
            os.remove(tmp_out)
        
        if not os.path.exists(final_out) or os.path.getsize(final_out) == 0:
            raise Exception("Failed to create WebM file")
            
        return final_out
    
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=2) as executor:
        result = await loop.run_in_executor(executor, process_sync)
    return result

async def process_tgs(path, top, bottom, color):
    def process_sync():
        with open(path, "rb") as f:
            animation = importers.tgs.import_tgs(f)
        
        temp_dir = tempfile.mkdtemp()
        exporters.png.export_png(animation, temp_dir, "frame")

        frames = []
        frame_files = sorted(os.listdir(temp_dir))
        
        max_frames = min(len(frame_files), 20)
        step = max(1, len(frame_files) // max_frames)
        
        for i in range(0, len(frame_files), step):
            if len(frames) >= max_frames:
                break
            fname = frame_files[i]
            frame_path = os.path.join(temp_dir, fname)
            img = Image.open(frame_path).convert("RGB")
            if img.width > 320 or img.height > 320:
                img.thumbnail((320, 320), Image.Resampling.LANCZOS)
            img = draw_on_frame(img, top, bottom, color)
            frames.append(img)

        tmp_video = "temp_from_tgs.mp4"
        fps = 10
        w, h = frames[0].size
        
        # Ensure even dimensions
        w = w if w % 2 == 0 else w - 1
        h = h if h % 2 == 0 else h - 1
        
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(tmp_video, fourcc, fps, (w, h))
        
        for f in frames:
            resized = f.resize((w, h), Image.Resampling.LANCZOS)
            writer.write(cv2.cvtColor(np.array(resized), cv2.COLOR_RGB2BGR))
        writer.release()

        final_out = "meme_from_tgs.webm"
        cmd = (
            f"ffmpeg -y -i {tmp_video} "
            f"-c:v libvpx-vp9 "
            f"-pix_fmt yuv420p "
            f"-b:v 400k "
            f"-crf 35 "
            f"-quality realtime "
            f"-speed 8 "
            f"-tile-columns 1 "
            f"-tile-rows 1 "
            f"-frame-parallel 1 "
            f"-threads 4 "
            f"-auto-alt-ref 0 "
            f"-lag-in-frames 0 "
            f"-an "
            f"-vf scale=320:320:force_original_aspect_ratio=decrease "
            f"{final_out} 2>&1"
        )
        
        os.system(cmd)
        
        if os.path.exists(tmp_video):
            os.remove(tmp_video)
        for fname in frame_files:
            frame_path = os.path.join(temp_dir, fname)
            if os.path.exists(frame_path):
                os.remove(frame_path)
        os.rmdir(temp_dir)
        
        return final_out
    
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=2) as executor:
        result = await loop.run_in_executor(executor, process_sync)
    return result

@pbot.on_message(filters.command("mmf"))
async def meme_handler(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.media:
        return await message.reply(font("Reply to an image/sticker/gif/video with `/mmf top ; bottom [color]`"))

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply(font("Usage: `/mmf top ; bottom [color]`\n\n**Examples:**\n`/mmf hello ; world`\n`/mmf top text ; bottom text red`"))

    raw_text = args[1].strip()
    parts = raw_text.split()
    color_name = None
    
    if parts and parts[-1].lower() in COLOR_MAP:
        color_name = parts[-1].lower()
        text_part = " ".join(parts[:-1])
    else:
        text_part = raw_text
        color_name = "white"
    
    color = COLOR_MAP[color_name]
    
    if ";" in text_part:
        top_text, bottom_text = text_part.split(";", 1)
        top_text = top_text.strip()
        bottom_text = bottom_text.strip()
    else:
        top_text = text_part.strip()
        bottom_text = ""
    
    if not top_text and not bottom_text:
        return await message.reply(font("Please provide at least top or bottom text!"))

    msg = await message.reply(font("🎨 Processing..."))
    
    try:
        file_path = await client.download_media(message.reply_to_message)
        
        if file_path.endswith((".jpg", ".jpeg", ".png", ".webp")):
            out = await process_static(file_path, top_text, bottom_text, color)
            await message.reply_sticker(out)
            
        elif file_path.endswith((".gif", ".mp4", ".mkv", ".webm", ".avi")):
            out = await process_video(file_path, top_text, bottom_text, color)
            await message.reply_sticker(out)
            
        elif file_path.endswith(".tgs"):
            out = await process_tgs(file_path, top_text, bottom_text, color)
            await message.reply_sticker(out)
        else:
            await msg.edit("❌ Unsupported file type")
            return

        for f in [file_path, out]:
            if os.path.exists(f):
                os.remove(f)
                
    except Exception as e:
        await msg.edit(f"❌ Error: {str(e)}")
        return

    await msg.delete()
