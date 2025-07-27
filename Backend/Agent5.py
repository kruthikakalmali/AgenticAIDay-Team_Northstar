import json
import logging
from py2neo import Graph, Node, Relationship
import os
# CONFIG
INPUT_FILE = "bengaluru_events_24h1.json"
# NEO4J_URI = "bolt://localhost:7687"
# NEO4J_USER = "neo4j"
# NEO4J_PASSWORD = "password"
CITY_NAME = "Bengaluru"
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

logging.basicConfig(level=logging.INFO)
graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def ensure_city():
    city = graph.nodes.match("City", name=CITY_NAME).first()
    if not city:
        city = Node("City", name=CITY_NAME)
        graph.create(city)
    return city

def ensure_jurisdiction(jname, city_node):
    jur = graph.nodes.match("TrafficJurisdiction", name=jname).first()
    if not jur:
        jur = Node("TrafficJurisdiction", name=jname)
        graph.create(jur)
        graph.create(Relationship(jur, "PART_OF", city_node))
    return jur

def ensure_container(jurisdiction):
    container = graph.nodes.match("Incidents", jurisdiction=jurisdiction).first()
    if not container:
        container = Node("Incidents", jurisdiction=jurisdiction)
        graph.create(container)
    return container

def link_container(holder, container):
    rel = Relationship(holder, "HAS_CONTAINER", container)
    graph.merge(rel)

def insert_incident(event, container_node):
    incident = Node("Incident", **event)
    graph.create(incident)
    graph.create(Relationship(container_node, "HAS_INCIDENT", incident))

def ingest():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        events = json.load(f)

    city = ensure_city()

    for event in events:
        jurisdiction = event.get("jurisdiction") or "Unknown"
        jurisdiction = jurisdiction.strip()
        event["jurisdiction"] = jurisdiction

        if jurisdiction == "Unknown":
            container = ensure_container("Unknown")
            link_container(city, container)
        else:
            jur_node = ensure_jurisdiction(jurisdiction, city)
            container = ensure_container(jurisdiction)
            link_container(jur_node, container)

        insert_incident(event, container)
        logging.info(f"Inserted: {event['id']} into {jurisdiction}")

    logging.info("✅ Done. All events inserted.")

def ingestevents(events: list[dict]):
    # with open(INPUT_FILE, "r", encoding="utf-8") as f:
    #     events = json.load(f)

    city = ensure_city()

    for event in events:
        jurisdiction = event.get("jurisdiction") or "Unknown"
        jurisdiction = jurisdiction.strip()
        event["jurisdiction"] = jurisdiction

        if jurisdiction == "Unknown":
            container = ensure_container("Unknown")
            link_container(city, container)
        else:
            jur_node = ensure_jurisdiction(jurisdiction, city)
            container = ensure_container(jurisdiction)
            link_container(jur_node, container)

        insert_incident(event, container)
        logging.info(f"Inserted: {event['id']} into {jurisdiction}")

    logging.info("✅ Done. All events inserted.")
if __name__ == "__main__":
    ingest()
