import pyrogram
from pyrogram.types import InlineKeyboardButton as IKB
from pyrogram.types import InlineKeyboardMarkup as IKM
from pyrogram.enums import ButtonStyle
from AloneX import pbot as app, font
from pyrogram import filters
from pyrogram.types import Message
from uuid import uuid4
import asyncio

@app.on_message(filters.command(["stickerinfo", "stinfo"]), group=-876)
async def give_st_info(c: app, m: Message):
    if not m.reply_to_message:
        await m.reply_text(font("Reply to a sticker"))
        return
    elif not m.reply_to_message.sticker:
        await m.reply_text(font("Reply to a sticker"))
        return
    st_in = m.reply_to_message.sticker
    st_type = "Normal"
    if st_in.is_animated:
        st_type = "Animated"
    elif st_in.is_video:
        st_type = "Video"
    st_to_gib = f"""[Sticker]({m.reply_to_message.link}) info:
❂ 𝗙𝗜𝗟𝗘 𝗜𝗗 : `{st_in.file_id}`
❂ 𝗙𝗜𝗟𝗘 𝗡𝗔𝗠𝗘 : {st_in.file_name}
❂ 𝗙𝗜𝗟𝗘 𝗨𝗡𝗜𝗤𝗨𝗘 𝗜𝗗 : `{st_in.file_unique_id}`
❂ 𝗗𝗔𝗧𝗘 𝗔𝗡𝗗 𝗧𝗜𝗠𝗘 𝗢𝗙 𝗦𝗧𝗜𝗖𝗞𝗘𝗥 𝗖𝗥𝗘𝗔𝗧𝗘𝗗 : `{st_in.date}`
❂ 𝗦𝗧𝗜𝗖𝗞𝗘𝗥 𝗧𝗬𝗣𝗘 : `{st_type}`
❂ 𝗘𝗠𝗢𝗝𝗜 : {st_in.emoji}
❂ 𝗣𝗔𝗖𝗞 𝗡𝗔𝗠𝗘 : {st_in.set_name}
"""
    kb = IKM(
        [
            [
                IKB(
                    "➕ 𝗔𝗱𝗱 𝘀𝘁𝗶𝗰𝗸𝗲𝗿 𝗽𝗮𝗰𝗸",
                    url=f"https://t.me/addstickers/{st_in.set_name}",
                    style=ButtonStyle.SUCCESS,
                )
            ]
        ]
    )
    await m.reply_text(st_to_gib, reply_markup=kb)
    return

