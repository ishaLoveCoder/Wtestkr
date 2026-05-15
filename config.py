import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Admin IDs — env se load karo, comma separated
# Example env: ADMIN_IDS=123456789,987654321
ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "123456789").split(",")
    if x.strip().isdigit()
]

TRNT_FILE_POST_CHNL = int(os.getenv("TRNT_FILE_POST_CHNL", "-100xxxxxxxxxx"))

TMV_URL = os.getenv("TMV_URL", "https://www.1tamilmv.futbol")
TBL_URL = os.getenv("TBL_URL", "https://www.1tamilblasters.garden")

BOT_TAG = os.getenv("BOT_TAG", "@botname")

PORT = int(os.getenv("PORT", "8000"))

CHECK_DELAY = int(os.getenv("CHECK_DELAY", "900"))

TMV_TORRENT_THUMB = os.getenv(
    "TMV_TORRENT_THUMB",
    "https://i.ibb.co/7dq7mMLp/photo-2025-10"
)
