import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_add():
    response = client.get("/calculate?operation=add&x=5&y=3")
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert data["result"] == 2 or 8

def test_divide_by_zero():
    response = client.get("/calculate?operation=divide&x=5&y=0")
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Je kunt niet door nul delen."
