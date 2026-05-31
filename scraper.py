import requests
import json, os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import fitz

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen_notices.json"

def get_notices():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/chromium-browser"

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    driver.get("https://www.bubt.edu.bd/notice")

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

def pdf_to_images(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=150)
        images.append(pix.tobytes("png"))
    return images

def send_notice_as_images(pdf_url, title):
    try:
        response = requests.get(pdf_url, timeout=15)
        images = pdf_to_images(response.content)
        print(f"PDF has {len(images)} pages")

        for i, img_bytes in enumerate(images):
            caption = f"🔔 {title}" if i == 0 else f"📄 Page {i+1}"
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"photo": (f"page{i+1}.png", img_bytes, "image/png")}
            )
            print(f"Page {i+1} sent:", r.status_code)
            if r.status_code != 200:
                print(r.text)

    except Exception as e:
        print("Error:", e)
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": f"🔔 <b>{title}</b>\n\n🔗 {pdf_url}", "parse_mode": "HTML"}
        )

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
        send_notice_as_images(n["url"], n["title"])
        seen.add(n["url"])

save_seen(seen)
