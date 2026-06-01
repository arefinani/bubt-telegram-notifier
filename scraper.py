import requests
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import fitz

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen_notices.json"


def get_latest_notices():
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
    print("Total rows found: " + str(len(rows)))

    notices = []
    for row in rows:
        try:
            title = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)").text.strip()
            eye = row.find_element(By.CSS_SELECTOR, "a")
            detail_url = eye.get_attribute("href")
            if title and detail_url:
                print("Notice: " + title)
                notices.append({"title": title, "detail_url": detail_url})
                if len(notices) == 5:
                    break
        except Exception as e:
            print("Row error: " + str(e))
            continue

    result = []
    for notice in notices:
        try:
            driver.get(notice["detail_url"])
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            pdf_url = None
            for a in driver.find_elements(By.TAG_NAME, "a"):
                href = a.get_attribute("href") or ""
                if "storage/notices" in href and ".pdf" in href:
                    pdf_url = href
                    print("PDF URL found: " + pdf_url)
                    break
            notice["pdf_url"] = pdf_url
            result.append(notice)
        except Exception as e:
            print("Detail page error: " + str(e))
            continue

    driver.quit()
    return result


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
            "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage",
            json={"chat_id": CHAT_ID, "text": "New Notice: " + title + "\n\n" + notice["detail_url"]}
        )
        return
    try:
        response = requests.get(pdf_url, timeout=15)
        print("PDF downloaded: " + str(len(response.content)) + " bytes")
        img_bytes = pdf_to_single_image(response.content)
        print("Image size: " + str(len(img_bytes)) + " bytes")
        r = requests.post(
            "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": "New Notice🚨:\n " + title + "\n\n" + pdf_url},
            files={"photo": ("notice.png", img_bytes, "image/png")}
        )
        print("Photo sent: " + str(r.status_code))
        print(r.text[:200])
    except Exception as e:
        print("Error: " + str(e))
        requests.post(
            "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage",
            json={"chat_id": CHAT_ID, "text": "New Notice: " + title + "\n\n" + pdf_url}
        )


def load_seen():
    if os.path.exists(SEEN_FILE):
        return set(json.load(open(SEEN_FILE)))
    return set()


def save_seen(seen):
    json.dump(list(seen), open(SEEN_FILE, "w"))


seen = load_seen()
notices = get_latest_notices()

for notice in notices:
    if notice["detail_url"] not in seen:
        send_notice(notice)
        seen.add(notice["detail_url"])

save_seen(seen)
