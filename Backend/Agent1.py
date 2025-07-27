
from neo4j import GraphDatabase
from xml.dom import minidom

# --- Neo4j Configuration ---
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# --- KML File Path ---
KML_FILE = "bengaluru-traffic-police.kml"  # Ensure this file is in the same directory

def extract_jurisdictions(kml_path):
    doc = minidom.parse(kml_path)
    placemarks = doc.getElementsByTagName('Placemark')
    jurisdictions = []
    for pm in placemarks:
        schema_data = pm.getElementsByTagName('SchemaData')
        props = {}
        if schema_data:
            for sd in schema_data[0].getElementsByTagName('SimpleData'):
                key = sd.getAttribute('name')
                val = sd.firstChild.nodeValue.strip() if sd.firstChild else None
                props[key] = val
        coords_text = ''
        polygon = pm.getElementsByTagName('coordinates')
        if polygon and polygon[0].firstChild:
            coords_text = polygon[0].firstChild.nodeValue.strip()
        coords = [
            [float(x), float(y)]
            for x, y, *_ in (point.split(',') for point in coords_text.split() if ',' in point)
        ]
        boundary_str = ', '.join(f"{lon} {lat}" for lon, lat in coords)
        jurisdiction = {
            "Traffic_PS": props.get("Traffic_PS"),
            "PS_BOUNDName": props.get("PS_BOUNDName"),
            "PS_BOUNDCode": props.get("PS_BOUNDCode"),
            "KGISPS_BOUNDID": props.get("KGISPS_BOUNDID"),
            "KGISPS_SUB_DIV_BOUNDID": props.get("KGISPS_SUB_DIV_BOUNDID"),
            "OBJECTID_12": props.get("OBJECTID_12"),
            "Shape_STArea__": float(props.get("Shape_STArea__")) if props.get("Shape_STArea__") else None,
            "Shape_STLength__": float(props.get("Shape_STLength__")) if props.get("Shape_STLength__") else None,
            "Date": props.get("Date"),
            "boundary": boundary_str
        }
        jurisdictions.append(jurisdiction)
    return jurisdictions

def create_jurisdiction(tx, data):
    tx.run("""
        MERGE (c:City {name: 'Bengaluru'})
        CREATE (j:TrafficJurisdiction {
            name: $Traffic_PS,
            ps_name: $PS_BOUNDName,
            code: $PS_BOUNDCode,
            kgis_id: $KGISPS_BOUNDID,
            sub_div_id: $KGISPS_SUB_DIV_BOUNDID,
            object_id: $OBJECTID_12,
            area: $Shape_STArea__,
            perimeter: $Shape_STLength__,
            date: $Date,
            boundary: $boundary
        })
        MERGE (j)-[:PART_OF]->(c)
    """, **data)

def main():
    jurisdictions = extract_jurisdictions(KML_FILE)
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        for j in jurisdictions:
            session.execute_write(create_jurisdiction, j)
    print(f"✅ Ingested {len(jurisdictions)} jurisdictions into Neo4j.")

if __name__ == "__main__":
    main()
