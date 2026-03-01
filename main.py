from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
import sqlite3
import math
from datetime import datetime, timezone, timedelta
import uuid

# Import our custom DB module
import database

app = FastAPI(title="Our Moments API")

# Enable CORS for local testing from index.html
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the DB on startup
@app.on_event("startup")
def startup_event():
    database.init_db()

from routers import map_router, schedule_router, auth_router, couple_router

app.include_router(map_router.router, prefix="/api")
app.include_router(schedule_router.router, prefix="/api")
app.include_router(auth_router.router, prefix="/api")
app.include_router(couple_router.router, prefix="/api")

# Serve static files (HTML, CSS, JS) - Mount this LAST
app.mount("/", StaticFiles(directory=".", html=True), name="static")
