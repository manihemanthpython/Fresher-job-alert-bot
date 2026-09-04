import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SEARCH_ROLES = [
    "Data Scientist",
    "Data Analyst",
    "Machine Learning Engineer",
]

CSV_FILE = "jobs_database.csv"

def fetch_jobs(query: str):
    url = "https://jsearch.p.rapidapi.com/search"
    params = {
        "query": f"{query} in India",
        "page": "1",
        "num_pages": "1",
        "date_posted": "today"
    }
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "jsearch.p.rapidapi.com"
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=20)
        res.raise_for_status()
        return res.json().get("data", [])
    except Exception as e:
        print(f"Error fetching '{query}': {e}")
        return []

def send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram bot token or chat ID not set. Skipping Telegram notification.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=20)
        res.raise_for_status()
        print("Telegram message sent successfully.")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        try:
            payload.pop("parse_mode", None)
            fallback_res = requests.post(url, json=payload, timeout=20)
            fallback_res.raise_for_status()
            print("Telegram message sent as plain text fallback.")
        except Exception as fallback_err:
            print(f"Failed fallback sending: {fallback_err}")


def main():
    if not RAPIDAPI_KEY:
        raise ValueError("RAPIDAPI_KEY secret is missing!")

    new_jobs = []
    for role in SEARCH_ROLES:
        data = fetch_jobs(role)
        for item in data:
            new_jobs.append({
                "job_id": item.get("job_id"),
                "title": item.get("job_title"),
                "company": item.get("employer_name"),
                "location": f"{item.get('job_city', '')}, {item.get('job_country', '')}",
                "apply_link": item.get("job_apply_link"),
                "posted_at": item.get("job_posted_at_datetime_utc"),
                "extracted_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    if not new_jobs:
        print("No jobs found today.")
        return

    new_df = pd.DataFrame(new_jobs)

    if os.path.exists(CSV_FILE):
        existing_df = pd.read_csv(CSV_FILE)
        combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=["job_id"], keep="first")
    else:
        combined_df = new_df.drop_duplicates(subset=["job_id"], keep="first")

    combined_df.to_csv(CSV_FILE, index=False)
    print(f"Added new jobs. Total records: {len(combined_df)}")

    message = [f"🚀 *Morning Fresher Alert ({datetime.now().strftime('%d %b %Y')})*\n"]
    for _, row in new_df.head(5).iterrows():
        message.append(f"• *{row['title']}* at *{row['company']}*\n  [Apply Here]({row['apply_link']})\n")

    send_telegram("\n".join(message))

if __name__ == "__main__":
    main()