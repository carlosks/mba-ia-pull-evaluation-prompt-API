import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_user():
    response = client.post("/users/", json={"email": "test@example.com"})
    assert response.status_code == 200
    assert response.json() == {"email": "test@example.com"}

def test_create_user_invalid_email():
    response = client.post("/users/", json={"email": "invalid-email"})
    assert response.status_code == 422