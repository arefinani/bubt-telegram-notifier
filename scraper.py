import os
import requests
from bs4 import BeautifulSoup

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SEEN_FILE = "seen_notices.txt"


def send_telegram(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": msg,
            "disable_web_page_preview": False
        },
        timeout=20
    )


def get_latest_notice():
    url = "https://www.bubt.edu.bd/notice"

    r = requests.get(url, timeout=20)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "/notice/details/" in href:
            title = a.get_text(strip=True)

            if not title:
                continue

            if href.startswith("/"):
                href = "https://www.bubt.edu.bd" + href

            return {
                "title": title,
                "url": href
            }

    return None


def read_last():
    if os.path.exists(SEEN_FILE):
        return open(SEEN_FILE).read().strip()
    return ""


def save_last(url):
    with open(SEEN_FILE, "w") as f:
        f.write(url)


latest = get_latest_notice()

if latest is None:
    print("No notice found")
    raise SystemExit()

last_url = read_last()

if latest["url"] != last_url:

    message = (
        f"📢 New BUBT Notice\n\n"
        f"{latest['title']}\n\n"
        f"{latest['url']}"
    )

    send_telegram(message)

    save_last(latest["url"])

    print("New notice sent")

else:
    print("No new notice")
