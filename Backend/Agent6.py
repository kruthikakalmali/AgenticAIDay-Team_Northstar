import os
import logging
from datetime import datetime
from geopy.distance import geodesic
from neo4j import GraphDatabase
import json
from google.cloud import pubsub_v1

# === Neo4j Setup ===
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.getenvb("NEO4J_PASSWORD")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

logging.basicConfig(level=logging.INFO)
GCP_PROJECT = os.getenv("GCP_PROJECT")
PUBSUB_TOPIC = "city-event-feed"

# publisher = pubsub_v1.PublisherClient()
# topic_path = publisher.topic_path(GCP_PROJECT, PUBSUB_TOPIC)


# === Point-in-Polygon Check ===
def point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-16) + xi):
            inside = not inside
        j = i
    return inside


# === 1. Load Traffic Jurisdictions ===
def load_jurisdictions(tx):
    q = """
    MATCH (j:TrafficJurisdiction)
    WHERE j.boundary IS NOT NULL
    RETURN elementId(j) AS id, j.name AS name, j.boundary AS boundary
    """
    jurisdictions = []
    for rec in tx.run(q):
        raw = rec["boundary"]
        pts = []
        for chunk in raw.split(","):
            parts = chunk.strip().split()
            if len(parts) >= 2:
                lng, lat = map(float, parts[:2])
                pts.append((lng, lat))
        if pts:
            jurisdictions.append({
                "id": rec["id"],
                "name": rec["name"],
                "coords": pts
            })
    return jurisdictions


# === 2. Find Jurisdiction for Location ===
def find_jurisdiction(lat, lng) -> dict:
    with driver.session() as sess:
        jurisdictions = sess.execute_read(load_jurisdictions)

    for jur in jurisdictions:
        if point_in_poly(lng, lat, jur["coords"]):
            logging.info(f"📍 Point inside jurisdiction '{jur['name']}' (ID: {jur['id']})")
            return jur
   

    # fallback to nearest
    best = None
    min_d = float("inf")
    for jur in jurisdictions:
        xs, ys = zip(*jur["coords"])
        centroid = (sum(ys) / len(ys), sum(xs) / len(xs))
        d = geodesic((lat, lng), centroid).km
        if d < min_d:
            min_d = d
            best = jur
    logging.info(f"📍 Fallback: nearest jurisdiction '{best['name']}' (~{min_d:.1f} km)")
    return best


# === 3. Get Jurisdiction-Specific Incidents ===
def get_incidents_by_jurisdiction_name(jur_name):
    q = """
    MATCH (i:Incident)
    WHERE i.jurisdiction = $jur_name
    RETURN i
    """
    with driver.session() as sess:
        return [dict(rec["i"]) for rec in sess.run(q, jur_name=jur_name) if rec["i"]]


# === 4. Get City-Wide Incidents ===
def get_city_incidents():
    q = """
    MATCH (i:Incident)
    WHERE i.city = 'Bengaluru'
    RETURN i
    """
    with driver.session() as sess:
        return [dict(rec["i"]) for rec in sess.run(q) if rec["i"]]


# === 5. Combined Lookup Driver ===
def lookup_incidents(lat, lng)->dict:
    jur = find_jurisdiction(lat, lng)
    if not jur:
        return {"error": "No matching jurisdiction"}

    jur_incidents = get_incidents_by_jurisdiction_name(jur["name"])
    if not jur_incidents:
        logging.warning(f"⚠️ No incidents in '{jur['name']}'")

    city_incidents = get_city_incidents()

    return {
        "jurisdiction_id": jur["id"],
        "jurisdiction_name": jur["name"],
        "jurisdiction_incidents": jur_incidents,
        "city_incidents": city_incidents
    }

def publish_single_event(event, source_label="jurisdiction",publisher=None, topic_path=None):
    message = {
        "source": source_label,
        "jurisdiction": event.get("jurisdiction", "Unknown"),
        "summary": event.get("summary", ""),
        "event_type": event.get("event_type", "other"),
        "published": event.get("published", ""),
        "score": event.get("score", 0),  # optional
        "lat": event.get("lat"),
        "lng": event.get("lng"),
        "id": event.get("id") or event.get("event_id") or None
    }

    try:
        payload = json.dumps(message).encode("utf-8")
        future = publisher.publish(topic_path, payload)
        msg_id = future.result()
        logging.info(f"✅ Published event to Pub/Sub [{source_label}] | MsgID: {msg_id}")
    except Exception as e:
        logging.error(f"❌ Failed to publish event: {e}")


if __name__ == "__main__":
    test_lat = 12.9127
    test_lng = 77.6228

    result = lookup_incidents(test_lat, test_lng)
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(GCP_PROJECT, PUBSUB_TOPIC)

    if "error" in result:
        print("❌ Error:", result["error"])
    else:
        print(f"\nJurisdiction: {result['jurisdiction_name']} (ID: {result['jurisdiction_id']})")
        print(f"→ {len(result['jurisdiction_incidents'])} local incidents")
        print(f"→ {len(result['city_incidents'])} city-wide incidents")
        print(result)
        for event in result["jurisdiction_incidents"]:
            publish_single_event(event, source_label="jurisdiction",publisher=publisher,topic_path=topic_path)

        for event in result["city_incidents"]:
            publish_single_event(event, source_label="citywide",publisher=publisher,topic_path=topic_path)
