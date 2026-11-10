import os
from os import getenv
from dotenv import load_dotenv

load_dotenv()

prefix_cmds = ['!', '?', '$', '/', '\\', '.', '*', '-','&', '#', ',']


# for stream 
MULTI_CLIENT:bool = getenv('MULTI_CLIENT', 'False').lower() == 'true'
multi_clients, work_loads = {}, {}


# necessary
PREFIX = getenv('PREFIX', 'True').lower() == 'true'
TOKEN: str = getenv('TOKEN')
DB_URL: str = getenv('DB_URL')
DB_URL2: str = getenv('DB_URL2')

if not TOKEN or not DB_URL:
    print("❌ ERROR: 'TOKEN' and 'DB_URL' environment variables are required.")
    exit(1)

BOT_ID: int = int(TOKEN.split(':')[0])
API_ID: int = int(getenv('API_ID', '0'))
API_HASH: str = getenv('API_HASH')
ELEVENLABS_API_KEY = getenv('ELEVENLABS_API_KEY', "sk_b60525985e2cce19eabdc4fec8d28640cfa1229490c4e22c")
IMAGE_UPLOAD_KEY = getenv('IMAGE_UPLOAD_KEY', "d8f59b7c8846df826a9c8428f7a44a0d")

GROQ_API_KEY = getenv('GROQ_API_KEY', "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")
GEMINI_API_KEY = getenv('GEMINI_API_KEY', "AQ.Ab8RN6K2KBi5tOIbrxu2V9HfSyFM4t4obDlSQQr6Nw5My7bWhQ")
MONSTER_API_KEY = getenv('MONSTER_API_KEY', "0")
REPLICATE_API_TOKEN = getenv('REPLICATE_API_TOKEN', "r8_csE10UhwOz72TOQ3x4qFYz8tOVkEOEQ3VQb4Q")

# Get this value from @MissRose_Bot on Telegram by /id
ALONE_OWNER_ID = int(getenv("ALONE_OWNER_ID", "0"))
# Chat id of a group for logging bot's activities
LOG_GROUP_ID = int(getenv("LOG_GROUP_ID", "0"))

SUPPORT_GROUP = getenv("SUPPORT_GROUP", "https://t.me/shona_bots")

START_IMG_URL = getenv("START_IMG_URL", "https://files.catbox.moe/1gxuh7.jpg")


SUPPORT_CHAT = getenv('SUPPORT_CHAT', 'shona_support')
UPDATE_CHANNEL = getenv('UPDATE_CHANNEL', 'shona_bots')

_logs_channel = getenv('LOGS_CHANNEL') or getenv('LOG_GROUP_ID') or getenv('LOGGER_ID')
if _logs_channel:
    try:
        LOGS_CHANNEL = int(_logs_channel)
    except ValueError:
        LOGS_CHANNEL = _logs_channel
else:
    LOGS_CHANNEL = None

LOGGER_ID = int(getenv('LOGGER_ID', '0'))
BOT_USERNAME = getenv('BOT_USERNAME', '@shonaxrobot')
BOT_NAME = getenv('BOT_NAME', 'Eiko')
IS_WEB_SUP = getenv('IS_WEB_SUP', 'True').lower() == 'true'

SUDO_USERS = [int(x) for x in getenv("SUDO_USERS", "8213572855").split() if x.isdigit()]
SUPPORT_USERS = [int(x) for x in getenv("SUPPORT_USERS", "8213572855").split() if x.isdigit()]
WHITELIST_USERS = [int(x) for x in getenv("WHITELIST_USERS", "8213572855").split() if x.isdigit()]
OWNER_ID = int(getenv("OWNER_ID", "8213572855"))
DEV_LIST = [int(x) for x in getenv("DEV_LIST", "8213572855").split() if x.isdigit()]

SPAM_USERS = {}

PREMIUM_USERS = []
PREMIUM_USERS.extend(DEV_LIST)



#vc player
USER_STRING = getenv('USER_STRING')

#gist
GIST_TOKEN = getenv('GIST_TOKEN')





# keep alive ( web support )
WEB_URL = getenv('WEB_URL', "https://t.me/shona_bots")

