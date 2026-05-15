import os
import re
import io
import json
import time
import logging
import threading
import requests
import telebot
import cloudscraper

from bs4 import BeautifulSoup
from urllib.parse import urljoin

from config import (
    BOT_TOKEN,
    ADMIN_IDS,
    TRNT_FILE_POST_CHNL,
    TMV_URL,
    TBL_URL,
    BOT_TAG,
    TMV_TORRENT_THUMB,
    CHECK_DELAY
)

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

SEEN_FILE = "seen_posts.json"

# ── Runtime mutable settings ──────────────────────────────
current_tmv_url    = TMV_URL
current_tbl_url    = TBL_URL
current_delay      = CHECK_DELAY
scheduler_running  = True          # scheduler ko pause/resume ke liye


# ── Seen posts ────────────────────────────────────────────
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(data):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(data), f, indent=2)


SEEN_POSTS = load_seen()


# ── Helpers ───────────────────────────────────────────────
def is_admin(message):
    return message.from_user.id in ADMIN_IDS


def clean_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    name = name.replace('.torrent', '')
    return f"{BOT_TAG} - {name}.torrent"


def send_torrent(file_bytes, filename, caption):
    try:
        bot.send_document(
            chat_id=TRNT_FILE_POST_CHNL,
            document=file_bytes,
            visible_file_name=filename,
            caption=caption
        )
    except Exception as e:
        logging.error(e)


# ── TamilBlasters ─────────────────────────────────────────
def process_tamilblasters(manual=False):
    global current_tbl_url
    scraper = cloudscraper.create_scraper()
    new_count = 0

    try:
        response = scraper.get(current_tbl_url, timeout=20)
        soup = BeautifulSoup(response.text, "html.parser")

        topics = [
            a["href"]
            for a in soup.find_all("a", href=re.compile(r'/forums/topic/'))
            if a.get("href")
        ]
        topics = list(dict.fromkeys(topics))[:15]

        for topic in topics:
            topic_url = topic if topic.startswith("http") else current_tbl_url + topic

            try:
                topic_resp = scraper.get(topic_url, timeout=20)
                topic_soup = BeautifulSoup(topic_resp.text, "html.parser")
                torrents = topic_soup.find_all("a", attrs={"data-fileext": "torrent"})

                for item in torrents:
                    href = item.get("href")
                    if not href or href in SEEN_POSTS:
                        continue

                    title = item.get_text(strip=True).replace("www.1TamilBlasters.red - ", "")
                    file_resp = scraper.get(href, timeout=20)

                    if file_resp.status_code != 200:
                        continue

                    file_bytes = io.BytesIO(file_resp.content)
                    filename = clean_filename(title)
                    caption = (
                        f"<b>{title}</b>\n\n"
                        f"#TamilBlasters\n"
                        f"Powered By {BOT_TAG}"
                    )

                    send_torrent(file_bytes, filename, caption)
                    SEEN_POSTS.add(href)
                    save_seen(SEEN_POSTS)
                    logging.info(f"Posted TBL: {title}")
                    new_count += 1
                    time.sleep(3)

            except Exception as e:
                logging.error(f"TBL Topic Error: {e}")

    except Exception as e:
        logging.error(f"TBL Error: {e}")

    return new_count


# ── TamilMV ───────────────────────────────────────────────
def process_tamilmv(manual=False):
    global current_tmv_url
    scraper = cloudscraper.create_scraper()
    new_count = 0

    try:
        response = scraper.get(current_tmv_url, timeout=20)
        soup = BeautifulSoup(response.text, "html.parser")

        topics = [
            urljoin(current_tmv_url, a["href"])
            for a in soup.find_all("a", href=True)
            if "topic" in a["href"]
        ][:30]

        for topic_url in topics:
            try:
                topic_html = scraper.get(topic_url, timeout=20).text
                topic_soup = BeautifulSoup(topic_html, "html.parser")
                posts = topic_soup.find_all("div", class_="cPost_contentWrap")

                for post in posts:
                    for a in post.find_all("a", href=True):
                        link_text = a.get_text(strip=True)

                        if "torrent" not in link_text.lower():
                            continue

                        href = urljoin(current_tmv_url, a["href"])

                        if href in SEEN_POSTS:
                            continue

                        file_resp = scraper.get(href, timeout=20)

                        if file_resp.status_code != 200:
                            continue

                        file_bytes = io.BytesIO(file_resp.content)
                        filename = clean_filename(link_text)
                        caption = (
                            f"<b>{link_text}</b>\n\n"
                            f"#TamilMV\n"
                            f"Powered By {BOT_TAG}"
                        )

                        send_torrent(file_bytes, filename, caption)
                        SEEN_POSTS.add(href)
                        save_seen(SEEN_POSTS)
                        logging.info(f"Posted TMV: {link_text}")
                        new_count += 1
                        time.sleep(3)

            except Exception as e:
                logging.error(f"TMV Topic Error: {e}")

    except Exception as e:
        logging.error(f"TMV Error: {e}")

    return new_count


# ── Scheduler ─────────────────────────────────────────────
def scheduler():
    global scheduler_running, current_delay
    while True:
        if scheduler_running:
            try:
                process_tamilmv()
                process_tamilblasters()
            except Exception as e:
                logging.error(e)
        time.sleep(current_delay)


# ══════════════════════════════════════════════════════════
#  BOT COMMANDS
# ══════════════════════════════════════════════════════════

