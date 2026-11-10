import aiohttp
import random

from pyrogram import filters, enums
from AloneX import pbot, font
from AloneX.helpers.utils import get_as_document

# cmd: [model, model name]
AI_DATA = {
    'openai': ['openai', 'OpenAI GPT-4o-mini'],
    'openail': ['openai-large', 'OpenAI GPT-4o'],
    'openair': ['openai-reasoning', 'OpenAI o1-mini'],
    'qwencoderai': ['qwen-coder', 'Qwen 2.5 Coder 32B'],
    'llamai': ['llama', 'Llama 3.3 70B'],
    'mistralai': ['mistral', 'Mistral Nemo'],
    'unityai': ['unity', 'Unity with Mistral Large by Unity AI Lab'],
    'mjai': ['midijourney', 'Midijourney musical transformer'],
    'rtistai': ['rtist', 'Rtist image generator'],
    'searchgpt': ['searchgpt', 'SearchGPT with realtime news and web search'],
    'evilai': ['evil', 'Evil Mode - Experimental'],
    'deepseek': ['deepseek', 'DeepSeek-V3'],
    'claude': ['claude-hybridspace', 'Claude Hybridspace'],
    'deepseekr1': ['deepseek-r1', 'DeepSeek-R1 Distill Qwen 32B'],
    'deepseekr': ['deepseek-reasoner', 'DeepSeek R1 - Full'],
    'llai': ['llamalight', 'Llama 3.1 8B Instruct'],
    'lgai': ['llamaguard', 'Llamaguard 7B AWQ'],
    'gfai': ['gemini', 'Gemini 2.0 Flash'],
    'gtai': ['gemini-thinking', 'Gemini 2.0 Flash Thinking'],
    'hormozai': ['hormoz', 'Hormoz 8b by Muhammadreza Haghiri'],
    'htai': ['hypnosis-tracy', 'Hypnosis Tracy - Your Self-Help AI'],
    'surai': ['sur', 'Sur AI Assistant'],
    'smai': ['sur-mistral', 'Sur AI Assistant (Mistral)'],
    'lsai': ['llama-scaleway', 'Llama (Scaleway)']
}


CMDS = list(AI_DATA.keys())


__module__ = "𝐀ɪ-(𝐓ᴇxᴛ)🤖"

__help__ = """
*AI Commands*:
https://graph.org/DEPSTEY-07-23

*Description:*  
Interact with various AI models for text-based responses. Generate answers, summaries, or creative text with ease.

*Note:*  
❗ Compatibility with all models is not guaranteed.  
❗ Report any issues to the /support team.
"""



SYSTEM_PROMPT = """
Only USE Telegram HTML [parseMode] for formatting content. Example:
<b>text</b> for bold  
<u>text</u> for underline  
<i>text</i> for italic  
<blockquote>text</blockquote> for quote  
<blockquote expandable>text</blockquote> for long quote  
<pre language='python'>code</pre> for Python (change the language if needed)  
<code>text</code> for monospace  
<spoiler>spoiler</spoiler> for magic phrases  
<s>strike</s> for strikethrough  
"""

# Dictionary to track processing users
process = {}

@pbot.on_message(filters.command(CMDS) & ~filters.forwarded)
async def AI_models(_, message):
    m = message
    user = m.from_user
    user_id = user.id
    command = m.text.split()[0][1:].lower()

    if process.get(user_id):
        return await m.reply_text(font("❌ <b>Processing another request!</b> Please wait for it to complete."))

    if len(m.text.split()) == 1:
        return await m.reply_text(f'❌ <b>Wrong usage!</b> Example: <code>/{command} hello</code>')

    ai_data = AI_DATA.get(command)
    if not ai_data:
        return await m.reply_text(f'❌ <b>Invalid model!</b> Available models: <code>{", ".join(CMDS)}</code>')

    model, model_name = ai_data
    msg = await m.reply(f'🔁 <b>{model_name} processing...</b>')

    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": m.text.split(maxsplit=1)[1]}
        ],
        "model": model,
        "seed": random.randint(10, 90),
        "jsonMode": False,
        "private": True
    }

    # Mark user as processing
    process[user_id] = True

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post('https://text.pollinations.ai/', json=payload, timeout=30) as response:
                response.raise_for_status()
                response_text = await response.text()

                if len(response_text) >= 4000:
                    document = get_as_document(response_text)
                    await m.reply_document(document, caption=f"By @{_.me.username}")
                else:
                    await msg.edit(response_text)

    except aiohttp.ClientError as e:
        await msg.edit(f'❌ <b>Request failed!</b>')
    except asyncio.TimeoutError:
        await msg.edit('❌ <b>Request timed out!</b> Please try again.')
    except Exception as e:
        await msg.edit(f'❌ <b>ERROR</b>')
    finally:
        # Remove user from processing list
        process.pop(user_id, None)