KEEP_ALIVE = getenv('KEEP_ALIVE', 'True').lower() == 'true'
PORT = int(os.environ.get("PORT", 8080))
BIND_ADDRESS = str(os.environ.get("WEB_SERVER_BIND_ADDRESS", "0.0.0.0"))
WEB_SLEEP = int(getenv('WEB_SLEEP', '240'))

# pagination & stuffs
AUTO_DEL = int(getenv('AUTO_DEL', '10'))
BTN_COLUMNS = int(getenv('BTN_COLUMNS', '2'))
BTN_ROWS = int(getenv('BTN_ROWS', '6'))


# some media source
PM_START_IMG = getenv('PM_START_IMG', "https://tmpfiles.org/w9wkpElfIw5N/video_2026-09-26_10-47-38.mp4")

HELP_CMD_IMG = getenv('HELP_CMD_IMG', "https://litter.catbox.moe/p6c5zt.jpg")


HELP_MODULE_IMG = getenv('HELP_MODULE_IMG', "https://litter.catbox.moe/p6c5zt.jpg")

START_IMG = getenv('START_IMG', "https://tmpfiles.org/w9wkpElfIw5N/video_2026-09-26_10-47-38.mp4")


FORCE_JOIN_IMG = getenv('FORCE_JOIN_IMG', "https://litter.catbox.moe/p6c5zt.jpg")

AF_START_STICKERS = [
  "CAACAgUAAxkBAAEBrV9nWukpft8gmtrZVMkbO4GKlZy0HQACWxUAAnHv2FZkjr7WjG3OjzYE",
  "CAACAgUAAxkBAAEBrVpnWuhM17A8xDlzxO2q5aqSa6xmawACMRMAAlpM2VYGl0Ro6224bjYE",
  "CAACAgUAAxkBAAEBrWJnWulBrVl7pq-QRI1QCaMjd6laLAAC2RYAAojK2Va2m-0pJ2vqLzYE"
]

