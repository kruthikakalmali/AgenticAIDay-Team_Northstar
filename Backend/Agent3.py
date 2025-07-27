import os
import json
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import requests
import feedparser
import praw

load_dotenv()
# NOW = datetime.now(timezone.utc)
# SINCE = NOW - timedelta(hours=1000)
NOW = datetime.now(timezone.utc)
START_TIME = NOW - timedelta(hours=10000)
END_TIME = NOW
SINCE = START_TIME  # ✅ This ensures that checks like `if pub < SINCE:` work as expected

RSS_URL = (
    "https://news.google.com/rss/search"
    "?q=Bengaluru+traffic+OR+waterlogging+OR+protest"
    "&hl=en-IN&gl=IN&ceid=IN:en"
)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RedditScraper/1.0"

logging.basicConfig(level=logging.INFO)

def fetch_rss():
    logging.info("📰 Fetching Google News RSS…")
    try:
        r = requests.get(RSS_URL, headers={"User-Agent": USER_AGENT}, timeout=10)
        r.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to fetch RSS: {e}")
        return []

    feed = feedparser.parse(r.content)
    items = []
    for e in feed.entries:
        parsed = e.get("published_parsed")
        if not parsed:
            continue
        pub = datetime(*parsed[:6], tzinfo=timezone.utc)
        if pub < SINCE:
            continue
        items.append({
            "source": "news",
            "id": e.get("id", e.get("link", "")).strip(),
            "title": e.get("title", "").strip(),
            "link": e.get("link", "").strip(),
            "text": e.get("summary", "").strip(),
            "published": pub.isoformat()
        })
    logging.info(f"  → {len(items)} news items scraped")
    return items



def fetch_reddit():
    logging.info("👾 Fetching r/bangalore Reddit posts…")
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=USER_AGENT
    )
    items = []
    try:
        for submission in reddit.subreddit("bangalore").new(limit=50):
            ts = datetime.fromtimestamp(submission.created_utc, timezone.utc)
            if ts < SINCE:
                continue
            items.append({
                "source": "reddit",
                "id": "reddit_" + submission.id,
                "title": submission.title.strip(),
                "link": "https://reddit.com" + submission.permalink,
                "text": submission.selftext.strip(),
                "published": ts.isoformat()
            })
        logging.info(f"  → {len(items)} reddit posts scraped")
    except Exception as e:
        logging.error(f"Reddit fetch failed: {e}")
    return items

def run_scraper() -> list:
    """Run scraper agent and return all events as a list of dicts."""
    news = fetch_rss()
    reddit = fetch_reddit()
    all_items = news + reddit
    logging.info(f"✅ Total scraped items: {len(all_items)}")
    return all_items

# Optional for local test/debug
if __name__ == "__main__":
    data = run_scraper()
    print(json.dumps(data[:3], indent=2))  # show first 3 items only


# import os
# import json
# import logging
# from datetime import datetime, timezone, timedelta
# from dotenv import load_dotenv
# import requests
# import feedparser
# import praw
# import google.generativeai as genai

# # ⏱ Config
# load_dotenv()
# NOW = datetime.now(timezone.utc)
# START_TIME = NOW - timedelta(hours=10000)
# SINCE = START_TIME

# # 📢 User Agent
# USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KannadaNewsScraper/1.0"

# logging.basicConfig(level=logging.INFO)

# # 🌐 RSS URLs
# RSS_URL_EN = (
#     "https://news.google.com/rss/search"
#     "?q=Bengaluru+traffic+OR+waterlogging+OR+protest"
#     "&hl=en-IN&gl=IN&ceid=IN:en"
# )
# RSS_URL_KN = (
#     "https://news.google.com/rss/search"
#     "?q=ಬೆಂಗಳೂರು"
#     "&hl=kn-IN&gl=IN&ceid=IN:kn"
# )
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# genai.configure(api_key=GEMINI_API_KEY)
# model = genai.GenerativeModel("models/gemini-pro")
# # Gemini model
# # model = genai.GenerativeModel("gemini-pro")
# from google.cloud import translate_v2 as translate
# import logging

