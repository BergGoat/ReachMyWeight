"""
Gewichtstracker API en Webapplicatie
------------------
Deze API bevat de frontend webapplicatie voor de gewichtstracker
en maakt verbinding met de bestaande API voor berekeningen.
"""

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3
import os
import httpx
from typing import List, Optional, Dict, Any, Callable
from datetime import date
import functools

# Initialiseer de FastAPI applicatie
app = FastAPI(
    title="Gewichtstracker App",
    description="Web applicatie voor het bijhouden van gewicht",
    version="1.0"
)

# Controleer of de benodigde mappen bestaan, zo niet, maak ze aan
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("sql", exist_ok=True)
os.makedirs("database", exist_ok=True)

# Configureer templates en statische bestanden
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuratie voor de database
DATABASE_FILE = "database/fitness.db"

# URL van de bestaande API
ORIGINAL_API_URL = os.environ.get("ORIGINAL_API_URL", "http://localhost:8000")

# Helper voor synchrone database operaties
def run_sync_db(func: Callable, *args, **kwargs):
    """
    Helper om synchrone database operaties uit te voeren in een asynchrone context.
    Elk database operatie wordt in zijn eigen connectie uitgevoerd.
    """
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        try:
            result = func(conn, *args, **kwargs)
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    return wrapped

# Database initialisatie
def init_db():
    """Initialiseert de database als deze nog niet bestaat."""
    if not os.path.exists(DATABASE_FILE):
        os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)
        conn = sqlite3.connect(DATABASE_FILE)
        try:
            with open('sql/schema.sql', 'r') as f:
                conn.executescript(f.read())
            conn.commit()
            print("Database geïnitialiseerd")
        finally:
            conn.close()

# Functie om met de originele API te communiceren
async def call_original_api(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Roept de originele API aan met de opgegeven data.
    
    Args:
        data: Data om naar de API te sturen
        
    Returns:
        De response van de API
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{ORIGINAL_API_URL}/calculate", json=data)
            response.raise_for_status()  # Raise exception voor HTTP errors
            return response.json()
        except httpx.HTTPError as e:
            print(f"HTTP Error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Kon geen verbinding maken met de originele API: {str(e)}"
            )

# Database operaties
@run_sync_db
def db_check_user(conn, username: str, password: str):
    """Controleert login gegevens."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?", 
        (username, password)
    )
    return cursor.fetchone()

@run_sync_db
def db_get_weights(conn, user_id: int):
    """Haalt gewichtsmetingen op voor een gebruiker."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM weights WHERE user_id = ? ORDER BY date DESC", 
        (user_id,)
    )
    return cursor.fetchall()

@run_sync_db
def db_get_user_profile(conn, user_id: int):
    """Haalt profielgegevens op voor een gebruiker."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()
    
    return user, profile

@run_sync_db
def db_add_weight(conn, user_id: int, weight: float, goal_weight: float, date_str: str = None):
    """Voegt een nieuwe gewichtsmeting toe."""
    cursor = conn.cursor()
    today = date.today().isoformat() if date_str is None else date_str
    
    cursor.execute(
        "INSERT INTO weights (user_id, weight, goal_weight, date) VALUES (?, ?, ?, ?)",
        (user_id, weight, goal_weight, today)
    )
    
    new_id = cursor.lastrowid
    cursor.execute("SELECT * FROM weights WHERE id = ?", (new_id,))
    return cursor.fetchone()

@run_sync_db
def db_check_user_exists(conn, user_id: int):
    """Controleert of een gebruiker bestaat."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone() is not None

# Datamodellen voor de API
class UserInput(BaseModel):
    """Model voor invoer naar de originele API."""
    gender: str
    weight: float
    height: float
    age: int
    activity_level: str
    sport: List[str]
    aantal_minuten_sporten: int
    gewenst_gewicht: float
    deficit_surplus: int

class WeightEntry(BaseModel):
    """Model voor gewichtsinvoer via de API."""
    user_id: int
    weight: float
    goal_weight: float
    date: Optional[str] = None

class WeightResponse(BaseModel):
    """Model voor de response van gewichtsgegevens via de API."""
    id: int
    user_id: int
    weight: float
    goal_weight: float
    date: str

class CalculationResult(BaseModel):
    """Model voor het resultaat van het tijdberekeningsalgoritme via de API."""
    days_to_goal: float
    current_weight: float
    goal_weight: float

# Start database bij opstarten
@app.on_event("startup")
async def startup_event():
    init_db()

#
# WEB ROUTES (HTML PAGINA'S)
#

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Hoofdpagina route, stuurt gebruiker door naar login."""
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    """Rendert de login pagina."""
    return templates.TemplateResponse(
        "login.html", 
        {"request": request, "error": error}
    )

@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request, 
    username: str = Form(...), 
    password: str = Form(...)
):
    """Verwerkt het inlogformulier."""
    user = db_check_user(username, password)
    
    if not user:
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "Ongeldige gebruikersnaam of wachtwoord"}
        )
    
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="username", value=username)
    response.set_cookie(key="user_id", value=str(user["id"]))
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Rendert het dashboard met gewichtsgegevens."""
    username = request.cookies.get("username")
    user_id = request.cookies.get("user_id")
    
    if not username or not user_id:
        return RedirectResponse(url="/login")
    
    entries = db_get_weights(int(user_id))
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "username": username, 
            "entries": entries,
            "result": None  # Initieel is er geen resultaat
        }
    )