STICKERS = {
"CAACAgQAAxkBAAECdO1ndW8ICjKDXuzrYsEo5hqQbVw6rAAC7w4AAjULSFDuxCh0capMYDYE",
"CAACAgQAAxkBAAECdPBndW8Sdvfw4Ppj87fy_npiIdJfDwACPBEAAg1eUVAboAI8ZLYkXTYE",
"CAACAgQAAxkBAAECdPNndW8utxbCZtWzQmf5ZsttjCmgjwACfhIAApO7UVDWdRWcykiwuDYE",
"CAACAgQAAxkBAAECdPZndW9Suh_gnSo8lD3WAsbCiISpYAACyA4AAiOqKVKUg3R3m5-gqjYE",
"CAACAgQAAxkBAAECdPlndW9cYXPSw39cyQHvE6nEdNB2JQACCBIAAtn8IFK1g1MaQBON0TYE",
"CAACAgQAAxkBAAECdPxndW9kD86_lqdWJszPI8vYbcyvngAC_REAAo_vSVJCrH8aUlOkyTYE",
"CAACAgQAAxkBAAECdP9ndW-Ia3qf4pXbjWZI8Y0-bz2DogACqBEAAtDXMFItdGU77Edd_TYE",
"CAACAgQAAxkBAAECdQJndW-dkLNejsHkTINe_Qxq3I08EwACITUAApRgTgOL1gVo29ff0TYE",
"CAACAgQAAxkBAAECdQVndW-wKUWRXxpUA4J_kh-PIG_9UwACKzcAApRgTgPiRf7a32h5vTYE",
"CAACAgIAAxkBAAECdQhndW_A211FzHXaW7Aw4RaMJF6tIgACsTEAAi_24UiQKhNSL9u30DYE",
"CAACAgIAAxkBAAECdQtndW_Ij8fMRzlbT3X_TfzVK1T8rAAC0C8AAodj4EjSZ1G3qw6FCDYE",
"CAACAgIAAxkBAAECdQ5ndW_VDdwsZNXZZax-TKaBfewtdQACiUsAArp5-EnWQpanpxF8yTYE",
"CAACAgIAAxkBAAECdRFndW_dd4wVOgwgFEkbi8dAM9XSlgACOEUAAnVA-En_oC_69i7LEzYE",
"CAACAgIAAxkBAAECdRRndW_v2TMrVzit9rYXYqczPlbkCQACsjsAAntc-EmVS7vTfBuJjzYE",
"CAACAgIAAxkBAAECdRdndXAIM_S1ZGNKci1kTAMPyvYNqgACwUoAAv4V8EkLHWsQUvK1gDYE",
"CAACAgIAAxkBAAECdRpndXAVErJDP8CnfHzdO-NswYwhFAACO1YAAkvCKUnA3XYg4FCWlTYE",
"CAACAgIAAxkBAAECdR1ndXAfoKxdgT2fkedoA4fS3m22lgACU1cAAthfKUkuBdehSY_rBzYE",
"CAACAgIAAxkBAAECdSBndXAmzGwiIEAljqKzCQlAY8TLMgACx2MAAuliKUlThRsve-oJyzYE",
"CAACAgUAAxkBAAECdSNndXBJquluZXwU0__JKxmfKMZDEAAChQ8AAqGacVXhgiCsahAGDzYE",
"CAACAgIAAxkBAAECdSZndXBapGEYja7rsroogCRodsny8AACozYAAiQP2EpVNGifwVsKjDYE",
"CAACAgIAAxkBAAECdSlndXBhosJB417LBilVJjF3BZo67AAC9EEAAsku0UqCpzP2ZVFhDTYE",
"CAACAgIAAxkBAAECdSxndXBurDS6bwIK8Qa1oR7veFCbiwACgDwAAjEl0Eomm59IgqSggTYE",
"CAACAgIAAxkBAAECdTJndXB5W3ezZamw35dpDjku80jgGgACGV8AAsU1OUqb69FyFb1c6jYE",
"CAACAgIAAxkBAAECdTVndXCbx0W9t_H2nUrd-Fl3KbUyyQACtj0AAg-5MUgE2eOcan38NjYE",
"CAACAgIAAxkBAAECdThndXClCzM7QcM77Nyuqcl_4dGp1AACPUYAAj1uMUjiLGn4YGxk9jYE",
"CAACAgIAAxkBAAECdT5ndXDVpuuQ8KvuMElfRT8kGOUp4gACHUYAAtMKMEgcf_DY6DSaXDYE",
"CAACAgIAAxkBAAECdURndXDsel2azVwIeyexmf-aMwNBLAAC-h8AAsDtmUlWim3BbUtNfDYE",
"CAACAgIAAxkBAAECdUdndXD4ih8jckxT-Hl3ZwxwxUzX0QACXCAAAhK-mEl6EeOdleoZZjYE",
"CAACAgIAAxkBAAECdUpndXEBmz2IpWxVWkbXz7mgvQlB1AAC-x8AAisNmEla-bbrY-25jTYE",
"CAACAgIAAxkBAAECdU1ndXEfJf6FXFOFL-w32FeXISTBvwAC4GcAAisfOEvOuPgyh_L6izYE",
"CAACAgIAAxkBAAECdVBndXE86_uoi8WCXgJ-1mjFaysxEgACWjYAAu1_-UlGpKXB9t-AwDYE",
"CAACAgIAAxkBAAECdVdndXGp48JGRAOe7zPQoJi5D3VxXQACQTgAApJ5-Emh0g5pFxiGnzYE",
"CAACAgIAAxkBAAECdVpndXGyPJthODJ8NuK6rtD3Vwua6QAC7jQAAkqo-EkdGBrhbITUEDYE",
"CAACAgIAAxkBAAECdV1ndXG_l-bUo46JvIM4Hxj8YEQaOQACtC0AAvs2-UmnONqktEwhTzYE",
"CAACAgIAAxkBAAECdWBndXHG29vG_dZMhvJlK4c07Ss3TQACeS8AAlPL-EkItgVnal3GBjYE",
"CAACAgIAAxkBAAECdV1ndXG_l-bUo46JvIM4Hxj8YEQaOQACtC0AAvs2-UmnONqktEwhTzYE",
"CAACAgIAAxkBAAECdWZndXIBjJ9rDtKutvip87-tAkSQ0QACgi4AAiXucUmJnZzoSNSCvDYE",
"CAACAgIAAxkBAAECdWlndXIQoHORueLutW0sMp7kYgABE1MAAoxHAAIltelK4So4wQ12bcc2BA",
"CAACAgIAAxkBAAECdWxndXIZcekEGymNrjhI5gWIZlOx7QACPkgAAlhi4UrkSTRqKK8iwDYE",
"CAACAgIAAxkBAAECdW9ndXIlwbYgNzDsW41v27Z7yMFf0QACzVEAAj1u4EpQbl_Qdr1NJDYE",
"CAACAgIAAxkBAAECdXJndXJDBU6b5wFDwuGkTAjUynRwiAACkzMAAkvCmUgudR-apFOqGDYE",
"CAACAgIAAxkBAAECdXVndXJIUh28BNFPmzgPXzAN7vtL1AACekYAAkCnmUgiILqmlERFLzYE",
"CAACAgIAAxkBAAECdXhndXJQk7bAMVF9S7x_KV48iYe0cQACzzUAAoavsUhVPK3wUyiO-TYE",
"CAACAgQAAxkBAAECdXtndXJwFKOSFC9ik9hMc9lfRqdqsQACYxYAAvMUAAFSZQEXkaJdECc2BA",
"CAACAgQAAxkBAAECdX5ndXJ6gSGAGc9EThFUPm91mXV5WwACxRUAAlCTCVKxsL-4uYPFCzYE",
"CAACAgQAAxkBAAECdYFndXKA1aRfjr-Yb8IQK8NHaT_FRAAC_BUAAukESFI1AYxe3mz5YTYE",
"CAACAgQAAxkBAAECdYRndXKS3hmAoqlJyk7DSubv58z2DogACqBEAAtDXMFItdGU77Edd_TYE",
"CAACAgQAAxkBAAECdYdndXKYUdgAAdfgZDJWHXVF4MUD6rYAAp8UAALqEQhSLZd3lUNZuvU2BA",
}


