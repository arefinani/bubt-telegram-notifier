import requests
import json, os

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen_notices.json"

def get_notices():
    # BUBT loads notices via API - try common endpoints
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bubt.edu.bd/notice",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # Try the API endpoint (found from network inspection)
    endpoints = [
        "https://www.bubt.edu.bd/api/notice/list",
        "https://www.bubt.edu.bd/notice/list",
        "https://www.bubt.edu.bd/notices/all",
    ]
    
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f"Tried {url} → status {r.status_code}")
            if r.status_code == 200:
                print(r.text[:500])
        except Exception as e:
            print(f"Error: {e}")

def send_telegram(message):
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message}
    )
    print("Telegram:", r.status_code)

send_telegram("🔍 Detecting BUBT notice API...")
get_notices()
