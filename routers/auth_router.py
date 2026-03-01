from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import database

router = APIRouter()

class LoginData(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(data: LoginData):
    conn = database.get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (data.username, data.password))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return {
            "status": "ok",
            "user": {
                "username": user["username"],
                "couple_id": user["couple_id"]
            }
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid username or password")

@router.get("/current_user/{username}")
def get_user(username: str):
    conn = database.get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT username, couple_id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return dict(user)
    else:
        raise HTTPException(status_code=404, detail="User not found")
