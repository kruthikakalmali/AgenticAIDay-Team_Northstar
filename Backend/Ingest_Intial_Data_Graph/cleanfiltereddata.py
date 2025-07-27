import os
import shutil

# Path to the filtered data directory
FILTERED_DATA_PATH = "./filtered_data"

# Keywords that indicate unnecessary folders
exclusion_keywords = [
    "budget", "speech", "manifesto", "agenda", "policy", "plan", "vision", "rmp",
    "zoning", "masterplan", "framework", "committee_report", "meeting", "minutes",
    "revised", "guideline", "bye-law", "notification", "amendment", "gazette",
    "mp_and_mla", "blueprint", "governance", "development_taskforce", "strategy", "election","tax"
]

def should_exclude(folder_name):
    folder = folder_name.lower()
    return any(keyword in folder for keyword in exclusion_keywords)

def remove_excluded_folders(root_path):
    removed = []
    for folder in os.listdir(root_path):
        folder_path = os.path.join(root_path, folder)
        if os.path.isdir(folder_path) and should_exclude(folder):
            shutil.rmtree(folder_path)
            removed.append(folder)
    return removed

if __name__ == "__main__":
    deleted = remove_excluded_folders(FILTERED_DATA_PATH)
    print(f"🧹 Removed {len(deleted)} folders:")
    for folder in deleted:
        print(f" - {folder}")