AF_PHOTOS = [
'AgACAgUAAxkBAAECo-tnej70ZWYrv0bQPM_XRre1lLK6cwACXsExGx-R2VenYteJPUaIjAEAAwIAA3kAAzYE',
'AgACAgUAAxkBAAECo-1nej706PWzzWvmOLAFagdYeONKvgACYMExGx-R2VfM2MDvp7f_9AEAAwIAA3kAAzYE',
'AgACAgUAAxkBAAECo-xnej70d68zKUx_NBuEz3PMZFa13AACX8ExGx-R2Vdc_HYt-dTN6gEAAwIAA3kAAzYE',
'AgACAgUAAxkBAAECo-5nej70IKBWUFDTjky0eAj6Q6KoMAACYcExGx-R2VcD_ZuS0CkwSAEAAwIAA3kAAzYE',
'AgACAgUAAxkBAAECpCVnekCldWbkBNdrjo6EsmTXJ9SLeQACZsExGx-R2Ve6FxfQ5ov_sAEAAwIAA3kAAzYE'
]






#autofilter & file store
AF_USERS = []
AF_USERS.extend(DEV_LIST) # load devs

STREAM_MOD = getenv('STREAM_MOD', 'False').lower() == 'true'
AF_FILE_DEL_TIME = int(getenv('AF_FILE_DEL_TIME', str(30*60)))
AF_SUB_CHAT = getenv('AF_SUB_CHAT', "@AloneUpdates")
FILE_DB_CHANNEL = int(getenv('FILE_DB_CHANNEL', '0')) # file store channel
AF_SUB_TEXT = getenv('AF_SUB_TEXT', """
<blockquote><b>
To access your files, first click on [📢 Join Our Channel/Group]. Once you've joined, click the [📁 Get File] button to download your files. We're glad to have you with us!

Thank you for being part of our community! 📲 ✨
</b></blockquote>
""")
AF_QS_TEXT = getenv('AF_QS_TEXT', """
🔎 <b>Quick Search</b>:
<blockquote>Select the below buttons to get accurate results for language, media type, etc.</blockquote>
""")


MODULE = {} # all loaded help commands
