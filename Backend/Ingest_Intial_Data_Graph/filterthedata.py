import os
import shutil

# Set your dataset root
SOURCE_FOLDER = "./data"
OUTPUT_FOLDER = "./filtered_data"

# Add more terms based on future use case extensions
KEEP_KEYWORDS = [
    "waste", "swm", "garbage", "pollution", "air", "water", "lake",
    "drain", "stormwater", "traffic", "mobility", "road", "accident",
    "transport", "bus", "metro", "rail", "cctv", "violation", "vehicle",
    "ward", "committee", "grievance", "property", "tax", "complaint",
    "school", "college", "education", "hospital", "toilet", "fire", "police",
    "crime", "safety", "dogs", "stray", "slum", "housing", "shelter",
    "rainfall", "groundwater", "waterbody", "tank", "reservoir", "sewage",
    "underpass", "intersection", "flyover", "streetlight", "pothole",
    "parks", "playground", "facility", "infrastructure"
]

# Lowercase keywords for case-insensitive match
KEEP_KEYWORDS = [k.lower() for k in KEEP_KEYWORDS]

def is_relevant_folder(folder_name):
    return any(kw in folder_name.lower() for kw in KEEP_KEYWORDS)

def filter_folders():
    if not os.path.exists(SOURCE_FOLDER):
        print(f"❌ Source folder '{SOURCE_FOLDER}' does not exist.")
        return

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    all_folders = os.listdir(SOURCE_FOLDER)
    kept = 0

    for folder in all_folders:
        full_path = os.path.join(SOURCE_FOLDER, folder)
        if os.path.isdir(full_path) and is_relevant_folder(folder):
            dest_path = os.path.join(OUTPUT_FOLDER, folder)
            shutil.copytree(full_path, dest_path, dirs_exist_ok=True)
            kept += 1
            print(f"✅ Kept: {folder}")

    print(f"\n✅ Done. Kept {kept}/{len(all_folders)} folders in '{OUTPUT_FOLDER}'.")

if __name__ == "__main__":
    filter_folders()
