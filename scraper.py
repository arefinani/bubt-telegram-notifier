import requests
from bs4 import BeautifulSoup
import json, os

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen_notices.json"

def get_notices():
    url = "https://www.bubt.edu.bd/notice"
    r = requests.get(url, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    notices = []
    # Grab all notice links
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if text and "/notice/" in href:
            full_url = "https://www.bubt.edu.bd" + href if href.startswith("/") else href
            notices.append({"title": text, "url": full_url})
    return notices[:10]  # latest 10

def send_telegram(message):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    )

def load_seen():
    if os.path.exists(SEEN_FILE):
        return set(json.load(open(SEEN_FILE)))
    return set()

def save_seen(seen):
    json.dump(list(seen), open(SEEN_FILE, "w"))

seen = load_seen()
notices = get_notices()
new_found = False

for n in notices:
    if n["url"] not in seen:
        send_telegram(f"🔔 <b>New BUBT Notice</b>\n\n{n['title']}\n\n🔗 {n['url']}")
        seen.add(n["url"])
        new_found = True

save_seen(seen)