@app.post("/add-weight", response_class=HTMLResponse)
async def add_weight(
    request: Request,
    weight: float = Form(...),
    goal_weight: float = Form(...)
):
    """Verwerkt het gewichtsinvoerformulier en roept de originele API aan."""
    username = request.cookies.get("username")
    user_id = request.cookies.get("user_id")
    
    if not username or not user_id:
        return RedirectResponse(url="/login")
    
    # Haal gebruikersgegevens op
    user, profile = db_get_user_profile(int(user_id))
    
    gender = profile["gender"] if profile and "gender" in profile.keys() else "male"
    height = profile["height"] if profile and "height" in profile.keys() else 180
    age = profile["age"] if profile and "age" in profile.keys() else 30
    activity_level = profile["activity_level"] if profile and "activity_level" in profile.keys() else "moderate"
    
    # Bereid data voor om naar de originele API te sturen
    api_data = {
        "gender": gender,
        "weight": weight,
        "height": height,
        "age": age,
        "activity_level": activity_level,
        "sport": ["Football"],  # Standaard sport
        "aantal_minuten_sporten": 30,  # Standaard minuten
        "gewenst_gewicht": goal_weight,
        "deficit_surplus": 500  # Standaard calorisch tekort/overschot
    }
    
    # Roep de originele API aan
    try:
        api_result = await call_original_api(api_data)
        # Gebruik het eerste resultaat uit de lijst
        days = api_result["results"][0]["time_to_reach_goal"] if api_result["results"] else 0
    except Exception as e:
        # Als er een fout is, toon een bericht
        print(f"Fout bij aanroepen originele API: {str(e)}")
        days = 0  # Default waarde
    
    # Sla gegevens op
    db_add_weight(int(user_id), weight, goal_weight)
    
    # Haal gewichtsgeschiedenis op
    entries = db_get_weights(int(user_id))
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "username": username, 
            "entries": entries,
            "result": {"days": round(days, 1)}
        }
    )

@app.get("/logout")
async def logout():
    """Verwerkt uitloggen door cookies te verwijderen."""
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="username")
    response.delete_cookie(key="user_id")
    return response

#
# API ROUTES (JSON DATA)
#

@app.get("/api", response_class=HTMLResponse)
async def api_docs(request: Request):
    """Toont documentatie over de API."""
    return templates.TemplateResponse(
        "api_docs.html",
        {"request": request}
    )

@app.get("/api/weights/{user_id}", response_model=List[WeightResponse])
async def get_weight_entries(user_id: int):
    """
    Haalt de gewichtsmetingen op voor een specifieke gebruiker.
    
    Args:
        user_id: De ID van de gebruiker
        
    Returns:
        Een lijst met gewichtsmetingen voor de gebruiker
    """
    entries = db_get_weights(user_id)
    
    # Als er geen metingen zijn, geef een lege lijst terug
    if not entries:
        return []
    
    # Zet de resultaten om naar het response model
    return [
        {
            "id": entry["id"],
            "user_id": entry["user_id"],
            "weight": entry["weight"],
            "goal_weight": entry["goal_weight"],
            "date": entry["date"]
        }
        for entry in entries
    ]

@app.post("/api/weights/", response_model=WeightResponse, status_code=status.HTTP_201_CREATED)
async def create_weight_entry(entry: WeightEntry):
    """
    Voegt een nieuwe gewichtsmeting toe aan de database.
    
    Args:
        entry: De gewichtsinvoer gegevens
        
    Returns:
        De toegevoegde gewichtsmeting
    """
    # Controleer of de gebruiker bestaat
    if not db_check_user_exists(entry.user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Gebruiker niet gevonden"
        )
    
    # Voeg gewichtsmeting toe
    try:
        result = db_add_weight(
            entry.user_id, entry.weight, entry.goal_weight, entry.date
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database fout: {str(e)}"
        )
    
    # Zet het resultaat om naar het response model
    return {
        "id": result["id"],
        "user_id": result["user_id"],
        "weight": result["weight"],
        "goal_weight": result["goal_weight"],
        "date": result["date"]
    }

@app.post("/api/calculate/", response_model=CalculationResult)
async def calculate_time(entry: WeightEntry):
    """
    Berekent de tijd die nodig is om een gewichtsdoel te bereiken door de originele API aan te roepen.
    
    Args:
        entry: De gewichtsinvoer gegevens
        
    Returns:
        Het resultaat van de berekening
    """
    # Standaardwaarden voor API-aanroep
    api_data = {
        "gender": "male",  # Standaard gender
        "weight": entry.weight,
        "height": 180,  # Standaard hoogte
        "age": 30,  # Standaard leeftijd
        "activity_level": "moderate",  # Standaard activiteitsniveau
        "sport": ["Football"],  # Standaard sport
        "aantal_minuten_sporten": 30,  # Standaard minuten
        "gewenst_gewicht": entry.goal_weight,
        "deficit_surplus": 500  # Standaard calorisch tekort/overschot
    }
    
    # Roep de originele API aan
    api_result = await call_original_api(api_data)
    
    # Gebruik het eerste resultaat uit de lijst
    days = api_result["results"][0]["time_to_reach_goal"] if api_result["results"] else 0
    
    # Geef het resultaat terug
    return {
        "days_to_goal": round(days, 1),
        "current_weight": entry.weight,
        "goal_weight": entry.goal_weight
    }

# Start de applicatie
if __name__ == "__main__":
    import uvicorn
    print("Starting Gewichtstracker App op poort 9200...")
    uvicorn.run(app, host="0.0.0.0", port=9200)