# /start
@bot.message_handler(commands=["start", "help"])
def cmd_help(message):
    if not is_admin(message):
        return
    text = (
        "<b>🤖 Bot Commands</b>\n\n"
        "<b>Domain:</b>\n"
        "  /settmv &lt;url&gt; — TamilMV domain set karo\n"
        "  /settbl &lt;url&gt; — TamilBlasters domain set karo\n"
        "  /getdomains — current domains dekho\n\n"
        "<b>Delay:</b>\n"
        "  /setdelay &lt;seconds&gt; — check delay change karo\n"
        "  /getdelay — current delay dekho\n\n"
        "<b>Manual Check:</b>\n"
        "  /checknow — abhi dono sites check karo\n"
        "  /checktmv — sirf TamilMV check karo\n"
        "  /checktbl — sirf TamilBlasters check karo\n\n"
        "<b>Control:</b>\n"
        "  /pause — scheduler band karo\n"
        "  /resume — scheduler chalu karo\n"
        "  /status — bot status dekho"
    )
    bot.reply_to(message, text)


# /settmv <url>
@bot.message_handler(commands=["settmv"])
def cmd_settmv(message):
    global current_tmv_url
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /settmv https://new-domain.com")
        return
    current_tmv_url = parts[1].strip().rstrip("/")
    bot.reply_to(message, f"✅ TamilMV URL updated:\n<code>{current_tmv_url}</code>")


# /settbl <url>
@bot.message_handler(commands=["settbl"])
def cmd_settbl(message):
    global current_tbl_url
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /settbl https://new-domain.com")
        return
    current_tbl_url = parts[1].strip().rstrip("/")
    bot.reply_to(message, f"✅ TamilBlasters URL updated:\n<code>{current_tbl_url}</code>")


# /getdomains
@bot.message_handler(commands=["getdomains"])
def cmd_getdomains(message):
    if not is_admin(message):
        return
    bot.reply_to(
        message,
        f"<b>Current Domains:</b>\n"
        f"🔹 TamilMV: <code>{current_tmv_url}</code>\n"
        f"🔹 TamilBlasters: <code>{current_tbl_url}</code>"
    )


# /setdelay <seconds>
@bot.message_handler(commands=["setdelay"])
def cmd_setdelay(message):
    global current_delay
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        bot.reply_to(message, "Usage: /setdelay 600  (seconds mein)")
        return
    current_delay = int(parts[1].strip())
    bot.reply_to(message, f"✅ Delay updated: <b>{current_delay} seconds</b> ({current_delay//60} min)")


# /getdelay
@bot.message_handler(commands=["getdelay"])
def cmd_getdelay(message):
    if not is_admin(message):
        return
    bot.reply_to(
        message,
        f"⏱ Current delay: <b>{current_delay} seconds</b> ({current_delay//60} min)"
    )


# /checknow
@bot.message_handler(commands=["checknow"])
def cmd_checknow(message):
    if not is_admin(message):
        return
    msg = bot.reply_to(message, "🔍 Dono sites check ho rahi hain...")

    def run():
        tmv = process_tamilmv(manual=True)
        tbl = process_tamilblasters(manual=True)
        total = tmv + tbl
        bot.edit_message_text(
            f"✅ Check complete!\n"
            f"🔹 TamilMV: <b>{tmv}</b> new posts\n"
            f"🔹 TamilBlasters: <b>{tbl}</b> new posts\n"
            f"📦 Total: <b>{total}</b>",
            chat_id=msg.chat.id,
            message_id=msg.message_id
        )

    threading.Thread(target=run, daemon=True).start()


# /checktmv
@bot.message_handler(commands=["checktmv"])
def cmd_checktmv(message):
    if not is_admin(message):
        return
    msg = bot.reply_to(message, "🔍 TamilMV check ho raha hai...")

    def run():
        count = process_tamilmv(manual=True)
        bot.edit_message_text(
            f"✅ TamilMV done! <b>{count}</b> new posts posted.",
            chat_id=msg.chat.id,
            message_id=msg.message_id
        )

    threading.Thread(target=run, daemon=True).start()


# /checktbl
@bot.message_handler(commands=["checktbl"])
def cmd_checktbl(message):
    if not is_admin(message):
        return
    msg = bot.reply_to(message, "🔍 TamilBlasters check ho raha hai...")

    def run():
        count = process_tamilblasters(manual=True)
        bot.edit_message_text(
            f"✅ TamilBlasters done! <b>{count}</b> new posts posted.",
            chat_id=msg.chat.id,
            message_id=msg.message_id
        )

    threading.Thread(target=run, daemon=True).start()


# /pause
@bot.message_handler(commands=["pause"])
def cmd_pause(message):
    global scheduler_running
    if not is_admin(message):
        return
    scheduler_running = False
    bot.reply_to(message, "⏸ Scheduler paused. Manual check ke liye /checknow use karo.")


# /resume
@bot.message_handler(commands=["resume"])
def cmd_resume(message):
    global scheduler_running
    if not is_admin(message):
        return
    scheduler_running = True
    bot.reply_to(message, "▶️ Scheduler resumed.")


# /status
@bot.message_handler(commands=["status"])
def cmd_status(message):
    if not is_admin(message):
        return
    status = "▶️ Running" if scheduler_running else "⏸ Paused"
    bot.reply_to(
        message,
        f"<b>Bot Status:</b>\n"
        f"🔄 Scheduler: {status}\n"
        f"⏱ Delay: {current_delay}s ({current_delay//60} min)\n"
        f"🌐 TMV: <code>{current_tmv_url}</code>\n"
        f"🌐 TBL: <code>{current_tbl_url}</code>\n"
        f"📋 Seen posts: {len(SEEN_POSTS)}"
    )


# ── Start ──────────────────────────────────────────────────
def run_bot():
    threading.Thread(target=scheduler, daemon=True).start()
    print("✅ Torrent Bot Started")
    bot.infinity_polling(skip_pending=True)
