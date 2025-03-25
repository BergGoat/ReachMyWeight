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
ORIGINAL_API_URL = os.environ.get("ORIGINAL_API_URL")
DATABASE_API_URL = os.environ.get("DATABASE_API_URL")

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
            print(f"Calling original API at {ORIGINAL_API_URL}/calculate with data: {data}")
            response = await client.post(f"{ORIGINAL_API_URL}/calculate", json=data)
            response.raise_for_status()  # Raise exception voor HTTP errors
            result = response.json()
            print(f"Original API response: {result}")
            return result
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
            print(f"Calling database API at {DATABASE_API_URL}{endpoint} with method {method} and data: {data}")
            if method.upper() == "GET":
                response = await client.get(f"{DATABASE_API_URL}{endpoint}")
            elif method.upper() == "POST":
                response = await client.post(f"{DATABASE_API_URL}{endpoint}", json=data)
            else:
                raise ValueError(f"Ongeldige HTTP methode: {method}")
                
            response.raise_for_status()  # Raise exception voor HTTP errors
            result = response.json()
            print(f"Database API response: {result}")
            return result
        except httpx.HTTPError as e:
            print(f"Database API Error: {e}")
            if hasattr(e.response, 'status_code'):
                status_code = e.response.status_code
            else:
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                
            if hasattr(e.response, 'text'):
                try:
                    detail = e.response.json().get('detail', str(e))
                except:
                    detail = e.response.text
            else:
                detail = str(e)
                
            raise HTTPException(
                status_code=status_code,
                detail=detail
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
    
    try:
        # Debug print to check data being sent
        print(f"Sending weight data to DB API: {data}")
        return await call_database_api("POST", "/api/weights", data)
    except HTTPException as e:
        print(f"Error adding weight: {e.detail}")
        # Return a more informative error
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Error adding weight: {e.detail}"
        )

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
async def login_page(request: Request, error: str = None, success: str = None):
    """Rendert de login pagina."""
    return templates.TemplateResponse(
        "login.html", 
        {"request": request, "error": error, "success": success}
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
    
    # Get weight entries
    entries = await db_get_weights(int(user_id))
    
    # Get the last weight entry to display calculation options
    if entries and len(entries) > 0:
        latest_entry = entries[0]  # Assuming entries are sorted by date desc
        
        # Get user profile
        try:
            user, profile = await db_get_user_profile(int(user_id))
            
            gender = profile["gender"] if profile and "gender" in profile else "male"
            height = profile["height"] if profile and "height" in profile else 170
            age = profile["age"] if profile and "age" in profile else 30
            activity_level = profile["activity_level"] if profile and "activity_level" in profile else "moderate"
            
            # Default sports
            sports = ["Swimming", "Football"]
            
            # Create calculation request for the latest entry
            calc_data = {
                "gender": gender,
                "weight": latest_entry["weight"],
                "height": height,
                "age": age,
                "activity_level": activity_level,
                "sport": sports,
                "aantal_minuten_sporten": 30,  # Default value
                "gewenst_gewicht": latest_entry["goal_weight"],
                "deficit_surplus": 500  # Default value
            }
            
            # Call API for calculation
            try:
                calculation_result = await call_original_api(calc_data)
                
                # Extract the detailed results
                detailed_results = calculation_result.get("results", [])
                
                # Initialize containers for the three deficit levels
                light_results = [r for r in detailed_results if r.get("calorie_adjustment") == 250]
                standard_results = [r for r in detailed_results if r.get("calorie_adjustment") == 500]
                intensive_results = [r for r in detailed_results if r.get("calorie_adjustment") == 1000]
                
                # Calculate the average days for each deficit level
                light_option = {
                    "days": sum(r.get("time_to_reach_goal", 0) for r in light_results) / max(len(light_results), 1),
                    "tdee": light_results[0].get("TDEE", 0) if light_results else 0
                }
                
                standard_option = {
                    "days": sum(r.get("time_to_reach_goal", 0) for r in standard_results) / max(len(standard_results), 1),
                    "tdee": standard_results[0].get("TDEE", 0) if standard_results else 0
                }
                
                intensive_option = {
                    "days": sum(r.get("time_to_reach_goal", 0) for r in intensive_results) / max(len(intensive_results), 1),
                    "tdee": intensive_results[0].get("TDEE", 0) if intensive_results else 0
                }
                
                # Compile complete calculation results
                calculation_results = {
                    "current_weight": latest_entry["weight"],
                    "goal_weight": latest_entry["goal_weight"],
                    "days_to_goal": calculation_result.get("days_to_goal", 0),
                    "weight_difference": abs(latest_entry["weight"] - latest_entry["goal_weight"]),
                    "bmr": calculation_result.get("BMR", 0),
                    "tdee": calculation_result.get("TDEE", 0)
                }
            except Exception as e:
                print(f"Error calculating time to goal for dashboard: {str(e)}")
                calculation_results = None
                light_option = None
                standard_option = None
                intensive_option = None
        except Exception as e:
            print(f"Error getting user profile for dashboard: {str(e)}")
            calculation_results = None
            light_option = None
            standard_option = None
            intensive_option = None
    else:
        calculation_results = None
        light_option = None
        standard_option = None
        intensive_option = None
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "username": username, 
            "entries": entries,
            "calculation_results": calculation_results,
            "light_option": light_option,
            "standard_option": standard_option,
            "intensive_option": intensive_option
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
    try:
        user, profile = await db_get_user_profile(int(user_id))
        
        gender = profile["gender"] if profile and "gender" in profile else "male"
        height = profile["height"] if profile and "height" in profile else 170
        age = profile["age"] if profile and "age" in profile else 30
        activity_level = profile["activity_level"] if profile and "activity_level" in profile else "moderate"
    except Exception as e:
        print(f"Error fetching user profile: {str(e)}")
        gender = "male"
        height = 170
        age = 30
        activity_level = "moderate"
    
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
    sport: List[str] = Form(...),  # Now required, validation handled in Javascript
    aantal_minuten_sporten: int = Form(0),
    deficit_surplus: int = Form(500)  # Default to 500 calorie deficit
):
    """Verwerkt het formulier voor gewichtsinvoer."""
    username = request.cookies.get("username")
    user_id = request.cookies.get("user_id")
    
    if not username or not user_id:
        return RedirectResponse(url="/login")
    
    # Check if at least 2 sports are selected
    if len(sport) < 2:
        return templates.TemplateResponse(
            "entry.html",
            {
                "request": request,
                "username": username,
                "gender": gender,
                "height": height,
                "age": age,
                "activity_level": activity_level,
                "error": "Selecteer minimaal 2 sportactiviteiten"
            }
        )
    
    # Print debug info
    print(f"User ID from cookie: {user_id}")
    print(f"Selected sports: {sport}")
    
    # Ensure user exists
    try:
        user_exists = await db_check_user_exists(int(user_id))
        if not user_exists:
            return templates.TemplateResponse(
                "entry.html",
                {
                    "request": request,
                    "username": username,
                    "gender": gender,
                    "height": height,
                    "age": age,
                    "activity_level": activity_level,
                    "error": f"User with ID {user_id} not found in database"
                }
            )
    except Exception as e:
        print(f"Error checking user: {str(e)}")
        return templates.TemplateResponse(
            "entry.html",
            {
                "request": request,
                "username": username,
                "gender": gender,
                "height": height,
                "age": age,
                "activity_level": activity_level,
                "error": f"Error checking user: {str(e)}"
            }
        )
    
    # Sla gegevens op
    try:
        await db_add_weight(int(user_id), weight, goal_weight)
    except HTTPException as e:
        return templates.TemplateResponse(
            "entry.html",
            {
                "request": request,
                "username": username,
                "gender": gender,
                "height": height,
                "age": age,
                "activity_level": activity_level,
                "error": f"Error adding weight: {e.detail}"
            }
        )
    
    # Calculate time to goal using all sports at once
    try:
        # Create calculation request
        calc_data = {
            "gender": gender,
            "weight": weight,
            "height": height,
            "age": age,
            "activity_level": activity_level,
            "sport": sport,  # Include all selected sports
            "aantal_minuten_sporten": aantal_minuten_sporten,
            "gewenst_gewicht": goal_weight,
            "deficit_surplus": deficit_surplus
        }
        
        # Call API for calculation
        calculation_result = await call_original_api(calc_data)
        
        # Extract the detailed results
        detailed_results = calculation_result.get("results", [])
        
        # Initialize containers for the three deficit levels
        light_results = [r for r in detailed_results if r.get("calorie_adjustment") == 250]
        standard_results = [r for r in detailed_results if r.get("calorie_adjustment") == 500]
        intensive_results = [r for r in detailed_results if r.get("calorie_adjustment") == 1000]
        
        # Calculate the average days for each deficit level
        light_option = {
            "days": sum(r.get("time_to_reach_goal", 0) for r in light_results) / max(len(light_results), 1),
            "tdee": light_results[0].get("TDEE", 0) if light_results else 0
        }
        
        standard_option = {
            "days": sum(r.get("time_to_reach_goal", 0) for r in standard_results) / max(len(standard_results), 1),
            "tdee": standard_results[0].get("TDEE", 0) if standard_results else 0
        }
        
        intensive_option = {
            "days": sum(r.get("time_to_reach_goal", 0) for r in intensive_results) / max(len(intensive_results), 1),
            "tdee": intensive_results[0].get("TDEE", 0) if intensive_results else 0
        }
        
        # Compile complete calculation results
        calculation_results = {
            "current_weight": weight,
            "goal_weight": goal_weight,
            "days_to_goal": calculation_result.get("days_to_goal", 0),
            "weight_difference": abs(weight - goal_weight),
            "bmr": calculation_result.get("BMR", 0),
            "tdee": calculation_result.get("TDEE", 0)
        }
        
    except Exception as e:
        print(f"Error calculating time to goal: {str(e)}")
        calculation_results = None
        light_option = None
        standard_option = None
        intensive_option = None
    
    # Haal gewichtsgeschiedenis op
    entries = await db_get_weights(int(user_id))
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "username": username, 
            "entries": entries,
            "calculation_results": calculation_results,
            "light_option": light_option,
            "standard_option": standard_option,
            "intensive_option": intensive_option
        }
    )