# translate_client = translate.Client()

# def translate_text(text: str, target="en") -> str:
#     try:
#         if not text.strip():
#             return ""
#         result = translate_client.translate(text, target_language=target)
#         return result["translatedText"]
#     except Exception as e:
#         logging.warning(f"Google Translate failed: {e}")
#         return text

# # def translate_text(text: str) -> str:
# #     try:
# #         prompt = f"Translate this Kannada text to English:\n\n{text}"
# #         response = model.generate_content(prompt)
# #         return response.text.strip()
# #     except Exception as e:
# #         logging.warning(f"Translation failed: {e}")
# #         return text

# # # 🌍 Translation Stub – Replace with Gemini or Google Translate API
# # def translate_text(text: str) -> str:
# #     try:
# #         # Replace this with real Gemini/Translate API call
# #         return f"[Translated] {text}"
# #     except Exception as e:
# #         logging.warning(f"Translation failed: {e}")
# #         return text


# # 📥 Fetch Kannada News & Translate
# def fetch_kannada_news():
#     logging.info("📰 Fetching Kannada Google News RSS…")
#     try:
#         r = requests.get(RSS_URL_KN, headers={"User-Agent": USER_AGENT}, timeout=10)
#         r.raise_for_status()
#     except Exception as e:
#         logging.error(f"Failed to fetch Kannada RSS: {e}")
#         return []

#     feed = feedparser.parse(r.content)
#     items = []
#     for e in feed.entries:
#         parsed = e.get("published_parsed")
#         if not parsed:
#             continue
#         pub = datetime(*parsed[:6], tzinfo=timezone.utc)
#         if pub < SINCE:
#             continue

#         original_title = e.get("title", "").strip()
#         original_summary = e.get("summary", "").strip()
#         translated_title = translate_text(original_title)
#         translated_summary = translate_text(original_summary)

#         items.append({
#             "source": "news_kn",
#             "id": e.get("id", e.get("link", "")).strip(),
#             "title": translated_title,
#             "original_title": original_title,
#             "link": e.get("link", "").strip(),
#             "text": translated_summary,
#             "original_text": original_summary,
#             "published": pub.isoformat()
#         })
#     logging.info(f"  → {len(items)} Kannada news items scraped and translated")
#     return items

# # 👾 Fetch Reddit
# def fetch_reddit():
#     logging.info("👾 Fetching r/bangalore Reddit posts…")
#     reddit = praw.Reddit(
#         client_id=os.getenv("REDDIT_CLIENT_ID"),
#         client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
#         user_agent=USER_AGENT
#     )
#     items = []
#     try:
#         for submission in reddit.subreddit("bangalore").new(limit=50):
#             ts = datetime.fromtimestamp(submission.created_utc, timezone.utc)
#             if ts < SINCE:
#                 continue
#             items.append({
#                 "source": "reddit",
#                 "id": "reddit_" + submission.id,
#                 "title": "Translated"+submission.title.strip(),
#                 "link": "https://reddit.com" + submission.permalink,
#                 "text": submission.selftext.strip(),
#                 "published": ts.isoformat()
#             })
#         logging.info(f"  → {len(items)} reddit posts scraped")
#     except Exception as e:
#         logging.error(f"Reddit fetch failed: {e}")
#     return items

# # 🧠 Scraper Orchestrator
# def run_scraper() -> list:
#     # news_en = fetch_english_news()
#     news_kn = fetch_kannada_news()
#     # reddit = fetch_reddit()
#     all_items =news_kn
#     logging.info(f"✅ Total scraped items: {len(all_items)}")
#     return all_items

# # 🧪 Local Test
# if __name__ == "__main__":
#     data = run_scraper()
#     print(json.dumps(data[:3], indent=2))  # show only first 3
