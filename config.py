# =====================================================================================
#  SHONA ROBOT  -  ONE CONFIG FOR EVERYTHING  (Robot + Music)
#
#  1. HELPERS
#  2. CORE            shared by Robot and Music (token, database, api, log group)
#  3. OWNER & SUDO    shared by Robot and Music
#  4. ROBOT           manage bot settings
#  5. MUSIC           music system settings  (class MusicConfig, used by AloneX/music)
#
#  Everything is read from environment variables / .env, nothing else to edit.
#  Music reuses the CORE values, so you never configure anything twice.
# =====================================================================================
import os
import re
from os import getenv

from dotenv import load_dotenv

load_dotenv()


# =====================================================================================
#  1. HELPERS
# =====================================================================================
def _bool(name: str, default: str = "False") -> bool:
    return getenv(name, default).strip().lower() in ("true", "1", "yes")


def _int(value, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _first(*names: str, default=None):
    """First non-empty environment variable among `names`."""
    for name in names:
        value = getenv(name)
        if value not in (None, ""):
            return value
    return default


def _ids(name: str, default: str) -> list:
    """'1 2 3' -> [1, 2, 3]"""
    return [int(x) for x in getenv(name, default).split() if x.isdigit()]


def _url(value: str) -> str:
    """'@name' / 'name' / full link -> always a https://t.me/ link."""
    value = (value or "").strip()
    if value.startswith("http"):
        return value
    return "https://t.me/" + value.lstrip("@")


_TG_NAME = re.compile(r"^@?[A-Za-z][A-Za-z0-9_]{3,31}$")


def _tg(name: str, default: str) -> str:
    """Telegram username or link from env. A wrong value (spaces, placeholder text, empty)
    would make Telegram reject the start buttons with BUTTON_URL_INVALID, so fall back."""
    raw = (getenv(name) or "").strip()
    if not raw:
        return default
    if raw.startswith("t.me/"):
        raw = "https://" + raw
    if raw.startswith(("http://", "https://")) and " " not in raw:
        return raw
    if _TG_NAME.match(raw):
        return raw
    print(f"⚠️ {name}={raw!r} is not a valid Telegram username/link -> using default {default!r}")
    return default


# =====================================================================================
#  2. CORE  (shared by Robot + Music)
# =====================================================================================
TOKEN: str = getenv("TOKEN")
DB_URL: str = getenv("DB_URL")
DB_URL2: str = getenv("DB_URL2")

if not TOKEN or not DB_URL:
    print("❌ ERROR: 'TOKEN' and 'DB_URL' environment variables are required.")
    exit(1)

BOT_ID: int = int(TOKEN.split(":")[0])
API_ID: int = int(getenv("API_ID", "0"))
API_HASH: str = getenv("API_HASH")

BOT_USERNAME = "@" + _tg("BOT_USERNAME", "@shonaxrobot").lstrip("@")
BOT_NAME = getenv("BOT_NAME", "Eiko")

# Chat id of the group where the bot logs its activity (starts with -100).
# The bot must be admin there; the music assistant account must be able to post there too.
LOG_GROUP_ID = int(getenv("LOG_GROUP_ID", "0"))
LOGGER_ID = int(getenv("LOGGER_ID", "0"))

_logs_channel = getenv("LOGS_CHANNEL") or getenv("LOG_GROUP_ID") or getenv("LOGGER_ID")
if _logs_channel:
    try:
        LOGS_CHANNEL = int(_logs_channel)
    except ValueError:
        LOGS_CHANNEL = _logs_channel
else:
    LOGS_CHANNEL = None

# Robot's own user account (Pyrogram string session). NOT the music assistant - music uses SESSION1/2/3.
USER_STRING = getenv("USER_STRING")


# =====================================================================================
#  3. OWNER & SUDO  (shared by Robot + Music)
# =====================================================================================
# Get this value from @MissRose_Bot on Telegram by /id
ALONE_OWNER_ID = int(getenv("ALONE_OWNER_ID", "0"))
OWNER_ID = int(getenv("OWNER_ID", "8213572855"))

SUDO_USERS = _ids("SUDO_USERS", "8213572855")
SUPPORT_USERS = _ids("SUPPORT_USERS", "8213572855")
WHITELIST_USERS = _ids("WHITELIST_USERS", "8213572855")
DEV_LIST = _ids("DEV_LIST", "8213572855")

SPAM_USERS = {}

PREMIUM_USERS = []
PREMIUM_USERS.extend(DEV_LIST)


# =====================================================================================
#  4. ROBOT  (manage bot)
# =====================================================================================
prefix_cmds = ['!', '?', '$', '/', '\\', '.', '*', '-', '&', '#', ',']
PREFIX = getenv("PREFIX", "True").lower() == "true"

# ---- stream ----
MULTI_CLIENT: bool = getenv("MULTI_CLIENT", "False").lower() == "true"
multi_clients, work_loads = {}, {}
STREAM_MOD = getenv("STREAM_MOD", "False").lower() == "true"

# ---- third party api keys ----
ELEVENLABS_API_KEY = getenv("ELEVENLABS_API_KEY", "sk_20448f3aced7edc0c3ee743d0115c6a682170bc2ba97f5f3")
IMAGE_UPLOAD_KEY = getenv("IMAGE_UPLOAD_KEY", "c4ca3530479b76ed2b5b10ac82a719c4")
GROQ_API_KEY = getenv("GROQ_API_KEY", "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")
GEMINI_API_KEY = getenv("GEMINI_API_KEY", "AQ.Ab8RN6IvlG0ZWQ0aPqhqq5XXUZv8WNDJneEBPvd1IxNi3y8Akg")
MONSTER_API_KEY = getenv("MONSTER_API_KEY", "0")
# Cloudflare Workers AI (free 10,000 neurons / day): used by the anti-NSFW cloud check and by /draw
CF_ACCOUNT_ID = getenv("CF_ACCOUNT_ID", "304dae051d26f169f1438f0142e19c95")
CF_API_TOKEN = getenv("CF_API_TOKEN", "cfat_uS7tNEX6pqIiKXY8ZOAz62LGCTbpvmZXfQLrqu3S8313ffce")
REPLICATE_API_TOKEN = getenv("REPLICATE_API_TOKEN", "r8_Wis2Jd4QIKQQPfwtLIjNbOyJqBaeow60fvaoo")
GIST_TOKEN = getenv("GIST_TOKEN")

# ---- anti-nsfw ----
# True  (default) = EVERY image / video frame is also checked by the cloud model (Cloudflare Workers AI). Strictest: catches
#                   kissing, bra / panty, lewd anime ... but uses more API calls (Cloudflare neurons).
# False           = the cloud model is asked only when the local NudeNet detector is unsure (saves API calls,
#                   but kissing / underwear pictures are NOT caught).
# Can also be set from Heroku Config Vars: NSFW_CLOUD_ALL = False
NSFW_CLOUD_ALL: bool = _bool("NSFW_CLOUD_ALL", "True")

# ---- support links ----
SUPPORT_GROUP = _tg("SUPPORT_GROUP", "https://t.me/shona_bots")
SUPPORT_CHAT = _tg("SUPPORT_CHAT", "shona_support")
UPDATE_CHANNEL = _tg("UPDATE_CHANNEL", "shona_bots")

# ---- web server / keep alive (Heroku) ----
IS_WEB_SUP = getenv("IS_WEB_SUP", "True").lower() == "true"
WEB_URL = getenv("WEB_URL", "https://t.me/shona_bots")
KEEP_ALIVE = getenv("KEEP_ALIVE", "True").lower() == "true"
PORT = int(os.environ.get("PORT", 8080))
BIND_ADDRESS = str(os.environ.get("WEB_SERVER_BIND_ADDRESS", "0.0.0.0"))
WEB_SLEEP = int(getenv("WEB_SLEEP", "240"))

# ---- pagination & misc ----
AUTO_DEL = int(getenv("AUTO_DEL", "10"))
BTN_COLUMNS = int(getenv("BTN_COLUMNS", "2"))
BTN_ROWS = int(getenv("BTN_ROWS", "6"))

# ---- media ----
# Robot start screen: PM_START_IMG = /start in private, START_IMG = /start in groups.
# Music has no start image of its own (its panel opens from the Robot start menu).
PM_START_IMG = getenv("PM_START_IMG", "https://tmpfiles.org/w9wkpElfIw5N/video_2026-09-26_10-47-38.mp4")
START_IMG = getenv("START_IMG", "https://tmpfiles.org/w9wkpElfIw5N/video_2026-09-26_10-47-38.mp4")
HELP_CMD_IMG = getenv("HELP_CMD_IMG", "https://litter.catbox.moe/p6c5zt.jpg")
HELP_MODULE_IMG = getenv("HELP_MODULE_IMG", "https://litter.catbox.moe/p6c5zt.jpg")
FORCE_JOIN_IMG = getenv("FORCE_JOIN_IMG", "https://litter.catbox.moe/p6c5zt.jpg")

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


# ---- autofilter & file store ----
AF_USERS = []
AF_USERS.extend(DEV_LIST)  # load devs

AF_FILE_DEL_TIME = int(getenv("AF_FILE_DEL_TIME", str(30 * 60)))
AF_SUB_CHAT = getenv("AF_SUB_CHAT", "@shona_bots")
FILE_DB_CHANNEL = int(getenv("FILE_DB_CHANNEL", "0"))  # file store channel
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


# =====================================================================================
#  5. MUSIC  (used by AloneX/music  ->  `from config import MusicConfig`)
#     Reuses everything from CORE / OWNER above, so only music-only options live here.
# =====================================================================================
class MusicConfig:
    def __init__(self):
        # ---- shared with the Robot (see CORE) ----
        self.API_ID = API_ID
        self.API_HASH = API_HASH
        self.BOT_TOKEN = TOKEN
        self.OWNER_ID = ALONE_OWNER_ID or OWNER_ID
        # music keeps its own database ("Anon") on the same cluster, so nothing clashes
        self.MONGO_URL = _first("MUSIC_MONGO_URL") or DB_URL
        self.LOGGER_ID = _int(_first("MUSIC_LOGGER_ID")) or LOG_GROUP_ID or LOGGER_ID

        # ---- music assistant accounts (Pyrogram string sessions) ----
        # SESSION1 is required for music, SESSION2 / SESSION3 are optional extra assistants.
        self.SESSION1 = _first("SESSION1", "SESSION")
        self.SESSION2 = _first("SESSION2")
        self.SESSION3 = _first("SESSION3")

        # ---- links ----
        self.SUPPORT_CHANNEL = _url(UPDATE_CHANNEL)
        self.SUPPORT_CHAT = _url(SUPPORT_CHAT)
        self.OWNER_USERNAME = _url(getenv("OWNER_USERNAME", "https://t.me/thecderqueen"))
        self.DEFAULT_THUMB = getenv("DEFAULT_THUMB", "https://te.legra.ph/file/3e40a408286d4eda24191.jpg")
        self.PING_IMG = getenv("PING_IMG", "https://files.catbox.moe/haagg2.png")

        # ---- behaviour ----
        self.AUTO_END = _bool("AUTO_END", "False")
        self.AUTO_LEAVE = _bool("AUTO_LEAVE", "True")
        self.VIDEO_PLAY = _bool("VIDEO_PLAY", "True")
        self.QUEUE_LIMIT = int(getenv("QUEUE_LIMIT", "2000"))
        self.DURATION_LIMIT = int(getenv("DURATION_LIMIT", "17000"))
        self.PLAYLIST_LIMIT = int(getenv("PLAYLIST_LIMIT", "2000"))

        # ---- stream quality ----
        self.AUDIO_QUALITY = getenv("AUDIO_QUALITY", "HIGH")      # HIGH / STUDIO
        self.VIDEO_QUALITY = getenv("VIDEO_QUALITY", "HD_720p")   # SD_480p / HD_720p / FHD_1080p
        # True: /vplay downloads the video first (smooth). False: stream directly (fast join).
        self.VIDEO_DOWNLOAD = _bool("VIDEO_DOWNLOAD", "True")

        # ---- API (single API: search, /play, /vplay, all platforms) ----
        # Key: https://yt.riteshyt.in/dashboard  (ya Telegram bot par /generate)
        self.RITESH_API_URL = getenv("RITESH_API_URL", "https://api.riteshyt.in")
        self.RITESH_API_KEY = getenv("RITESH_API_KEY", "riteshfreeb4b51bb4314b87718b7d97dd")
        # Purana Fallen client (core/_api.py) ab use nahi hota; defaults khali hain
        self.API_URL = getenv("API_URL", "")
        self.API_KEY = getenv("API_KEY", "")

    def missing(self) -> list:
        """Names of required music settings that are not configured."""
        required = ["API_ID", "API_HASH", "BOT_TOKEN", "MONGO_URL", "LOGGER_ID", "OWNER_ID", "SESSION1"]
        return [name for name in required if not getattr(self, name)]

    def check(self):
        missing = self.missing()
        if missing:
            raise SystemExit(f"Music: missing required environment variables: {', '.join(missing)}")


# =====================================================================================
#  help modules registry (filled at runtime by the plugins)
# =====================================================================================
MODULE = {}  # all loaded help commands
          
