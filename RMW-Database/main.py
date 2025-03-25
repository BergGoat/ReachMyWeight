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

# Create SQL schema file
def create_sql_schema():
    """
    Create the SQL schema file if it doesn't exist
    """
    sql_content = """
    -- RMW.sql schema file
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );

    -- Profiles table
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        gender TEXT NOT NULL DEFAULT 'male',
        height REAL NOT NULL DEFAULT 170,
        age INTEGER NOT NULL DEFAULT 30,
        activity_level TEXT NOT NULL DEFAULT 'moderate',
        FOREIGN KEY (user_id) REFERENCES users (id)
    );

    -- Weights table
    CREATE TABLE IF NOT EXISTS weights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        weight REAL NOT NULL,
        goal_weight REAL NOT NULL,
        date TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );

    -- Create a test user if none exist
    INSERT OR IGNORE INTO users (username, password) 
    VALUES ('test', 'password');

    -- Create profile for test user
    INSERT OR IGNORE INTO profiles (user_id, gender, height, age, activity_level) 
    VALUES (1, 'male', 180, 35, 'moderate');
    """
    
    with open("RMW.sql", "w") as f:
        f.write(sql_content)

# Initialize database with schema if it doesn't exist
def init_db():
    conn = sqlite3.connect("db/RMW.db", check_same_thread=False)
    try:
        with open("RMW.sql") as f:
            conn.executescript(f.read())
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
    finally:
        conn.close()

# Call init_db at startup
@app.on_event("startup")
async def startup_event():
    create_sql_schema()
    init_db()
    
    # Create a test user if none exist
    conn = sqlite3.connect("db/RMW.db", check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        # Check if any users exist
        user_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        
        if user_count == 0:
            # Create test user
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                ("test", "password")
            )
            
            # Create profile for test user
            cursor.execute(
                "INSERT INTO profiles (user_id, gender, height, age, activity_level) VALUES (?, ?, ?, ?, ?)",
                (1, "male", 180, 35, "moderate")
            )
            
            conn.commit()
            print("Created test user and profile")
    except Exception as e:
        print(f"Error creating test user: {str(e)}")
    finally:
        conn.close()

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
        # Check if profile already exists
        existing = db.execute("SELECT id FROM profiles WHERE user_id = ?", (profile.user_id,)).fetchone()
        
        if existing:
            # Update existing profile
            db.execute(
                "UPDATE profiles SET gender = ?, height = ?, age = ?, activity_level = ? WHERE user_id = ?",
                (profile.gender, profile.height, profile.age, profile.activity_level, profile.user_id)
            )
            db.commit()
            result = db.execute("SELECT * FROM profiles WHERE user_id = ?", (profile.user_id,)).fetchone()
            return dict(result)
        else:
            # Create new profile
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
        raise HTTPException(status_code=404, detail=f"User with ID {weight.user_id} not found")
    
    # Insert weight
    try:
        if weight.date:
            cursor = db.execute(
                "INSERT INTO weights (user_id, weight, goal_weight, date) VALUES (?, ?, ?, ?)",
                (weight.user_id, weight.weight, weight.goal_weight, weight.date)
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
        
        if result is None:
            raise HTTPException(
                status_code=500, 
                detail="Weight record was created but could not be retrieved"
            )
        
        return dict(result)
    except sqlite3.Error as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Error creating weight record: {str(e)}"
        )

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