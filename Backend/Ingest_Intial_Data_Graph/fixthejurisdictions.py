
import json
import time
from pathlib import Path
from neo4j import GraphDatabase
from vertexai.preview.generative_models import GenerativeModel
import vertexai
import os
# === CONFIGURATION ===
KML_PATH = "bengaluru-traffic-police.kml"
PROJECT_ID = os.getenv("GCP_PROJECT", "your-gcp-project-id")
LOCATION = "us-central1"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
MODEL = "gemini-2.0-flash-001"
RETRY_LIMIT = 3
# =======================

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)
model = GenerativeModel(MODEL)

def extract_kml_sample(path, max_lines=40):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return ''.join(f.readlines()[:max_lines])

def build_prompt(sample_text):
    return f"""
You are a civic data intelligence agent. The goal is to analyze semantic structure in datasets collected for a real-time urban monitoring agent in Indian cities like Bengaluru.

This file is a KML dataset likely containing traffic police jurisdiction information. You are to extract the underlying knowledge schema — entities and relationships — that this dataset contributes to a Neo4j graph.

### SAMPLE CONTENT:

{sample_text}

### TASK:
1. What entities are present?
2. What relationships exist between them?
3. Generate a clean JSON schema to define:
   - Nodes (labels and property names)
   - Relationships (type, from, to)

### CONTEXT:
This schema is the foundation of a knowledge graph for Bengaluru’s traffic and civic infrastructure. Normalize location-related entities. Do not create redundant entities.

### OUTPUT FORMAT:
```json
{{
  "entities": [
    {{
      "label": "EntityLabel",
      "properties": ["prop1", "prop2"]
    }}
  ],
  "relationships": [
    {{
      "type": "REL_TYPE",
      "from": "EntityLabel1",
      "to": "EntityLabel2"
    }}
  ]
}}
```
"""

def call_gemini(prompt, retry=0):
    try:
        response = model.generate_content(prompt)
        text = response.text.strip("```json").strip("```").strip()
        return json.loads(text)
    except Exception as e:
        if "429" in str(e) and retry < RETRY_LIMIT:
            wait = 2 ** retry
            print(f"⚠️ Rate limit hit, retrying in {wait}s...")
            time.sleep(wait)
            return call_gemini(prompt, retry + 1)
        raise RuntimeError(f"Gemini error: {e}")

def format_props(props):
    return ", ".join([f"{k}: ${k}" for k in props])

def ingest_to_neo4j(schema):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        # Create nodes
        for entity in schema.get("entities", []):
            label = entity["label"]
            props = {p: f"<{p}>" for p in entity.get("properties", [])}
            if not props:
                continue
            cypher = f"MERGE (n:{label} {{ name: $name }}) SET n += {{ {format_props(props)} }}"
            if "name" not in props:
                props["name"] = label
            session.run(cypher, **props)

        # Create relationships
        for rel in schema.get("relationships", []):
            from_label = rel["from"]
            to_label = rel["to"]
            rel_type = rel["type"]
            cypher = f"""
            MATCH (a:{from_label}), (b:{to_label})
            WHERE a.name IS NOT NULL AND b.name IS NOT NULL
            MERGE (a)-[r:{rel_type}]->(b)
            """
            session.run(cypher)

    driver.close()
    print("✅ Ingestion complete!")

# === MAIN EXECUTION ===
if __name__ == "__main__":
    print(f"📄 Reading {KML_PATH}...")
    sample = extract_kml_sample(KML_PATH)
    prompt = build_prompt(sample)
    print("🤖 Generating schema from Gemini...")
    schema = call_gemini(prompt)
    print("📊 Schema generated. Ingesting into Neo4j...")
    ingest_to_neo4j(schema)