@app.on_message(filters.command("pkang"), group=-654)
async def _packkang(client, message):
    """
    Kang entire sticker pack using batch processing strategy
    Creates pack in chunks to avoid timeout while maximizing speed
    """
    txt = await message.reply_text(font("Processing...."))
    
    if not message.reply_to_message:
        await txt.edit("Reply to a sticker from the pack you want to kang")
        return
    
    if not message.reply_to_message.sticker:
        await txt.edit("Reply to a sticker")
        return
    if len(message.command) < 2:
        pack_name = f"{message.from_user.first_name}'s Pack"
    else:
        pack_name = message.text.split(maxsplit=1)[1]
    short_name = message.reply_to_message.sticker.set_name
    
    if not short_name:
        return await txt.edit("This sticker is not from any pack!")
    
    try:
        stickers = await client.invoke(
            pyrogram.raw.functions.messages.GetStickerSet(
                stickerset=pyrogram.raw.types.InputStickerSetShortName(
                    short_name=short_name
                ),
                hash=0,
            )
        )
        is_animated = message.reply_to_message.sticker.is_animated
        is_video = message.reply_to_message.sticker.is_video
        
        sticker_type = "Normal"
        if is_animated:
            sticker_type = "Animated (TGS)"
        elif is_video:
            sticker_type = "Video (WEBM)"
        
        shits = stickers.documents
        total_stickers = len(shits)
        
        await txt.edit(
            f"📦 **Pack Found!**\n\n"
            f"**Type:** {sticker_type}\n"
            f"**Total Stickers:** {total_stickers}\n\n"
            f"⏳ Preparing batch kang..."
        )
        sticks = []
        
        for i in shits:
            try:
                file_ref = b""
                if hasattr(i, 'thumbs') and i.thumbs:
                    file_ref = i.thumbs[0].bytes
                
                sex = pyrogram.raw.types.InputDocument(
                    id=i.id, 
                    access_hash=i.access_hash, 
                    file_reference=file_ref
                )
                emoji = "🙂"
                for attr in i.attributes:
                    if isinstance(attr, pyrogram.raw.types.DocumentAttributeSticker):
                        emoji = attr.alt if attr.alt else "🙂"
                        break
                
                sticks.append(
                    pyrogram.raw.types.InputStickerSetItem(
                        document=sex, 
                        emoji=emoji
                    )
                )
            except Exception:
                continue
        
        if not sticks:
            return await txt.edit("❌ No valid stickers found in pack!")
        short_name_new = f'pack_{str(uuid4()).replace("-","")}_by_{client.me.username}'
        user_id = await client.resolve_peer(message.from_user.id)
        INITIAL_BATCH = 30
        ADD_BATCH_SIZE = 20
        BATCH_DELAY = 2
        initial_stickers = sticks[:INITIAL_BATCH]
        remaining_stickers = sticks[INITIAL_BATCH:]
        
        await txt.edit(
            f"📦 Creating pack with first {len(initial_stickers)} stickers...\n"
            f"⏳ Step 1 of {1 + (len(remaining_stickers) + ADD_BATCH_SIZE - 1) // ADD_BATCH_SIZE}"
        )
        max_retries = 3
        for attempt in range(max_retries):
            try:
                create_params = {
                    "user_id": user_id,
                    "title": pack_name,
                    "short_name": short_name_new,
                    "stickers": initial_stickers,
                }
                
                if is_video:
                    create_params["videos"] = True
                
                await client.invoke(
                    pyrogram.raw.functions.stickers.CreateStickerSet(**create_params)
                )
                break
                
            except Exception as e:
                if "TIMEOUT" in str(e) or "INTERDC" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = 3 ** attempt  # 3s, 9s, 27s
                        await txt.edit(
                            f"⚠️ Server timeout (attempt {attempt + 1}/{max_retries})\n"
                            f"⏳ Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        raise
                else:
                    raise
        
        added = len(initial_stickers)
        if remaining_stickers:
            total_batches = (len(remaining_stickers) + ADD_BATCH_SIZE - 1) // ADD_BATCH_SIZE
            
            for batch_num in range(total_batches):
                start_idx = batch_num * ADD_BATCH_SIZE
                end_idx = min((batch_num + 1) * ADD_BATCH_SIZE, len(remaining_stickers))
                batch = remaining_stickers[start_idx:end_idx]
                
                await txt.edit(
                    f"📦 Adding batch {batch_num + 1}/{total_batches}\n"
                    f"✅ Added: {added}/{total_stickers}\n"
                    f"⏳ Processing..."
                )
                
                # Add batch of stickers
                failed_in_batch = 0
                for sticker in batch:
                    for attempt in range(2): 
                        try:
                            await client.invoke(
                                pyrogram.raw.functions.stickers.AddStickerToSet(
                                    stickerset=pyrogram.raw.types.InputStickerSetShortName(
                                        short_name=short_name_new
                                    ),
                                    sticker=sticker
                                )
                            )
                            added += 1
                            await asyncio.sleep(0.3)
                            break
                            
                        except pyrogram.errors.exceptions.flood_420.FloodWait as e:
                            await txt.edit(
                                f"⚠️ Rate limit!\n"
                                f"⏳ Waiting {e.value}s...\n"
                                f"Progress: {added}/{total_stickers}"
                            )
                            await asyncio.sleep(e.value)
                            
                        except Exception:
                            if attempt == 1:
                                failed_in_batch += 1
                            await asyncio.sleep(0.5)
                
                
                if batch_num < total_batches - 1:
                    await txt.edit(
                        f"✅ Batch {batch_num + 1} complete!\n"
                        f"📊 Progress: {added}/{total_stickers}\n"
                        f"⏳ Cooling down {BATCH_DELAY}s..."
                    )
                    await asyncio.sleep(BATCH_DELAY)
        
        
        success_rate = (added / total_stickers) * 100
        await txt.edit(
            f"""✅ **Pack Kanged Successfully!**

📦 **Type:** {sticker_type}
🎨 **Added:** {added}/{total_stickers} ({success_rate:.1f}%)
📝 **Pack Name:** {pack_name}

**Note:** Remove & re-add pack for instant update""",
            reply_markup=IKM(
                [
                    [
                        IKB(
                            "📦 View Pack", 
                            url=f"http://t.me/addstickers/{short_name_new}",
                            style=ButtonStyle.SUCCESS,
                        )
                    ]
                ]
            ),
        )
        
    except pyrogram.errors.exceptions.bad_request_400.StickersetInvalid:
        await txt.edit("❌ Invalid sticker set!")
    except pyrogram.errors.exceptions.bad_request_400.PeerIdInvalid:
        await txt.edit("❌ Invalid user ID!")
    except pyrogram.errors.exceptions.bad_request_400.ShortnameOccupyFailed:
        await txt.edit("❌ Failed to create pack. Please try again!")
    except Exception as e:
        error_msg = str(e)
        if "TIMEOUT" in error_msg or "INTERDC" in error_msg:
            await txt.edit(
                "❌ **Telegram Server Error**\n\n"
                "Server overloaded. Try again in a few minutes."
            )
        else:
            await txt.edit(f"❌ Error: `{error_msg}`")
