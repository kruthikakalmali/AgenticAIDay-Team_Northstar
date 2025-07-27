import xml.etree.ElementTree as ET
import pandas as pd
from shapely.geometry import Polygon
from py2neo import Graph, Node, Relationship
import os
# === Config ===
WARD_KML_PATH = "bbmp_final_new_wards.kml"
WARD_MAPPING_CSV = "ward_to_traffic_jurisdiction.csv"
# NEO4J_URI = "bolt://localhost:7687"
# NEO4J_USER = "neo4j"
# NEO4J_PASSWORD = "password"
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# === Parse ward KML and extract properties ===
def extract_wards_with_properties(kml_path):
    tree = ET.parse(kml_path)
    root = tree.getroot()
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}

    wards = []

    for placemark in root.findall('.//kml:Placemark', ns):
        props = {}
        for data in placemark.findall('.//kml:SimpleData', ns):
            key = data.attrib.get('name')
            if key:
                props[key] = data.text

        coords_elem = placemark.find('.//kml:coordinates', ns)
        if coords_elem is None:
            continue

        coords_text = coords_elem.text.strip()
        coord_pairs = [
            tuple(map(float, coord.strip().split(',')[:2]))
            for coord in coords_text.split()
        ]
        if len(coord_pairs) < 3:
            continue

        polygon = Polygon(coord_pairs)
        props["geometry_wkt"] = polygon.wkt  # Optional: Store geometry
        wards.append(props)

    return wards

# === Main Logic ===
def main():
    # Load mapping CSV
    mapping_df = pd.read_csv(WARD_MAPPING_CSV)
    mapping_dict = dict(zip(mapping_df["Ward"], mapping_df["Assigned_Jurisdiction"]))

    # Load ward data with all properties
    wards = extract_wards_with_properties(WARD_KML_PATH)

    # Connect to Neo4j
    graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # Create nodes and relationships
    for ward in wards:
        ward_name = ward.get("proposed_ward_name_en")
        if not ward_name:
            continue

        jurisdiction_name = mapping_dict.get(ward_name)
        if not jurisdiction_name:
            print(f"⚠️ No jurisdiction mapping found for ward: {ward_name}")
            continue

        # Create/merge Ward node with all its properties
        ward_node = Node("Ward", name=ward_name, **ward)

        # Ensure Jurisdiction node exists
        jurisdiction_node = graph.nodes.match("TrafficJurisdiction", name=jurisdiction_name).first()
        if not jurisdiction_node:
            jurisdiction_node = Node("TrafficJurisdiction", name=jurisdiction_name)
            graph.create(jurisdiction_node)

        # Merge and relate
        graph.merge(ward_node, "Ward", "name")
        rel = Relationship(ward_node, "BELONGS_TO", jurisdiction_node)
        graph.merge(rel)

    print("✅ Wards and BELONGS_TO relationships loaded into Neo4j.")

if __name__ == "__main__":
    main()
