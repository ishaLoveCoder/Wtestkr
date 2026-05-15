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


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(data):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(data), f, indent=2)


SEEN_POSTS = load_seen()


def clean_filename(name):
    name = re.sub(r'[\/*?:"<>|]', '_', name)
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


# ================= TamilBlasters =================

def process_tamilblasters():

    scraper = cloudscraper.create_scraper()

    try:
        response = scraper.get(TBL_URL, timeout=20)

        soup = BeautifulSoup(response.text, "html.parser")

        topics = [
            a["href"]
            for a in soup.find_all(
                "a",
                href=re.compile(r'/forums/topic/')
            )
            if a.get("href")
        ]

        topics = list(dict.fromkeys(topics))[:15]

        for topic in topics:

            topic_url = topic if topic.startswith("http") else TBL_URL + topic

            try:
                topic_resp = scraper.get(topic_url, timeout=20)
                topic_soup = BeautifulSoup(topic_resp.text, "html.parser")

                torrents = topic_soup.find_all(
                    "a",
                    attrs={"data-fileext": "torrent"}
                )

                for item in torrents:

                    href = item.get("href")

                    if not href or href in SEEN_POSTS:
                        continue

                    title = item.get_text(strip=True)

                    title = title.replace(
                        "www.1TamilBlasters.red - ",
                        ""
                    )

                    file_resp = scraper.get(href, timeout=20)

                    if file_resp.status_code != 200:
                        continue

                    file_bytes = io.BytesIO(file_resp.content)

                    filename = clean_filename(title)

                    caption = (
                        f"<b>{title}</b>

"
                        f"#TamilBlasters
"
                        f"Powered By {BOT_TAG}"
                    )

                    send_torrent(file_bytes, filename, caption)

                    SEEN_POSTS.add(href)
                    save_seen(SEEN_POSTS)

                    logging.info(f"Posted TBL: {title}")

                    time.sleep(3)

            except Exception as e:
                logging.error(f"TBL Topic Error: {e}")

    except Exception as e:
        logging.error(f"TBL Error: {e}")


# ================= TamilMV =================

def process_tamilmv():

    scraper = cloudscraper.create_scraper()

    try:
        response = scraper.get(TMV_URL, timeout=20)

        soup = BeautifulSoup(response.text, "html.parser")

        topics = [
            urljoin(TMV_URL, a["href"])
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

                        href = urljoin(TMV_URL, a["href"])

                        if href in SEEN_POSTS:
                            continue

                        file_resp = scraper.get(href, timeout=20)

                        if file_resp.status_code != 200:
                            continue

                        file_bytes = io.BytesIO(file_resp.content)

                        filename = clean_filename(link_text)

                        caption = (
                            f"<b>{link_text}</b>

"
                            f"#TamilMV
"
                            f"Powered By {BOT_TAG}"
                        )

                        send_torrent(file_bytes, filename, caption)

                        SEEN_POSTS.add(href)
                        save_seen(SEEN_POSTS)

                        logging.info(f"Posted TMV: {link_text}")

                        time.sleep(3)

            except Exception as e:
                logging.error(f"TMV Topic Error: {e}")

    except Exception as e:
        logging.error(f"TMV Error: {e}")


# ================= Scheduler =================

def scheduler():

    while True:

        try:
            process_tamilmv()
            process_tamilblasters()
        except Exception as e:
            logging.error(e)

        time.sleep(CHECK_DELAY)


def run_bot():

    threading.Thread(target=scheduler, daemon=True).start()

    print("✅ Torrent Bot Started")

    bot.infinity_polling(skip_pending=True)