@app.get("/logout")
async def logout():
    """Verwerkt uitloggen door cookies te verwijderen."""
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="username")
    response.delete_cookie(key="user_id")
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = None):
    """Rendert de registratie pagina."""
    return templates.TemplateResponse(
        "register.html", 
        {"request": request, "error": error}
    )

@app.post("/register", response_class=HTMLResponse)
async def handle_register(
    request: Request, 
    username: str = Form(...), 
    password: str = Form(...), 
    confirm_password: str = Form(...),
    gender: str = Form(...),
    height: float = Form(...),
    age: int = Form(...),
    activity_level: str = Form(...)
):
    """Verwerkt het registratieformulier."""
    # Controleer of de wachtwoorden overeenkomen
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Wachtwoorden komen niet overeen"}
        )
    
    # Controleer of de gebruikersnaam al bestaat
    try:
        # Maak een nieuwe gebruiker aan
        user_data = {
            "username": username,
            "password": password
        }
        
        # Voeg gebruiker toe via de database API
        user = await call_database_api("POST", "/api/users", user_data)
        
        # Voeg profiel toe voor de nieuwe gebruiker
        profile_data = {
            "user_id": user["id"],
            "gender": gender,
            "height": height,
            "age": age,
            "activity_level": activity_level
        }
        
        # Profiel toevoegen via de database API
        await call_database_api("POST", "/api/profiles", profile_data)
        
        # Stuur door naar login pagina met succes bericht
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "success": "Account succesvol aangemaakt! Log nu in."}
        )
        
    except HTTPException as e:
        error_message = e.detail
        if e.status_code == 400 and "Username already exists" in e.detail:
            error_message = "Deze gebruikersnaam is al in gebruik."
        
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": error_message}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": f"Er is een fout opgetreden: {str(e)}"}
        )

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