from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import os

app = FastAPI()

# Ensure the database directory exists
os.makedirs("db", exist_ok=True)

# Initialize the database
def get_db():
    conn = sqlite3.connect("db/RMW.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Initialize database with schema if it doesn't exist
def init_db():
    conn = sqlite3.connect("db/RMW.db", check_same_thread=False)
    with open("RMW.sql") as f:
        conn.executescript(f.read())
    conn.close()

# Call init_db at startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Models
class User(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str

class Profile(BaseModel):
    user_id: int
    gender: str
    height: float
    age: int
    activity_level: str

class ProfileResponse(BaseModel):
    id: int
    user_id: int
    gender: str
    height: float
    age: int
    activity_level: str

class Weight(BaseModel):
    user_id: int
    weight: float
    goal_weight: float
    date: Optional[str] = None

class WeightResponse(BaseModel):
    id: int
    user_id: int
    weight: float
    goal_weight: float
    date: str

# User endpoints with original paths
@app.post("/users", response_model=UserResponse)
async def create_user(user: User, db: sqlite3.Connection = Depends(get_db)):
    try:
        cursor = db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (user.username, user.password)
        )
        db.commit()
        user_id = cursor.lastrowid
        
        return {"id": user_id, "username": user.username}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: sqlite3.Connection = Depends(get_db)):
    result = db.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
    
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return dict(result)

@app.post("/login")
async def login(user: User, db: sqlite3.Connection = Depends(get_db)):
    result = db.execute(
        "SELECT id, username FROM users WHERE username = ? AND password = ?",
        (user.username, user.password)
    ).fetchone()
    
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return dict(result)

# Profile endpoints
@app.post("/profiles", response_model=ProfileResponse)
async def create_profile(profile: Profile, db: sqlite3.Connection = Depends(get_db)):
    # Verify user exists
    user = db.execute("SELECT id FROM users WHERE id = ?", (profile.user_id,)).fetchone()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        cursor = db.execute(
            "INSERT INTO profiles (user_id, gender, height, age, activity_level) VALUES (?, ?, ?, ?, ?)",
            (profile.user_id, profile.gender, profile.height, profile.age, profile.activity_level)
        )
        db.commit()
        profile_id = cursor.lastrowid
        
        result = db.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        return dict(result)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Profile already exists for this user")

@app.get("/profiles/{user_id}", response_model=ProfileResponse)
async def get_profile(user_id: int, db: sqlite3.Connection = Depends(get_db)):
    result = db.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    
    if result is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return dict(result)

# Weight endpoints with original paths
@app.post("/weights", response_model=WeightResponse)
async def create_weight(weight: Weight, db: sqlite3.Connection = Depends(get_db)):
    # Verify user exists
    user = db.execute("SELECT id FROM users WHERE id = ?", (weight.user_id,)).fetchone()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Insert weight
    date_value = weight.date if weight.date else "CURRENT_DATE"
    if date_value != "CURRENT_DATE":
        cursor = db.execute(
            "INSERT INTO weights (user_id, weight, goal_weight, date) VALUES (?, ?, ?, ?)",
            (weight.user_id, weight.weight, weight.goal_weight, date_value)
        )
    else:
        cursor = db.execute(
            "INSERT INTO weights (user_id, weight, goal_weight) VALUES (?, ?, ?)",
            (weight.user_id, weight.weight, weight.goal_weight)
        )
    
    db.commit()
    weight_id = cursor.lastrowid
    
    # Get the inserted record
    result = db.execute(
        "SELECT id, user_id, weight, goal_weight, date FROM weights WHERE id = ?", 
        (weight_id,)
    ).fetchone()
    
    return dict(result)

@app.get("/weights/{user_id}", response_model=List[WeightResponse])
async def get_weights(user_id: int, db: sqlite3.Connection = Depends(get_db)):
    # Verify user exists
    user = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get weights
    results = db.execute(
        "SELECT id, user_id, weight, goal_weight, date FROM weights WHERE user_id = ? ORDER BY date DESC",
        (user_id,)
    ).fetchall()
    
    return [dict(result) for result in results]

@app.get("/weights/{user_id}/latest", response_model=WeightResponse)
async def get_latest_weight(user_id: int, db: sqlite3.Connection = Depends(get_db)):
    # Verify user exists
    user = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get latest weight
    result = db.execute(
        "SELECT id, user_id, weight, goal_weight, date FROM weights WHERE user_id = ? ORDER BY date DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    
    if result is None:
        raise HTTPException(status_code=404, detail="No weight records found for this user")
    
    return dict(result)

# User endpoints with /api/ prefix to match the frontend
@app.post("/api/users", response_model=UserResponse)
async def create_user_api(user: User, db: sqlite3.Connection = Depends(get_db)):
    return await create_user(user, db)

@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user_api(user_id: int, db: sqlite3.Connection = Depends(get_db)):
    return await get_user(user_id, db)

@app.post("/api/login")
async def login_api(user: User, db: sqlite3.Connection = Depends(get_db)):
    return await login(user, db)

# Profile endpoints with /api/ prefix
@app.post("/api/profiles", response_model=ProfileResponse)
async def create_profile_api(profile: Profile, db: sqlite3.Connection = Depends(get_db)):
    return await create_profile(profile, db)

@app.get("/api/profiles/{user_id}", response_model=ProfileResponse)
async def get_profile_api(user_id: int, db: sqlite3.Connection = Depends(get_db)):
    return await get_profile(user_id, db)

# Weight endpoints with /api/ prefix to match the frontend
@app.post("/api/weights", response_model=WeightResponse)
async def create_weight_api(weight: Weight, db: sqlite3.Connection = Depends(get_db)):
    return await create_weight(weight, db)

@app.get("/api/weights/{user_id}", response_model=List[WeightResponse])
async def get_weights_api(user_id: int, db: sqlite3.Connection = Depends(get_db)):
    return await get_weights(user_id, db)

@app.get("/api/weights/{user_id}/latest", response_model=WeightResponse)
async def get_latest_weight_api(user_id: int, db: sqlite3.Connection = Depends(get_db)):
    return await get_latest_weight(user_id, db) 