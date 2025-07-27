import os
import uuid
import time
from datetime import datetime, timezone
from collections import defaultdict

from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer, util
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-pro")

# Neo4j connection
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

encoder = SentenceTransformer("all-MiniLM-L6-v2")

def fetch_all_items(tx):
    query = """
    MATCH (n:Incident)
    OPTIONAL MATCH (n)<-[:ABOUT]-(inf:Inference)
    WHERE inf IS NULL
    RETURN n.id AS id,
           COALESCE(n.merged_titles, [n.title]) AS titles,
           n.event_type AS event_type,
           n.jurisdiction AS jurisdiction
    """
    return [r.data() for r in tx.run(query)]

def group_by_bucket(items):
    buckets = defaultdict(list)
    for item in items:
        key = (item["jurisdiction"], item["event_type"])
        buckets[key].append(item)
    return buckets

def deduplicate_and_group(bucket, threshold=0.7):
    flat = []
    for item in bucket:
        for t in item["titles"]:
            if t:
                flat.append({
                    "id": item["id"],
                    "jurisdiction": item["jurisdiction"],
                    "event_type": item["event_type"],
                    "title": t
                })

    if len(flat) < 3:
        return []

    titles = [e["title"] for e in flat]
    embeddings = encoder.encode(titles, convert_to_tensor=True)
    used, groups = set(), []

    for i in range(len(flat)):
        if i in used:
            continue
        group = [flat[i]]
        used.add(i)
        sim = util.pytorch_cos_sim(embeddings[i], embeddings)[0]
        for j in range(i + 1, len(flat)):
            if j not in used and sim[j] > threshold:
                group.append(flat[j])
                used.add(j)
        if len(group) >= 3:
            groups.append(group)
    return groups

def generate_summary(event_type, jurisdiction, titles):
    prompt = f"""
You are a trends analyst like Google Trends. Only summarize if there’s a strong, non-trivial pattern across incidents.

Event Type: {event_type}
Jurisdiction: {jurisdiction or "Unknown"}
Incident Titles:
{chr(10).join(f"- {t}" for t in titles[:10])}

Step 1: Analyze if a clear, repetitive or noteworthy trend exists.
Step 2: If confident, write a short 2–3 sentence public-facing inference of the likely real-world cause or pattern.
Step 3: If not confident, just say "NO INFERENCE".
"""
    for _ in range(2):
        try:
            response = model.generate_content(prompt)
            result = response.text.strip()
            if result.upper().startswith("NO INFERENCE"):
                return None
            return result
        except Exception as e:
            print(f"❌ Gemini error: {e}")
            time.sleep(1)
    return None

def create_inference(tx, summary, sources, ids, jurisdiction):
    inference_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    print(f"[🧠] Creating inference: {inference_id}")

    tx.run("""
    UNWIND $ids AS eid
    MATCH (e) WHERE e.id = eid
    WITH collect(e) AS collected_entities
CREATE (infNode:Inference {
  id: $id,
  summary: $summary,
  sources: $sources,
  created_at: datetime($now)
})
WITH collected_entities, infNode
UNWIND collected_entities AS entity

    MERGE (infNode)-[:ABOUT]->(entity)
    WITH infNode
    OPTIONAL MATCH (j:Jurisdiction {name: $jurisdiction})
    FOREACH (_ IN CASE WHEN j IS NOT NULL THEN [1] ELSE [] END |
        MERGE (infNode)-[:MENTIONS]->(j)
    )
    """, id=inference_id, summary=summary, sources=sources,
         ids=ids, now=now, jurisdiction=jurisdiction)


def run_pipeline():
    print("🚀 Running Multi-source Inference Pipeline")
    with driver.session() as session:
        items = session.execute_read(fetch_all_items)
        print(f"[📦] Found {len(items)} un-inferred items")

        grouped = group_by_bucket(items)
        created = 0

        for (jurisdiction, event_type), bucket in grouped.items():
            print(f"\n=== Bucket: {jurisdiction or 'Unknown'} - {event_type} ===")
            groups = deduplicate_and_group(bucket)

            for group in groups:
                titles = [x["title"] for x in group]
                ids = list(set(x["id"] for x in group))
                sources = list(set("reddit" if id.startswith("reddit") else "news" for id in ids))

                summary = generate_summary(event_type, jurisdiction, titles)
                if summary:
                    session.execute_write(
                        create_inference, summary, sources, ids, jurisdiction
                    )
                    created += 1
                else:
                    print("🛑 No valid pattern found")

    print(f"✨ Inference generation complete. ✅ {created} inferences created")

if __name__ == "__main__":
    run_pipeline()
