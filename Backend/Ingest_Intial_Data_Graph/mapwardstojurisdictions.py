import xml.etree.ElementTree as ET
from shapely.geometry import Polygon
import pandas as pd

def extract_polygons_from_kml(file_path, field_name):
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    polygons = []

    for placemark in root.findall('.//kml:Placemark', ns):
        name = None
        for data in placemark.findall('.//kml:SimpleData', ns):
            if data.attrib.get('name') == field_name:
                name = data.text
                break

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
        polygons.append({'name': name, 'geometry': polygon})

    return polygons

def map_wards_to_jurisdictions(ward_polygons, jurisdiction_polygons):
    results = []
    for ward in ward_polygons:
        ward_center = ward['geometry'].centroid
        matched_jurisdiction = None
        for juris in jurisdiction_polygons:
            if juris['geometry'].contains(ward_center):
                matched_jurisdiction = juris['name']
                break
        results.append({
            "Ward": ward['name'],
            "Assigned_Jurisdiction": matched_jurisdiction
        })
    return results

if __name__ == "__main__":
    # === FILE PATHS ===
    ward_file = "bbmp_final_new_wards.kml"
    jurisdiction_file = "bengaluru-traffic-police.kml"

    # === FIELD NAMES FROM KML ===
    ward_field = "proposed_ward_name_en"
    jurisdiction_field = "Traffic_PS"

    # === Parse and map ===
    wards = extract_polygons_from_kml(ward_file, ward_field)
    jurisdictions = extract_polygons_from_kml(jurisdiction_file, jurisdiction_field)
    mapping = map_wards_to_jurisdictions(wards, jurisdictions)

    # === Output to CSV ===
    df = pd.DataFrame(mapping)
    df.to_csv("ward_to_traffic_jurisdiction.csv", index=False)
    print("✅ Mapping CSV generated: ward_to_traffic_jurisdiction.csv")
