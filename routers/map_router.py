import uuid
from datetime import datetime, timezone
import math
from fastapi import APIRouter
from pydantic import BaseModel

import database
from services.kakao_service import reverse_geocode_kakao

router = APIRouter()

class LocationData(BaseModel):
    lat: float
    lng: float

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two GPS coordinates using Haversine formula"""
    R = 6371000 # Radius of earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

@router.post("/location")
async def update_location(data: LocationData):
    """
    Receives current GPS coordinates and checks Dwell Time.
    """
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()
    
    conn = database.get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tracking_sessions WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    session = cursor.fetchone()
    
    response_msg = "Location updated."
    place_tagged = None
    
    if not session:
        cursor.execute('''
            INSERT INTO tracking_sessions (start_lat, start_lng, start_time, last_update_time, is_active)
            VALUES (?, ?, ?, ?, 1)
        ''', (data.lat, data.lng, now_str, now_str))
        response_msg = "Started new tracking session."
    else:
        dist = calculate_distance(data.lat, data.lng, session["start_lat"], session["start_lng"])
        start_time = datetime.fromisoformat(session["start_time"])
        time_diff = (now - start_time).total_seconds()
        
        if dist > 50:
            cursor.execute("UPDATE tracking_sessions SET is_active = 0 WHERE id = ?", (session["id"],))
            cursor.execute('''
                INSERT INTO tracking_sessions (start_lat, start_lng, start_time, last_update_time, is_active)
                VALUES (?, ?, ?, ?, 1)
            ''', (data.lat, data.lng, now_str, now_str))
            
            response_msg = f"User moved {dist:.1f}m. Tracking reset."
        else:
            if time_diff >= 10:
                name, addr = await reverse_geocode_kakao(session["start_lat"], session["start_lng"])
                
                cursor.execute("SELECT name FROM places ORDER BY timestamp DESC LIMIT 1")
                last_place = cursor.fetchone()
                
                cursor.execute("UPDATE tracking_sessions SET is_active = 0 WHERE id = ?", (session["id"],))
                
                if last_place and last_place["name"] == name:
                    response_msg = f"Stayed >10s, but ignored duplicate place: {name}"
                else:
                    place_id = "p" + str(uuid.uuid4())[:8]
                    cursor.execute('''
                        INSERT INTO places (id, name, lat, lng, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (place_id, name, session["start_lat"], session["start_lng"], now_str))
                    
                    response_msg = f"Place auto-tagged via Kakao API after {time_diff:.1f}s!"
                    place_tagged = {
                        "id": place_id,
                        "name": name,
                        "address": addr,
                        "lat": session["start_lat"],
                        "lng": session["start_lng"],
                        "timestamp": now_str
                    }
            else:
                cursor.execute("UPDATE tracking_sessions SET last_update_time = ? WHERE id = ?", (now_str, session["id"]))
                response_msg = f"User staying. Time elapsed: {time_diff:.1f}s (needs 10s)"
    
    conn.commit()
    conn.close()
    
    return {"status": "ok", "message": response_msg, "place_tagged": place_tagged}

@router.delete("/places/{place_id}")
def delete_place(place_id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM places WHERE id = ?", (place_id,))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Place deleted."}

@router.get("/timeline")
def get_timeline():
    """Returns successfully tagged places, ordered by newest first."""
    conn = database.get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM places ORDER BY timestamp DESC")
    places = cursor.fetchall()
    
    conn.close()
    return [dict(p) for p in places]
