from fastapi import APIRouter, HTTPException, Query
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
    description: str = ""
    isAnnual: bool = False

class AnniversaryData(BaseModel):
    start_date: str

@router.post("/schedule")
def add_schedule(data: ScheduleData, couple_id: str = Query(...)):
    conn = database.get_db()
    cursor = conn.cursor()
    
    schedule_id = "s" + uuid.uuid4().hex[:8]
    cursor.execute('''
        INSERT INTO schedules (id, date, title, time, place_id, couple_id, description, is_annual)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (schedule_id, data.date, data.title, data.time, data.placeId, couple_id, data.description, 1 if data.isAnnual else 0))
    
    conn.commit()
    conn.close()
    
    return {"status": "ok", "id": schedule_id}

@router.get("/schedule/{date_str}")
def get_schedules_for_date(date_str: str, couple_id: str = Query(...)):
    conn = database.get_db()
    cursor = conn.cursor()
    
    # Get exact date schedules
    cursor.execute("SELECT * FROM schedules WHERE date = ? AND couple_id = ?", (date_str, couple_id))
    schedules = list(cursor.fetchall())
    
    # Inject annual schedules from other years with matching month-day
    month_day = date_str[5:]  # 'MM-DD'
    cursor.execute(
        "SELECT * FROM schedules WHERE couple_id = ? AND is_annual = 1 AND date != ? AND substr(date, 6) = ?",
        (couple_id, date_str, month_day)
    )
    annual_schedules = cursor.fetchall()
    schedules.extend(annual_schedules)

    # 3. Dynamic Couple Anniversary Injection
    cursor.execute("SELECT start_date FROM couple_info WHERE couple_id = ?", (couple_id,))
    couple_info = cursor.fetchone()
    if couple_info and couple_info["start_date"]:
        start_date = couple_info["start_date"]
        if start_date[5:] == date_str[5:]: # MM-DD matches
            start_year = int(start_date[:4])
            curr_year = int(date_str[:4])
            years = curr_year - start_year
            if years > 0:
                schedules.append({
                    "id": f"anniv_{years}y",
                    "date": date_str,
                    "title": f"🎉 {years}주년!",
                    "time": "종일",
                    "place_id": None,
                    "couple_id": couple_id,
                    "description": "",
                    "is_annual": 0
                })

    # 4. Dynamic Birthday Injection
    cursor.execute("SELECT name, birthday FROM users WHERE couple_id = ?", (couple_id,))
    users = cursor.fetchall()
    for u in users:
        bday = u["birthday"]
        if bday and bday[5:] == date_str[5:]: # MM-DD matches
            schedules.append({
                "id": f"bday_{u['name']}",
                "date": date_str,
                "title": f"{u['name']} 생일 🎂",
                "time": "종일",
                "place_id": None,
                "couple_id": couple_id,
                "description": "",
                "is_annual": 0
            })

    conn.close()
    
    result = []
    for s in schedules:
        result.append({
            "id": s["id"],
            "title": s["title"],
            "time": s["time"],
            "placeId": s["place_id"],
            "description": s["description"] or "",
            "isAnnual": bool(s["is_annual"])
        })
    return result

@router.post("/anniversary")
def generate_anniversaries(data: AnniversaryData, couple_id: str = Query(...)):
    """
    Saves start_date and calculates 100, 200, 300 days.
    """
    start_dt = datetime.strptime(data.start_date, "%Y-%m-%d")
    
    conn = database.get_db()
    cursor = conn.cursor()

    # 1. Update couple_info
    cursor.execute('''
        INSERT OR REPLACE INTO couple_info (couple_id, start_date)
        VALUES (?, ?)
    ''', (couple_id, data.start_date))
    
    # 2. Clear old day-based anniversaries
    # We match "💖 %일 기념일!" to clear them
    cursor.execute(
        "DELETE FROM schedules WHERE couple_id = ? AND title LIKE '💖 %일 기념일!'",
        (couple_id,)
    )

    # 3. Calculate and save new ones (100, 200, 300 days)
    saved_count = 0
    for days in [100, 200, 300]:
        ann_date = start_dt + timedelta(days=days-1)
        date_str = ann_date.strftime("%Y-%m-%d")
        title = f"💖 {days}일 기념일!"
        
        schedule_id = "s" + uuid.uuid4().hex[:8]
        cursor.execute('''
            INSERT INTO schedules (id, date, title, time, place_id, couple_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (schedule_id, date_str, title, "종일", None, couple_id))
        saved_count += 1
            
    conn.commit()
    conn.close()
    
    return {"status": "ok", "message": f"{saved_count} day-anniversaries generated. Yearly anniversaries are now dynamic."}

@router.get("/schedule/month/{year_month}")
def get_schedules_for_month(year_month: str, couple_id: str):
    """year_month: '2026-02' 형식"""
    conn = database.get_db()
    cursor = conn.cursor()
    
    # Get exact month schedules
    cursor.execute("SELECT * FROM schedules WHERE date LIKE ? AND couple_id = ?", (f"{year_month}%", couple_id))
    schedules = list(cursor.fetchall())
    
    # Inject annual schedules from other years with matching month
    target_month = year_month[5:]  # 'MM'
    target_year = year_month[:4]
    cursor.execute(
        "SELECT * FROM schedules WHERE couple_id = ? AND is_annual = 1 AND substr(date, 1, 4) != ? AND substr(date, 6, 2) = ?",
        (couple_id, target_year, target_month)
    )
    annual_schedules = cursor.fetchall()
    schedules = [dict(s) for s in schedules]
    annual_schedules = [dict(s) for s in annual_schedules]
    schedules.extend(annual_schedules)

    # 3. Dynamic Couple Anniversary Injection
    cursor.execute("SELECT start_date FROM couple_info WHERE couple_id = ?", (couple_id,))
    couple_info = cursor.fetchone()
    if couple_info and couple_info["start_date"]:
        start_date = couple_info["start_date"]
        start_month = start_date[5:7]
        if start_month == target_month:
            start_year = int(start_date[:4])
            curr_year = int(target_year)
            years = curr_year - start_year
            if years > 0:
                ann_day = start_date[8:10]
                # Check for leap year Feb 29 -> 28
                if start_month == "02" and ann_day == "29":
                    try:
                        datetime(curr_year, 2, 29)
                    except ValueError:
                        ann_day = "28"
                
                schedules.append({
                    "id": f"anniv_{years}y",
                    "date": f"{target_year}-{start_month}-{ann_day}",
                    "title": f"🎉 {years}주년!",
                    "time": "종일",
                    "place_id": None,
                    "couple_id": couple_id,
                    "description": "",
                    "is_annual": 0
                })
    
    # 4. Dynamic Birthday Injection
    cursor.execute("SELECT name, birthday FROM users WHERE couple_id = ?", (couple_id,))
    users = cursor.fetchall()
    for u in users:
        bday = u["birthday"]
        if bday and bday[5:7] == target_month:
            b_day = bday[8:10]
            # Handle leap year birthday Feb 29
            if bday[5:7] == "02" and b_day == "29":
                try:
                    datetime(int(target_year), 2, 29)
                except ValueError:
                    b_day = "28"
            
            schedules.append({
                "id": f"bday_{u['name']}",
                "date": f"{target_year}-{target_month}-{b_day}",
                "title": f"{u['name']} 생일 🎂",
                "time": "종일",
                "place_id": None,
                "couple_id": couple_id,
                "description": "",
                "is_annual": 0
            })
    
    conn.close()
    
    result = {}
    for s in schedules:
        # Safety: convert to dict if not already
        if not isinstance(s, dict):
            s = dict(s)
            
        date = s.get("date")
        if not date:
            continue
            
        # For annual schedules from other years, map to current year-month
        if s.get("is_annual") and not date.startswith(target_year):
            date = f"{target_year}-{date[5:]}"  # Remap to current year
            
        if date not in result:
            result[date] = []
        result[date].append({
            "id": s["id"],
            "title": s["title"],
            "time": s["time"],
            "placeId": s["place_id"],
            "description": s["description"] or "",
            "isAnnual": bool(s["is_annual"])
        })
    return result

@router.put("/schedule/{schedule_id}")
def update_schedule(schedule_id: str, data: ScheduleData, couple_id: str):
    conn = database.get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE schedules 
        SET title = ?, time = ?, place_id = ?, description = ?, is_annual = ?
        WHERE id = ? AND couple_id = ?
    ''', (data.title, data.time, data.placeId, data.description, 1 if data.isAnnual else 0, schedule_id, couple_id))
    
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
