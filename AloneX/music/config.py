# SHONA-CODER
# Music config. Reads the SAME .env as the manage bot, so no duplicate setup is needed.
# Every value can still be overridden with its own music-specific variable.
from os import getenv

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: str) -> bool:
    return getenv(name, default).lower() in ("true", "1", "yes")


def _first(*names: str, default=None):
    """Return the first non-empty env var among `names`."""
    for name in names:
        value = getenv(name)
        if value not in (None, ""):
            return value
    return default


def _int(value, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _url(value: str) -> str:
    """Accept '@name', 'name' or a full link and always return a t.me link."""
    value = (value or "").strip()
    if value.startswith("http"):
        return value
    return "https://t.me/" + value.lstrip("@")


class Config:
    def __init__(self):
        # ---- Telegram (shared with the manage bot's .env) ----
        self.API_ID = _int(_first("API_ID"))
        self.API_HASH = _first("API_HASH")
        self.BOT_TOKEN = _first("BOT_TOKEN", "TOKEN")
        self.MONGO_URL = _first("MUSIC_MONGO_URL", "MONGO_URL", "DB_URL")
        self.LOGGER_ID = _int(_first("MUSIC_LOGGER_ID", "LOGGER_ID", "LOG_GROUP_ID", "LOGS_CHANNEL"))
        self.OWNER_ID = _int(_first("OWNER_ID", "ALONE_OWNER_ID"))

        # ---- Assistant sessions ----
        # SESSION / SESSION2 / SESSION3 (music) or USER_STRING (manage bot's vc player string)
        self.SESSION1 = _first("SESSION", "SESSION1", "USER_STRING")
        self.SESSION2 = _first("SESSION2")
        self.SESSION3 = _first("SESSION3")

        # ---- Links ----
        self.SUPPORT_CHANNEL = _url(_first("SUPPORT_CHANNEL", "UPDATE_CHANNEL", default="https://t.me/Shona_bots"))
        self.SUPPORT_CHAT = _url(_first("SUPPORT_CHAT", default="https://t.me/shona_support"))
        self.OWNER_USERNAME = _url(_first("OWNER_USERNAME", default="https://t.me/thecderqueen"))
        self.DEFAULT_THUMB = getenv("DEFAULT_THUMB", "https://te.legra.ph/file/3e40a408286d4eda24191.jpg")
        self.PING_IMG = getenv("PING_IMG", "https://files.catbox.moe/haagg2.png")
        self.START_IMG = getenv("MUSIC_START_IMG", "https://files.catbox.moe/zvziwk.jpg")

        # ---- Bot behaviour ----
        self.AUTO_END = _bool("AUTO_END", "False")
        self.AUTO_LEAVE = _bool("AUTO_LEAVE", "True")
        self.VIDEO_PLAY = _bool("VIDEO_PLAY", "True")
        self.QUEUE_LIMIT = int(getenv("QUEUE_LIMIT", "2000"))
        self.DURATION_LIMIT = int(getenv("DURATION_LIMIT", "17000"))
        self.PLAYLIST_LIMIT = int(getenv("PLAYLIST_LIMIT", "2000"))

        # ---- Stream quality ----
        self.AUDIO_QUALITY = getenv("AUDIO_QUALITY", "HIGH")      # HIGH / STUDIO
        self.VIDEO_QUALITY = getenv("VIDEO_QUALITY", "HD_720p")   # SD_480p / HD_720p / FHD_1080p
        # True: /vplay video pehle download hoti hai (smooth). False: seedha stream (fast join).
        self.VIDEO_DOWNLOAD = _bool("VIDEO_DOWNLOAD", "True")

        # ---- APIs ----
        # Music (/play): main API pehle, fail/limit khatam hone par Inflex
        self.API_URL = getenv("API_URL", "https://api.onegrab.fun")
        self.API_KEY = getenv("API_KEY", "68027e_n0JU9_N0Y_DlKp_OTFGmVMdtLkb6TPZy")
        self.INFLEX_API_URL = getenv("INFLEX_API_URL", "https://teaminflex.xyz")
        self.INFLEX_API_KEY = getenv("INFLEX_API_KEY", "INFLEX42847728D")
        # Video (/vplay): sirf Shruti API (key: @SHRUTIAPIBOT)
        self.SHRUTI_API_URL = getenv("SHRUTI_API_URL", "https://api.shrutibots.in")
        self.SHRUTI_API_KEY = getenv("SHRUTI_API_KEY", "ShrutiBotspUErr2mxArElKbWI4pVU")

    def missing(self) -> list:
        """Names of required settings that are not configured."""
        required = ["API_ID", "API_HASH", "BOT_TOKEN", "MONGO_URL", "LOGGER_ID", "OWNER_ID", "SESSION1"]
        return [name for name in required if not getattr(self, name)]

    def check(self):
        missing = self.missing()
        if missing:
            raise SystemExit(f"Music: missing required environment variables: {', '.join(missing)}")
