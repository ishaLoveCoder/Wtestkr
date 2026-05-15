import threading

from app import run_web
from bot import TorrentBot

threading.Thread(target=run_web, daemon=True).start()

TorrentBot().run()
