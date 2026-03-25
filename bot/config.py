import os

# Telegram
TG_BOT_TOKEN = os.environ["TG_BOT_TOKEN"]
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
TG_PROXY = os.environ.get("TG_PROXY", "")  # e.g. http://clash:7890

# Radarr
RADARR_URL = os.environ.get("RADARR_URL", "http://radarr:7878")
RADARR_API_KEY = os.environ.get("RADARR_API_KEY", "")

# Sonarr
SONARR_URL = os.environ.get("SONARR_URL", "http://sonarr:8989")
SONARR_API_KEY = os.environ.get("SONARR_API_KEY", "")

# qBittorrent
QBIT_URL = os.environ.get("QBIT_URL", "http://qbit-pt:8092")
QBIT_USER = os.environ.get("QBIT_USER", "admin")
QBIT_PASS = os.environ.get("QBIT_PASS", "")

# M-Team
MT_API_TOKEN = os.environ.get("MT_API_TOKEN", "")
MT_BASE_URL = os.environ.get("MT_BASE_URL", "https://api.m-team.cc")

# Farm
FARM_ENABLED = os.environ.get("FARM_ENABLED", "true").lower() == "true"
FARM_SCAN_INTERVAL = int(os.environ.get("FARM_SCAN_INTERVAL", "30"))
FARM_MAX_DISK_GB = int(os.environ.get("FARM_MAX_DISK_GB", "500"))
FARM_SEED_RATIO_TARGET = float(os.environ.get("FARM_SEED_RATIO_TARGET", "2.0"))
FARM_SEED_TIME_TARGET = int(os.environ.get("FARM_SEED_TIME_TARGET", "4320"))
FARM_SAVE_PATH = "/media/downloads/seed"

# Paths
MEDIA_ROOT = "/media"
DATA_DIR = "/app/data"
