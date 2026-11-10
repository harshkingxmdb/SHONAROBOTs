from AloneX import font

from img2pdf import get_fixed_dpi_layout_fun, convert

from AloneX.helpers.decorator import Command
from telegram import constants

user_temp = {}
    

__module__ = "𝐏ᴅғ〽️"


__help__ = '''
**Commands**:
/img2pdf, /getimg2pdf


❂ /img2pdf: Add images to the conversion queue
❂ /getimg2pdf: Convert queued images to a PDF file
```

Usage:-
1. Use /img2pdf to add multiple images
2. Use /getimg2pdf to generate the PDF

Note:-
After generating the PDF, the image queue will be cleared automatically.

Example:-
1. Send an image
2. Reply to the image with `/img2pdf`
3. Repeat steps 1-2 for all images you want to include
4. Use `/getimg2pdf` to receive your PDF
'''



@Command('getimg2pdf')
async def img2pdf(update, context):
    m = message = update.effective_message
    reply = message.reply_to_message
    user = update.effective_user
  
    if not user.id in user_temp:
        return await message.reply_text(
            "🙋 It seems you haven't added any images to convert pdf please use /img2pdf for add images."
        )
    images = user_temp[user.id].get('images', [])
  
    if not images:
       return await m.reply_text(font("🤔 No images found in data."))
      
    dpix = dpiy = 300
    layout_fun = get_fixed_dpi_layout_fun((dpix, dpiy))
    file_path = f"user_{user.first_name}.pdf"
  
    try:
      
      with open(file_path,"wb") as f:
          f.write(convert(images, layout_fun=layout_fun))
      if (await m.reply_document(file_path, caption=f"*By {context.bot.username} ⚡*", parse_mode=constants.ParseMode.MARKDOWN)):
           user_temp[user.id]['images'].clear()
      
    except Exception as e:
        return await message.reply_text(f"❌ Error: {str(e)}")
      
@Command('img2pdf')
async def img2pdf(update, context):
    m = message = update.effective_message
    reply = message.reply_to_message
    user = update.effective_user
    if not reply or not (reply and reply.photo):
        return await message.reply_text(font("Reply to a photo for convert to pdf."))
    if not user.id in user_temp:
           user_temp.setdefault(user.id, {'images': []})
           photo_id = reply.photo[-1].file_id
           file = await (await context.bot.get_file(photo_id)).download_to_drive()
           user_temp[user.id]['images'].append(file)
           images = user_temp[user.id].get('images', [])
           await message.reply_text(
               f"⚡ Successfully image {len(images)} added to convert but if you want to add multiply images please continue to use /img2pdf to add more. and after all done, use /getimg2pdf to get the pdf file."
           )
    else:
        photo_id = reply.photo[-1].file_id
        file = await (await context.bot.get_file(photo_id)).download_to_drive()
        user_temp[user.id]['images'].append(file)
        images = user_temp[user.id]['images']
        await message.reply_text(
               f"⚡ Successfully image {len(images)} added to convert but if you want to add multiple images please continue to use /img2pdf to add more. and after all done use /getimg2pdf to send the file"
           )
    
    
