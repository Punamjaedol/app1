import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

import database

router = APIRouter()

class ScheduleData(BaseModel):
    date: str
    title: str
    time: str = ""
    placeId: Optional[str] = None

class AnniversaryData(BaseModel):
    start_date: str

@router.post("/schedule")
def add_schedule(data: ScheduleData):
    conn = database.get_db()
    cursor = conn.cursor()
    
    schedule_id = "s" + str(uuid.uuid4())[:8]
    cursor.execute('''
        INSERT INTO schedules (id, date, title, time, place_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (schedule_id, data.date, data.title, data.time, data.placeId))
    
    conn.commit()
    conn.close()
    
    return {"status": "ok", "id": schedule_id}

@router.get("/schedule/{date_str}")
def get_schedules_for_date(date_str: str):
    conn = database.get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM schedules WHERE date = ?", (date_str,))
    schedules = cursor.fetchall()
    
    conn.close()
    
    result = []
    for s in schedules:
        result.append({
            "id": s["id"],
            "title": s["title"],
            "time": s["time"],
            "placeId": s["place_id"]
        })
    return result

@router.post("/anniversary")
def generate_anniversaries(data: AnniversaryData):
    """
    Given a start date, calculates 100, 200, 300 days and 1, 2 years.
    Automatically saves them as schedules.
    """
    start_dt = datetime.strptime(data.start_date, "%Y-%m-%d")
    
    anniversaries = [
        ("💖 100일 기념일!", timedelta(days=99)), # +99 days since day 1 counts
        ("💖 200일 기념일!", timedelta(days=199)),
        ("💖 300일 기념일!", timedelta(days=299)),
        ("🎉 1주년!", timedelta(days=365)),
        ("🎉 2주년!", timedelta(days=730)) # Roughly 2 years ignoring leap exactly
    ]
    
    conn = database.get_db()
    cursor = conn.cursor()
    
    saved_count = 0
    for title, delta in anniversaries:
        ann_date = start_dt + delta
        date_str = ann_date.strftime("%Y-%m-%d")
        
        # Check if already exists to prevent duplication
        cursor.execute("SELECT count(*) as count FROM schedules WHERE date = ? AND title = ?", (date_str, title))
        if cursor.fetchone()["count"] == 0:
            schedule_id = "s" + str(uuid.uuid4())[:8]
            cursor.execute('''
                INSERT INTO schedules (id, date, title, time, place_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (schedule_id, date_str, title, "All Day", None))
            saved_count += 1
            
    conn.commit()
    conn.close()
    
    return {"status": "ok", "message": f"{saved_count} anniversaries auto-generated."}

@router.get("/schedule/month/{year_month}")
def get_schedules_for_month(year_month: str):
    """year_month: '2026-02' 형식"""
    conn = database.get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM schedules WHERE date LIKE ?", (f"{year_month}%",))
    schedules = cursor.fetchall()
    conn.close()
    
    result = {}
    for s in schedules:
        date = s["date"]
        if date not in result:
            result[date] = []
        result[date].append({
            "id": s["id"],
            "title": s["title"],
            "time": s["time"],
            "placeId": s["place_id"]
        })
    return result