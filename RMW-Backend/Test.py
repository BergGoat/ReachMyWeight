import pytest
from fastapi.testclient import TestClient
from main import app, calculate_bmr, calculate_tdee, calculate_time

test_client = TestClient(app)

def test_calculate_bmr():
    assert calculate_bmr(70, 175, 25, "male") == 1703.75
    assert calculate_bmr(60, 165, 30, "female") == 1366.25
    with pytest.raises(ValueError):
        calculate_bmr(70, 175, 25, "unknown")

def test_calculate_tdee():
    assert calculate_tdee(1700, "sedentary") == 2040.0
    assert calculate_tdee(1700, "active") == 2932.5
    assert calculate_tdee(1700, "very active") == 3230.0

def test_calculate_time():
    assert calculate_time("Football", 80, 75, 60, 500) > 0
    assert calculate_time("Basketball", 90, 85, 45, 1000) > 0
    assert calculate_time("Tennis", 70, 80, 30, -500) > 0

def test_api_calculate():
    response = test_client.post("/calculate", json={
        "gender": "male",
        "weight": 80,
        "height": 180,
        "age": 28,
        "activity_level": "moderate",
        "sport": ["Football"],
        "aantal_minuten_sporten": 60,
        "gewenst_gewicht": 75,
        "deficit_surplus": -500
    })
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) > 0
    assert "TDEE" in data["results"][0]
    assert "goal" in data["results"][0]
    assert "time_to_reach_goal" in data["results"][0]

if __name__ == "__main__":
    pytest.main()
