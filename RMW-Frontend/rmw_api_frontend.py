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

# Configureer templates en statische bestanden
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# URL van de bestaande APIs
ORIGINAL_API_URL = os.environ.get("ORIGINAL_API_URL", "http://Backend:8000")
DATABASE_API_URL = os.environ.get("DATABASE_API_URL", "http://Database:8000")

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

# Functie om met de database API te communiceren
async def call_database_api(method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Roept de database API aan met de opgegeven methode, endpoint en data.
    
    Args:
        method: HTTP methode (GET, POST, etc.)
        endpoint: API endpoint (bijv. "/api/users")
        data: Optional data om naar de API te sturen bij POST requests
        
    Returns:
        De response van de API
    """
    async with httpx.AsyncClient() as client:
        try:
            if method.upper() == "GET":
                response = await client.get(f"{DATABASE_API_URL}{endpoint}")
            elif method.upper() == "POST":
                response = await client.post(f"{DATABASE_API_URL}{endpoint}", json=data)
            else:
                raise ValueError(f"Ongeldige HTTP methode: {method}")
                
            response.raise_for_status()  # Raise exception voor HTTP errors
            return response.json()
        except httpx.HTTPError as e:
            print(f"Database API Error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Kon geen verbinding maken met de database API: {str(e)}"
            )

# Database API operaties
async def db_check_user(username: str, password: str):
    """Controleert login gegevens via de Database API."""
    try:
        result = await call_database_api(
            "POST", 
            "/api/login", 
            {"username": username, "password": password}
        )
        return result
    except HTTPException as e:
        if e.status_code == 401:
            return None
        raise e

async def db_get_weights(user_id: int):
    """Haalt gewichtsmetingen op voor een gebruiker via de Database API."""
    return await call_database_api("GET", f"/api/weights/{user_id}")

async def db_get_user_profile(user_id: int):
    """Haalt profielgegevens op voor een gebruiker via de Database API."""
    user = await call_database_api("GET", f"/api/users/{user_id}")
    
    try:
        profile = await call_database_api("GET", f"/api/profiles/{user_id}")
    except HTTPException as e:
        if e.status_code == 404:
            profile = None
        else:
            raise e
    
    return user, profile

async def db_add_weight(user_id: int, weight: float, goal_weight: float, date_str: str = None):
    """Voegt een nieuwe gewichtsmeting toe via de Database API."""
    data = {
        "user_id": user_id,
        "weight": weight,
        "goal_weight": goal_weight
    }
    
    if date_str:
        data["date"] = date_str
    
    return await call_database_api("POST", "/api/weights", data)

async def db_check_user_exists(user_id: int):
    """Controleert of een gebruiker bestaat via de Database API."""
    try:
        await call_database_api("GET", f"/api/users/{user_id}")
        return True
    except HTTPException as e:
        if e.status_code == 404:
            return False
        raise e

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
    user = await db_check_user(username, password)
    
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
    
    entries = await db_get_weights(int(user_id))
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "username": username, 
            "entries": entries,
        }
    )

@app.get("/entry", response_class=HTMLResponse)
async def entry_page(request: Request, error: str = None):
    """Rendert de pagina voor gewichtsinvoer."""
    username = request.cookies.get("username")
    user_id = request.cookies.get("user_id")
    
    if not username or not user_id:
        return RedirectResponse(url="/login")
    
    # Haal gebruikersgegevens op
    user, profile = await db_get_user_profile(int(user_id))
    
    gender = profile["gender"] if profile and "gender" in profile else "male"
    height = profile["height"] if profile and "height" in profile else 170
    age = profile["age"] if profile and "age" in profile else 30
    activity_level = profile["activity_level"] if profile and "activity_level" in profile else "moderate"
    
    return templates.TemplateResponse(
        "entry.html", 
        {
            "request": request, 
            "username": username,
            "gender": gender,
            "height": height,
            "age": age,
            "activity_level": activity_level,
            "error": error
        }
    )

@app.post("/entry", response_class=HTMLResponse)
async def handle_entry(
    request: Request,
    weight: float = Form(...),
    goal_weight: float = Form(...),
    gender: str = Form(...),
    height: float = Form(...),
    age: int = Form(...),
    activity_level: str = Form(...),
    # De volgende parameters zijn optioneel
    sport: List[str] = Form([]),
    aantal_minuten_sporten: int = Form(0),
    deficit_surplus: int = Form(0)
):
    """Verwerkt het formulier voor gewichtsinvoer."""
    username = request.cookies.get("username")
    user_id = request.cookies.get("user_id")
    
    if not username or not user_id:
        return RedirectResponse(url="/login")
    
    # Sla gegevens op
    await db_add_weight(int(user_id), weight, goal_weight)
    
    # Haal gewichtsgeschiedenis op
    entries = await db_get_weights(int(user_id))
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "username": username, 
            "entries": entries,
            "result": None
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

@app.get("/api/weights/{user_id}", response_model=List[Dict[str, Any]])
async def get_weights(user_id: int):
    """
    API endpoint voor het ophalen van gewichtsmetingen.
    
    Args:
        user_id: ID van de gebruiker
        
    Returns:
        Een lijst met gewichtsmetingen voor de gebruiker
    """
    entries = await db_get_weights(user_id)
    
    # Als er geen metingen zijn, geef een lege lijst terug
    if not entries:
        return []
    
    return entries

@app.post("/api/weights", response_model=Dict[str, Any])
async def add_weight(entry: WeightEntry):
    """
    API endpoint voor het toevoegen van een gewichtsmeting.
    
    Args:
        entry: Data voor de nieuwe gewichtsmeting
        
    Returns:
        De toegevoegde gewichtsmeting
    """
    # Controleer of de gebruiker bestaat
    if not await db_check_user_exists(entry.user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Gebruiker met ID {entry.user_id} bestaat niet"
        )
    
    # Voeg gewichtsmeting toe
    try:
        result = await db_add_weight(
            entry.user_id, entry.weight, entry.goal_weight, entry.date
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kon gewichtsmeting niet toevoegen: {str(e)}"
        )

@app.post("/api/calculate", response_model=CalculationResult)
async def calculate(data: UserInput):
    """
    API endpoint voor het berekenen van de tijd tot doel.
    
    Args:
        data: Invoergegevens voor de berekening
        
    Returns:
        Resultaat van de berekening
    """
    # Roep de originele API aan voor de berekening
    result = await call_original_api(data.dict())
    
    return {
        "days_to_goal": result.get("days_to_goal", 0),
        "current_weight": data.weight,
        "goal_weight": data.gewenst_gewicht
    }