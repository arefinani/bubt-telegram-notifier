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

def get_latest_notice():
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
    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
    print(f"Total rows found: {len(rows)}")
    notice = None
    for row in rows:
        try:
            title = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)").text.strip()
            eye = row.find_element(By.CSS_SELECTOR, "a")
            detail_url = eye.get_attribute("href")
            if title and detail_url:
                print(f"Latest notice: {title}")
                print(f"Detail URL: {detail_url}")
                notice = {"title": title, "detail_url": detail_url}
                break
        except Exception as e:
            print("Row error:", e)
            continue
    if notice:
        driver.get(notice["detail_url"])
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        pdf_url = None
        for a in driver.find_elements(By.TAG_NAME, "a"):
            href = a.get_attribute("href") or ""
            if "storage/notices" in href and ".pdf" in href:
                pdf_url = href
                print(f"PDF URL found: {pdf_url}")
                break
        notice["pdf_url"] = pdf_url
    driver.quit()
    return notice

def pdf_to_single_image(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    width = 0
    total_height = 0
    for page in doc:
        pix = page.get_pixmap(dpi=150)
        pages.append(pix)
        width = max(width, pix.width)
        total_height += pix.height
    combined = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, width, total_height))
    combined.clear_with(255)
    y = 0
    for pix in pages:
        combined.copy(pix, fitz.IRect(0, y, pix.width, y + pix.height))
        y += pix.height
    return combined.tobytes("png")

def send_notice(notice):
    title = notice["title"]
    pdf_url = notice.get("pdf_url")
    if not pdf_url:
        print("No PDF URL found, sending text message")
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": f"🔔 <b>{title}</b>\n\n🔗 {notice['detail_url']}", "parse_mode": "HTML"}
        )
        return
    try:
        response = requests.get(pdf_url, timeout=15)
        print(f"PDF downloaded: {len(response.content)} bytes")
        img_bytes = pdf_to_single_image(response.content)
        print(f"Image size: {len(img_bytes)} bytes")
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": f"🔔 {title}"},
            files={"photo": ("notice.png", img_bytes, "image/png")}
        )
        print("Photo sent:", r.status_code, r.text[:200])
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
notice = get_latest_notice()

if notice and notice["detail_url"] not in seen:
    send_notice(notice)
    seen.add(notice["detail_url"])
    save_seen(seen)
else:
    print("No new notice.")
