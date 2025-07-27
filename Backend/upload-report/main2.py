from fastapi import FastAPI, UploadFile, File, Form
from typing import List, Optional
from google.cloud import storage, firestore
from google.oauth2 import service_account
import uuid
import os
import json
import base64
import requests

app = FastAPI()

# Google Cloud Setup
BUCKET_NAME = os.environ.get("BUCKET_NAME", "nth-fort-466215-a3")
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)
db = firestore.Client()

# Gemini API Setup
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

def call_gemini_vision(base64_image: str) -> dict:
    """Send the image to Gemini multimodal and return structured summary"""
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",  # Assuming JPEG, adjust if needed
                            "data": base64_image
                        }
                    },
                    {
                        "text": "What incident does this image show? Describe the situation, categorize the event type (e.g., fire, protest, accident), and give a short summary."
                    }
                ]
            }
        ]
    }
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        raise  # Re-raise the exception to be handled by the caller

@app.post("/report-incident")
async def report_incident(
    location: str = Form(...),
    timestamp: str = Form(...),
    images: Optional[List[UploadFile]] = File(None)
):
    report_id = str(uuid.uuid4())
    image_urls = []
    description = "N/A"
    event_type = "unknown"

    try:
        parsed_location = json.loads(location)

        if not images:
            return {"status": "fail", "error": "At least one image is required."}

        # Process only the first image for analysis
        first_image = images[0]

        # Upload image to Google Cloud Storage
        blob = bucket.blob(f'incidents/{report_id}/{first_image.filename}')
        first_image.file.seek(0)  # Reset before upload
        blob = bucket.blob(f'incidents/{report_id}/{first_image.filename}')
        blob.upload_from_file(first_image.file, content_type=first_image.content_type)
        blob.make_public()
        image_url = blob.public_url
        image_urls.append(image_url)

        # await blob.upload_from_file(first_image.file, content_type=first_image.content_type)
        # await blob.make_public()
        # image_url = blob.public_url
        # image_urls.append(image_url)

        # Reset file pointer for reading image bytes for Gemini
        first_image.file.seek(0)
        image_bytes = first_image.file.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Call Gemini Vision
        gemini_result = call_gemini_vision(base64_image)

        if gemini_result and "candidates" in gemini_result and gemini_result["candidates"]:
            if gemini_result["candidates"][0]["content"]["parts"]:
                text = gemini_result["candidates"][0]["content"]["parts"][0]["text"]
                # Improved parsing of Gemini's response
                lines = text.strip().split('\n')
                description_parts = []
                for line in lines:
                    lower_line = line.lower()
                    if lower_line.startswith("description:"):
                        description_parts.append(line.split(":", 1)[1].strip())
                    elif lower_line.startswith("event type:"):
                        event_type = line.split(":", 1)[1].strip().lower()
                        # Normalize common variations
                        if event_type in ["fire", "fires"]:
                            event_type = "fire"
                        elif event_type in ["protest", "protests", "demonstration"]:
                            event_type = "protest"
                        elif event_type in ["accident", "car accident", "vehicle accident"]:
                            event_type = "accident"
                        else:
                            event_type = "other" # Default for unclassified
                    else:
                        # Assume general description parts if not specifically labeled
                        description_parts.append(line.strip())

                description = " ".join(description_parts)
                # Fallback for event type if Gemini didn't explicitly classify
                if event_type == "unknown" or event_type == "other":
                    if "fire" in description.lower():
                        event_type = "fire"
                    elif "protest" in description.lower():
                        event_type = "protest"
                    elif "accident" in description.lower() or "crash" in description.lower():
                        event_type = "accident"
                    else:
                        event_type = "general" # A catch-all if still no category

            else:
                description = "Gemini API did not return any text content."
        else:
            description = "Gemini API did not return expected candidates."
            print(f"Unexpected Gemini response structure: {gemini_result}")


        # Save to Firestore
        doc_ref = db.collection("events").document(report_id)
        doc_ref.set({
            "description": description,
            "event_type": event_type,
            "lat": parsed_location.get("latitude"),
            "lng": parsed_location.get("longitude"),
            "timestamp": timestamp,
            "image_urls": image_urls,
            "report_id": report_id,
        })

        return {"status": "success", "report_id": report_id, "event_type": event_type, "description": description, "image_urls": image_urls}

    except json.JSONDecodeError:
        print("🚨 Error: Invalid JSON format for location.")
        return {"status": "fail", "error": "Invalid JSON format for location."}
    except requests.exceptions.RequestException as e:
        print(f"🚨 Error communicating with Gemini API: {e}")
        return {"status": "fail", "error": f"Gemini API error: {e}"}
    except Exception as e:
        print(f"🚨 An unexpected error occurred: {e}")
        return {"status": "fail", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)