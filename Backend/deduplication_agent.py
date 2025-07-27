import os
import uuid
from datetime import datetime, timezone

from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer, util
import google.generativeai as genai
from dotenv import load_dotenv

# --- Load credentials ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-1.5-pro")

# Neo4j config
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

def summarize_titles(titles, event_type, jurisdiction):
    prompt = f"""
You are summarizing real-world incident reports.

Event Type: {event_type}
Jurisdiction: {jurisdiction or "Unknown"}
Here are the event titles:
{chr(10).join(f"- {t}" for t in titles[:10])}

Write a 2-3 sentence citizen-facing summary of what likely happened. Be concise and specific.
"""
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Gemini error: {e}")
        return None

def fetch_all_items(tx):
    print("[🔍] Fetching all incidents and clusters with titles")
    result = tx.run("""
        MATCH (n)
        WHERE (n:Incident OR n:EventCluster) AND (n.title_sample IS NOT NULL OR n.title IS NOT NULL)
        RETURN n.id AS id, 
               COALESCE(n.title_sample, n.title) AS title,
               n.source AS source, 
               n.event_type AS event_type, 
               n.jurisdiction AS jurisdiction, 
               labels(n)[0] AS label
    """)
    records = [record.data() for record in result]
    print(f"[📥] Retrieved {len(records)} items (incidents + clusters)")
    return records

def group_by_bucket(items):
    buckets = {}
    for item in items:
        key = (item["jurisdiction"], item["event_type"])
        buckets.setdefault(key, []).append(item)
    print(f"[📊] Grouped into {len(buckets)} buckets")
    return buckets

def deduplicate_cluster(items, threshold=0.7):
    titles = [e["title"] for e in items if e["title"]]
    embeddings = model.encode(titles, convert_to_tensor=True)
    clusters = []
    used = set()

    print(f"[🧠] Deduplicating {len(items)} items with similarity threshold {threshold}")
    for i in range(len(items)):
        if i in used or not items[i]["title"]:
            continue
        cluster = [items[i]]
        used.add(i)
        cos_scores = util.pytorch_cos_sim(embeddings[i], embeddings)[0]
        for j in range(i + 1, len(items)):
            if j not in used and items[j]["title"] and cos_scores[j] > threshold:
                cluster.append(items[j])
                used.add(j)
        if len(cluster) >= 3:
            clusters.append(cluster)
            print(f"  ✅ Cluster of size {len(cluster)} with sample: {cluster[0]['title'][:60]}")
    print(f"[🔁] Total clusters formed: {len(clusters)}")
    return clusters

def create_event_cluster(tx, cluster, jurisdiction, event_type):
    sources = list({e.get("source", "unknown") for e in cluster if e.get("source")})
    ids = [e["id"] for e in cluster if e.get("id")]
    labels = [e["label"] for e in cluster if e.get("label")]
    titles = [e["title"] for e in cluster if e.get("title")]

    summary = summarize_titles(titles, event_type, jurisdiction)
    if not summary:
        summary = "Summary unavailable."

    summary_title = titles[0] if titles else "Untitled Cluster"
    cluster_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    print(f"[📌] Creating cluster: {cluster_id}")
    print(f"     Jurisdiction: {jurisdiction or 'Unknown'}, Event Type: {event_type}")

    tx.run("""
    CREATE (c:EventCluster {
        id: $id,
        event_type: $event_type,
        jurisdiction: $jurisdiction,
        event_ids: $ids,
        sources: $sources,
        event_count: $count,
        title_sample: $title_sample,
        summary: $summary,
        merged_titles: $titles,
        created_at: datetime($now)
    })
    WITH c
    OPTIONAL MATCH (j:Jurisdiction {name: $jurisdiction})
    FOREACH (_ IN CASE WHEN j IS NOT NULL THEN [1] ELSE [] END |
        MERGE (c)-[:BELONGS_TO]->(j)
    )
    WITH c, $ids AS item_ids, $labels AS item_labels
    UNWIND RANGE(0, size(item_ids)-1) AS idx
    WITH c, item_ids[idx] AS eid, item_labels[idx] AS lbl
    CALL apoc.do.when(
        lbl = 'Incident',
        'MATCH (n:Incident {id: $eid}) MERGE (n)-[:PART_OF]->(c) DETACH DELETE n',
        '
         MATCH (n:EventCluster {id: $eid}) 
         OPTIONAL MATCH (i:Incident)-[:PART_OF]->(n)
         WITH $c AS newCluster, collect(i) AS incidents, n
         UNWIND incidents AS x
         MERGE (x)-[:PART_OF]->(c)
         DETACH DELETE n
        ',
        {eid: eid, c: c}
    ) YIELD value
    RETURN count(*)
""",
    id=cluster_id,
    event_type=event_type,
    jurisdiction=jurisdiction,
    ids=ids,
    sources=sources,
    count=len(cluster),
    title_sample=summary_title,
    summary=summary,
    now=now,
    labels=labels,
    titles=titles  # ✅ ADD THIS LINE
)

def run_pipeline():
    print("🚀 Starting Deduplication + Merging Pipeline")
    with driver.session() as session:
        try:
            items = session.execute_read(fetch_all_items)
            if not items:
                print("⚠️ No data found.")
                return
            grouped = group_by_bucket(items)

            for (jurisdiction, event_type), group in grouped.items():
                print(f"\n=== Processing Bucket: {jurisdiction or 'Unknown'} - {event_type} ===")
                clusters = deduplicate_cluster(group)
                for cluster in clusters:
                    session.execute_write(create_event_cluster, cluster, jurisdiction, event_type)

        except Exception as e:
            print("❌ Pipeline error:", str(e))

    print("✨ Deduplication + Merge complete")

if __name__ == "__main__":
    run_pipeline()
