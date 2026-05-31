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
