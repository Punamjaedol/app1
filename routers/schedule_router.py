from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import uuid

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
def add_schedule(data: ScheduleData, couple_id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    
    schedule_id = "s" + uuid.uuid4().hex[:8]
    cursor.execute('''
        INSERT INTO schedules (id, date, title, time, place_id, couple_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (schedule_id, data.date, data.title, data.time, data.placeId, couple_id))
    
    conn.commit()
    conn.close()
    
    return {"status": "ok", "id": schedule_id}

@router.get("/schedule/{date_str}")
def get_schedules_for_date(date_str: str, couple_id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM schedules WHERE date = ? AND couple_id = ?", (date_str, couple_id))
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
def generate_anniversaries(data: AnniversaryData, couple_id: str):
    """
    Given a start date, calculates 100, 200, 300 days and 1, 2 years.
    Automatically saves them as schedules.
    """
    start_dt = datetime.strptime(data.start_date, "%Y-%m-%d")
    
    anniversaries = [
        ("💖 100일 기념일!", timedelta(days=99)), 
        ("💖 200일 기념일!", timedelta(days=199)),
        ("💖 300일 기념일!", timedelta(days=299)),
        ("🎉 1주년!", timedelta(days=365)),
        ("🎉 2주년!", timedelta(days=730))
    ]
    
    conn = database.get_db()
    cursor = conn.cursor()
    
    saved_count = 0
    for title, delta in anniversaries:
        ann_date = start_dt + delta
        date_str = ann_date.strftime("%Y-%m-%d")
        
        # Check if already exists to prevent duplication
        cursor.execute("SELECT count(*) as count FROM schedules WHERE date = ? AND title = ? AND couple_id = ?", (date_str, title, couple_id))
        if cursor.fetchone()["count"] == 0:
            schedule_id = "s" + uuid.uuid4().hex[:8]
            cursor.execute('''
                INSERT INTO schedules (id, date, title, time, place_id, couple_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (schedule_id, date_str, title, "All Day", None, couple_id))
            saved_count += 1
            
    conn.commit()
    conn.close()
    
    return {"status": "ok", "message": f"{saved_count} anniversaries auto-generated."}

@router.get("/schedule/month/{year_month}")
def get_schedules_for_month(year_month: str, couple_id: str):
    """year_month: '2026-02' 형식"""
    conn = database.get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM schedules WHERE date LIKE ? AND couple_id = ?", (f"{year_month}%", couple_id))
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

@router.put("/schedule/{schedule_id}")
def update_schedule(schedule_id: str, data: ScheduleData, couple_id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE schedules 
        SET title = ?, time = ?, place_id = ?
        WHERE id = ? AND couple_id = ?
    ''', (data.title, data.time, data.placeId, schedule_id, couple_id))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Schedule not found")
        
    conn.commit()
    conn.close()
    return {"status": "ok"}

@router.delete("/schedule/{schedule_id}")
def delete_schedule(schedule_id: str, couple_id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM schedules WHERE id = ? AND couple_id = ?", (schedule_id, couple_id))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Schedule not found")
        
    conn.commit()
    conn.close()
    return {"status": "ok"}
