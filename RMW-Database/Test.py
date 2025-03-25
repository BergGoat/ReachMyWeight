import pytest
import sqlite3
import time
from fastapi.testclient import TestClient
from main import app, get_db

# Test database setup
@pytest.fixture(scope="session")
def test_db():
    """Vervangt de database met een in-memory database voor tests."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    with open("RMW.sql") as f:
        conn.executescript(f.read())
    yield conn
    conn.close()

@pytest.fixture
def override_get_db(test_db):
    """Fixture om een database-verbinding te bieden."""
    def _override_get_db():
        try:
            yield test_db
        finally:
            pass
    return _override_get_db

@pytest.fixture
def test_client(override_get_db):
    """Fixture om een test client te maken met de database override."""
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(test_client):
    """Fixture om een testgebruiker aan te maken."""
    # Genereer een unieke gebruikersnaam met timestamp
    timestamp = int(time.time() * 1000)
    unique_username = f"testuser_{timestamp}"
    
    response = test_client.post("/users", json={"username": unique_username, "password": "test123"})
    assert response.status_code == 200, f"User creation failed: {response.text}"
    return response.json()

@pytest.fixture
def test_weight(test_client, test_user):
    """Fixture om een testgewicht aan te maken."""
    response = test_client.post("/weights", json={
        "user_id": test_user["id"],
        "weight": 80.5,
        "goal_weight": 75
    })
    assert response.status_code == 200
    return response.json()

# Gebruikerstests
def test_create_user(test_client):
    """Test voor het aanmaken van een gebruiker."""
    timestamp = int(time.time() * 1000)
    unique_username = f"testuser2_{timestamp}"
    
    response = test_client.post("/users", json={"username": unique_username, "password": "test123"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] > 0
    assert data["username"] == unique_username

def test_login(test_client, test_user):
    """Test voor inloggen met de juiste gegevens."""
    response = test_client.post("/login", json={
        "username": test_user["username"], 
        "password": "test123"
    })
    assert response.status_code == 200, f"Login failed: {response.json()}"
    data = response.json()
    assert "id" in data
    assert data["username"] == test_user["username"]

def test_invalid_login(test_client):
    """Test voor een foutieve login poging."""
    response = test_client.post("/login", json={"username": "test", "password": "wrongpass"})
    assert response.status_code == 401

def test_get_user(test_client, test_user):
    """Test om een gebruiker op te halen."""
    response = test_client.get(f"/users/{test_user['id']}")
    assert response.status_code == 200, f"Get user failed: {response.json()}"
    data = response.json()
    assert data["id"] == test_user["id"]
    assert data["username"] == test_user["username"]

# Gewichtentests
def test_create_weight(test_client, test_user):
    """Test om een gewicht toe te voegen."""
    response = test_client.post("/weights", json={
        "user_id": test_user["id"],
        "weight": 80.5,
        "goal_weight": 75
    })
    assert response.status_code == 200, f"Create weight failed: {response.json()}"
    data = response.json()
    assert data["user_id"] == test_user["id"]
    assert data["weight"] == 80.5

def test_get_weights(test_client, test_weight):
    """Test om gewichtsgegevens op te halen."""
    user_id = test_weight["user_id"]
    response = test_client.get(f"/weights/{user_id}")
    assert response.status_code == 200, f"Get weights failed: {response.json()}"
    data = response.json()
    assert len(data) > 0, "Weight list is empty"

def test_get_latest_weight(test_client, test_weight):
    """Test om het nieuwste gewicht op te halen."""
    user_id = test_weight["user_id"]
    response = test_client.get(f"/weights/{user_id}/latest")
    assert response.status_code == 200, f"Get latest weight failed: {response.json()}"
    data = response.json()
    assert data["user_id"] == user_id
    assert data["weight"] == 80.5

if __name__ == "__main__":
    pytest.main()
