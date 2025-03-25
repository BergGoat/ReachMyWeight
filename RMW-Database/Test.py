import pytest
import sqlite3
from fastapi.testclient import TestClient
from main import app, get_db

# Test database setup
def override_get_db():
    """Vervangt de database met een in-memory database voor tests."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    with open("RMW.sql") as f:
        conn.executescript(f.read())
    try:
        yield conn
    finally:
        conn.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# Testvolgorde: eerst gebruiker aanmaken, dan login testen
def test_create_user():
    """Test voor het aanmaken van een gebruiker."""
    response = client.post("/users", json={"username": "test", "password": "test123"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] > 0
    assert data["username"] == "test"

def test_login():
    """Test voor inloggen met de juiste gegevens."""
    test_create_user()  

    response = client.post("/login", json={"username": "test", "password": "test123"})
    assert response.status_code == 200, f"Login failed: {response.json()}"
    data = response.json()
    assert "id" in data
    assert data["username"] == "test"

def test_invalid_login():
    """Test voor een foutieve login poging."""
    response = client.post("/login", json={"username": "test", "password": "wrongpass"})
    assert response.status_code == 401

def test_get_user():
    """Test om een gebruiker op te halen."""
    test_create_user() 

    response = client.get("/users/1")
    assert response.status_code == 200, f"Get user failed: {response.json()}"
    data = response.json()
    assert data["id"] == 1
    assert data["username"] == "test"

# Gewichtentests
def test_create_weight():
    """Test om een gewicht toe te voegen."""
    test_create_user()  

    response = client.post("/weights", json={
        "user_id": 1,
        "weight": 80.5,
        "goal_weight": 75
    })
    assert response.status_code == 200, f"Create weight failed: {response.json()}"
    data = response.json()
    assert data["user_id"] == 1
    assert data["weight"] == 80.5

def test_get_weights():
    """Voeg eerst een gewicht toe voordat we gewichten ophalen."""
    test_create_weight()  

    response = client.get("/weights/1")
    assert response.status_code == 200, f"Get weights failed: {response.json()}"
    data = response.json()
    assert len(data) > 0, "Weight list is empty"

def test_get_latest_weight():
    """Zorg dat er een gewicht is voordat we de nieuwste opvragen."""
    test_create_weight()  

    response = client.get("/weights/1/latest")
    assert response.status_code == 200, f"Get latest weight failed: {response.json()}"
    data = response.json()
    assert data["user_id"] == 1
    assert data["weight"] == 80.5

if __name__ == "__main__":
    pytest.main()
