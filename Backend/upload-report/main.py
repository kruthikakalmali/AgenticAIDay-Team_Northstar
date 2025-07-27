from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Form
from typing import List, Optional
from google.cloud import storage, firestore
import uuid
import os
import json
from fastapi import FastAPI, Query
from typing import List, Dict, Any
from google.cloud import firestore
import math


app = FastAPI()
BUCKET_NAME = os.environ.get("BUCKET_NAME", "nth-fort-466215-a3")
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)
db = firestore.Client()

@app.post("/report-incident")
async def report_incident(
    description: str = Form(...),
    event_type: str = Form(...),
    location: str = Form(...),
    timestamp: str = Form(...),
    images: Optional[List[UploadFile]] = File(None)
):
    report_id = str(uuid.uuid4())
    image_urls = []

    try:
        parsed_location = json.loads(location)  # parses JSON string to dict

        if images:
            for image in images:
                image.file.seek(0)
                blob = bucket.blob(f'incidents/{report_id}/{image.filename}')
                blob.upload_from_file(image.file, content_type=image.content_type)
                blob.make_public()
                image_urls.append(blob.public_url)

        db.collection("events").document(report_id).set({
            "description": description,
            "event_type": event_type,
            "lat": parsed_location.get("latitude"),
            "lng": parsed_location.get("longitude"),
            "timestamp": timestamp,
            "image_urls": image_urls,
            "report_id": report_id,
        })

        return {"status": "success", "report_id": report_id}

    except Exception as e:
        print("🚨 Error:", str(e))
        return {"status": "fail", "error": str(e)}
    



# @app.post("/report-incident")
# async def report_incident(
#     description: str = Form(...),
#     event_type: str = Form(...),
#     location: str = Form(...),
#     timestamp: str = Form(...),
#     images: Optional[List[UploadFile]] = File(None)
# ):
#     report_id = str(uuid.uuid4())
#     image_urls = []

#     try:
#         parsed_location = json.loads(location)  # parses JSON string to dict

#         if images:
#             for image in images:
#                 image.file.seek(0)
#                 blob = bucket.blob(f'incidents/{report_id}/{image.filename}')
#                 blob.upload_from_file(image.file, content_type=image.content_type)
#                 blob.make_public()
#                 image_urls.append(blob.public_url)

#         db.collection("events").document(report_id).set({
#             "description": description,
#             "event_type": event_type,
#             "location": parsed_location,
#             "timestamp": timestamp,
#             "image_urls": image_urls,
#             "report_id": report_id,
#         })

#         return {"status": "success", "report_id": report_id}

#     except Exception as e:
#         print("🚨 Error:", str(e))
#         return {"status": "fail", "error": str(e)}
    




def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c  # distance in kilometers

@app.get("/events-nearby")
async def get_events_nearby(
    latitude: float = Query(..., description="Your current latitude"),
    longitude: float = Query(..., description="Your current longitude")
) -> List[Dict[str, Any]]:
    try:
        events_ref = db.collection("events").stream()
        results_by_type = {}

        for doc in events_ref:
            data = doc.to_dict()
            event_lat = data.get("lat")
            event_lng = data.get("lng")

            if event_lat is not None and event_lng is not None:
                distance = haversine(latitude, longitude, event_lat, event_lng)
                if distance <= 50:
                    event_type = data.get("type", "unknown")
                    event_info = {
                        "datetime": data.get("datetime"),
                        "lat": event_lat,
                        "lng": event_lng,
                        "location": data.get("location"),
                        "link": data.get("link"),
                        "title": data.get("title"),
                        "type": event_type
                    }

                    if event_type not in results_by_type:
                        results_by_type[event_type] = []

                    results_by_type[event_type].append(event_info)

        response = [{"type": t, "events": evts} for t, evts in results_by_type.items()]
        return response

    except Exception as e:
        return {"status": "error", "message": str(e)}
