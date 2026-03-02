from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import get_db

router = APIRouter()

class CoupleInfoUpdate(BaseModel):
    start_date: str

class ProfileUpdate(BaseModel):
    name: str = ""
    birthday: str = ""

@router.get("/couple/info")
def get_couple_info(couple_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT start_date FROM couple_info WHERE couple_id = ?", (couple_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"couple_id": couple_id, "start_date": row["start_date"]}
    else:
        return {"couple_id": couple_id, "start_date": None}

@router.post("/couple/info")
def update_couple_info(couple_id: str, info: CoupleInfoUpdate):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO couple_info (couple_id, start_date)
        VALUES (?, ?)
    ''', (couple_id, info.start_date))
    
    conn.commit()
    conn.close()
    return {"message": "Couple information updated successfully"}

@router.get("/couple/profile")
def get_profile(couple_id: str, username: str):
    """Get profile info for current user and partner."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get current user
    cursor.execute("SELECT username, name, birthday FROM users WHERE username = ? AND couple_id = ?", (username, couple_id))
    me = cursor.fetchone()
    
    if not me:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get partner (other user with same couple_id)
    cursor.execute("SELECT username, name, birthday FROM users WHERE couple_id = ? AND username != ?", (couple_id, username))
    partner = cursor.fetchone()
    
    # Get couple start date
    cursor.execute("SELECT start_date FROM couple_info WHERE couple_id = ?", (couple_id,))
    couple_info = cursor.fetchone()
    conn.close()
    
    start_date = couple_info["start_date"] if couple_info else None
    d_day = None
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            start = start.replace(hour=0, minute=0, second=0)
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            d_day = (today - start).days + 1
        except ValueError:
            pass
    
    result = {
        "me": {
            "username": me["username"],
            "name": me["name"] or "",
            "birthday": me["birthday"] or ""
        },
        "partner": None,
        "start_date": start_date,
        "d_day": d_day
    }
    
    if partner:
        result["partner"] = {
            "username": partner["username"],
            "name": partner["name"] or "",
            "birthday": partner["birthday"] or ""
        }
    
    return result

@router.post("/couple/profile")
def update_profile(couple_id: str, username: str, data: ProfileUpdate):
    """Update current user's name and birthday."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET name = ?, birthday = ? WHERE username = ? AND couple_id = ?",
        (data.name, data.birthday, username, couple_id)
    )
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Profile updated"}
