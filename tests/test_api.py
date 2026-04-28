from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_criar_usuario():
    response = client.post("/usuarios", json={
        "nome": "Usuario Teste",
        "email": "usuario@teste.com"
    })
    assert response.status_code == 200
    assert response.json()["nome"] == "Usuario Teste"
    assert response.json()["email"] == "usuario@teste.com"

def test_criar_usuario_email_invalido():
    response = client.post("/usuarios", json={
        "nome": "Usuario Teste",
        "email": "usuario.teste.com"
    })
    assert response.status_code == 422