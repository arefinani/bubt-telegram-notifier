import requests
import json, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen_notices.json"

def get_notices():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    driver.get("https://www.bubt.edu.bd/notice")
    
    # Wait for notices to load
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "table"))
    )
    
    notices = []
    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
    print(f"Found {len(rows)} rows")
    
    for row in rows:
        try:
            title = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)").text.strip()
            link = row.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
            if title and link:
                notices.append({"title": title, "url": link})
                print(f"Notice: {title[:60]}")
        except:
            continue
    
    driver.quit()
    return notices[:10]

def send_telegram(message):
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    )
    print("Telegram:", r.status_code)

def send_pdf(pdf_url, caption):
    try:
        pdf = requests.get(pdf_url, timeout=15)
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument",
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"document": ("notice.pdf", pdf.content, "application/pdf")}
        )
        print("PDF sent:", r.status_code)
    except Exception as e:
        print("PDF error:", e)
        send_telegram(f"🔔 <b>{caption}</b>\n\n🔗 {pdf_url}")

def load_seen():
    if os.path.exists(SEEN_FILE):
        return set(json.load(open(SEEN_FILE)))
    return set()

def save_seen(seen):
    json.dump(list(seen), open(SEEN_FILE, "w"))

seen = load_seen()
notices = get_notices()

for n in notices:
    if n["url"] not in seen:
        send_pdf(n["url"], n["title"])
        seen.add(n["url"])

save_seen(seen)
