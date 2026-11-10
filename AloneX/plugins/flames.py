from pyrogram import filters, enums
from AloneX import pbot as bot
from pyrogram.types import Message


__module__ = "𝐅ʟᴀᴍᴇs🔥"

__help__ = """
❂ *FLAMES Game Module* — Predict relationships in a fun way!  

❂ *Description*:
❂ Do you want to know your playful future with a friend or crush? The FLAMES game predicts the type of relationship between two people in a joyful, childhood-game style. It's perfect for fun chats and teasing friends!  

❂ *Commands*:
/flames
❂ *Example*:
`/flames AloneX & ackerman`
"""

# ------------------- FLAMES LOGIC ------------------- #

def remove_match_char(list1: list, list2: list) -> list:
    for i in range(len(list1)):
        for j in range(len(list2)):
            if list1[i] == list2[j]:
                c = list1[i]
                list1.remove(c)
                list2.remove(c)
                list3 = list1 + ["*"] + list2
                return [list3, True]
    list3 = list1 + ["*"] + list2
    return [list3, False]

def flames(p1: str, p2: str) -> str:
    p1 = p1.lower().replace(" ", "")
    p2 = p2.lower().replace(" ", "")
    p1_list = list(p1)
    p2_list = list(p2)

    proceed = True
    while proceed:
        ret_list = remove_match_char(p1_list, p2_list)
        con_list = ret_list[0]
        proceed = ret_list[1]
        star_index = con_list.index("*")
        p1_list = con_list[:star_index]
        p2_list = con_list[star_index + 1:]

    count = len(p1_list) + len(p2_list)
    result = ["Friends", "Love", "Affection", "Marriage", "Enemy", "Siblings"]

    while len(result) > 1:
        split_index = count % len(result) - 1
        if split_index >= 0:
            right = result[split_index + 1:]
            left = result[:split_index]
            result = right + left
        else:
            result = result[:len(result) - 1]

    return p1.title(), p2.title(), result[0]

# ------------------- COMMAND HANDLER ------------------- #

@bot.on_message(filters.command("flames") & ~filters.forwarded, group=-123)
async def flames_handler(bot, message: Message):
    usage = "<b>Usage:</b> <code>/flames person1 & person2</code>"
    
    if len(message.command) < 2 or '&' not in message.text:
        return await message.reply_text(usage, parse_mode=enums.ParseMode.HTML)

    try:
        _, rest = message.text.split(maxsplit=1)
        person1, person2 = rest.split('&')
    except Exception:
        return await message.reply_text(usage, parse_mode=enums.ParseMode.HTML)

    p1, p2, prediction = flames(person1.strip(), person2.strip())
    info = "FLAMES is a childhood game that predicts your relationship status based on name letters."

    await message.reply_text(
        f"💜 <b>{p1}</b> and ❤️ <b>{p2}</b> flames is: <b>{prediction}</b> ✨\n\n<code>{info}</code>",
        parse_mode=enums.ParseMode.HTML
    )
