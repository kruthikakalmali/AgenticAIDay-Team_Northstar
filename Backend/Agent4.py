import os
import time
import json
import logging
import re
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
GENIE_MODEL = "gemini-2.0-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GENIE_MODEL}:generateContent?key={API_KEY}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RedditScraper/1.0"

logging.basicConfig(level=logging.INFO)

def chunk_items(items, chunk_size):
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]

def load_jurisdictions(filename="jurisdictions.txt"):
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def classify_with_gemini_batch(session, items, jurisdictions):
    jurisdictions_text = "\n".join(jurisdictions)
    prompt = (
        "You are a Bengaluru civic-pulse filter.\n"
        "Here is a list of possible jurisdictions:\n"
        f"{jurisdictions_text}\n\n"
        "Given these items, respond with EXACTLY valid JSON array. For each event, include a 'summary' field: a concise summary of the event/news based on its content.\n\n[\n"
    )
    for item in items:
        prompt += f'''  {{
  "title": "{item['title']}",
  "content": "{item['text'] or '(no body)'}",
  "timestamp": "{item['published']}",
  "summary": ""
}},\n'''
    prompt += "]\n\nFor each item, respond with:\n" + '''
[
  {
    "ingest": <true|false>,
    "event_type":"<pothole|waterlogging|protest|traffic|power_outage|other>",
    "jurisdiction":"<TrafficZone X|Ward Y|Unknown>",
    "summary": "<A concise summary of the event/news>"
  }
]
If possible, estimate the jurisdiction from the event text using the list above. If not, use "Unknown".
'''

    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    resp = session.post(API_URL, json=payload, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    parts = body.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = parts[0].get("text", "").strip() if parts else ""

    # strip markdown
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()

    def extract_first_json_array(s):
        start = s.find('[')
        if start == -1:
            return None
        count = 0
        for i in range(start, len(s)):
            if s[i] == '[':
                count += 1
            elif s[i] == ']':
                count -= 1
                if count == 0:
                    return s[start:i+1]
        return None

    json_blob = extract_first_json_array(text)
    if not json_blob:
        raise ValueError(f"No JSON array found in response: {text!r}")
    return json.loads(json_blob)

def run_schema_builder(events: list[dict], jurisdictions: list[str]) -> list[dict]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    enriched = []
    batch_size = 20
    idx = 0

    for chunk in chunk_items(events, batch_size):
        results = classify_with_gemini_batch(session, chunk, jurisdictions)
        for item, result in zip(chunk, results):
            item["ingest"] = bool(result.get("ingest", False))
            item["event_type"] = result.get("event_type", "other")
            item["jurisdiction"] = result.get("jurisdiction", "Unknown")
            item["summary"] = result.get("summary", "")
            enriched.append(item)
        idx += len(chunk)
        logging.info(f"🧠 Processed {idx}/{len(events)} events")
        time.sleep(2)  # Respect rate limits
    return enriched

# Optional: local test
if __name__ == "__main__":
    RAW_INPUT_FILE = "raw_events_24h.json"
    with open(RAW_INPUT_FILE, "r", encoding="utf-8") as f:
        raw_items = json.load(f)
    jurisdictions = load_jurisdictions()
    enriched = run_schema_builder(raw_items, jurisdictions)
    print(json.dumps(enriched[:3], indent=2))  # show first 3 results
