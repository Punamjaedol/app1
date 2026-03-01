from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db

router = APIRouter()

class CoupleInfoUpdate(BaseModel):
    start_date: str

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
        # Return empty/default if not set
        return {"couple_id": couple_id, "start_date": None}

@router.post("/couple/info")
def update_couple_info(couple_id: str, info: CoupleInfoUpdate):
    conn = get_db()
    cursor = conn.cursor()
    
    # Use REPLACE INTO for SQLite Upsert
    cursor.execute('''
        INSERT OR REPLACE INTO couple_info (couple_id, start_date)
        VALUES (?, ?)
    ''', (couple_id, info.start_date))
    
    conn.commit()
    conn.close()
    return {"message": "Couple information updated successfully"}
