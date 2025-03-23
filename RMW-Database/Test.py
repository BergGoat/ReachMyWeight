import pytest
import sqlite3
from fastapi.testclient import TestClient
from main import app, get_db
 
# Test database setup
def override_get_db():
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
 
# User tests
def test_create_user():
    response = client.post("/users", json={"username": "testuser", "password": "securepass"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] > 0
    assert data["username"] == "testuser"
 
def test_login():
    response = client.post("/login", json={"username": "testuser", "password": "securepass"})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "username" in data
 
def test_invalid_login():
    response = client.post("/login", json={"username": "testuser", "password": "wrongpass"})
    assert response.status_code == 401
 
def test_get_user():
    response = client.get("/users/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["username"] == "testuser"
 
# Profile tests
def test_create_profile():
    response = client.post("/profiles", json={
        "user_id": 1,
        "gender": "male",
        "height": 180,
        "age": 25,
        "activity_level": "moderate"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 1
 
def test_get_profile():
    response = client.get("/profiles/1")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 1
    assert data["gender"] == "male"
 
# Weight tests
def test_create_weight():
    response = client.post("/weights", json={
        "user_id": 1,
        "weight": 80.5,
        "goal_weight": 75
    })
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 1
    assert data["weight"] == 80.5
 
def test_get_weights():
    response = client.get("/weights/1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
 
def test_get_latest_weight():
    response = client.get("/weights/1/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 1
    assert data["weight"] == 80.5
 
if __name__ == "__main__":
    pytest.main()
