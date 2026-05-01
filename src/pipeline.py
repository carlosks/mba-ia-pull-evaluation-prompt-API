import os
import json
import re
import ast
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def limpar(texto: str):
    texto = re.sub(r"```json|```python|```", "", texto)
    return texto.strip()


def safe_json_loads(content):
    try:
        return json.loads(content)
    except Exception:
        return None


def codigo_python_valido(codigo: str):
    try:
        ast.parse(codigo)
        return True
    except SyntaxError:
        return False


def melhorar_codigo_python(codigo: str):
    codigo = re.sub(r",?\s*HTTPException", "", codigo)
    codigo = re.sub(r",?\s*Body", "", codigo)
    codigo = re.sub(r"uvicorn\.run\(.*?\)", "", codigo)

    if "from fastapi import FastAPI" in codigo:
        codigo = codigo.replace(
            "from fastapi import FastAPI",
            "from fastapi import FastAPI, Request"
        )

    if "from fastapi.responses import JSONResponse" not in codigo and "JSONResponse" in codigo:
        codigo = "from fastapi.responses import JSONResponse\n" + codigo

    if "from fastapi.exceptions import RequestValidationError" not in codigo and "RequestValidationError" in codigo:
        codigo = "from fastapi.exceptions import RequestValidationError\n" + codigo

    codigo = re.sub(r"['\"]password['\"]\s*:\s*.*?,?", "", codigo)
    codigo = re.sub(r"\n{3,}", "\n\n", codigo).strip()

    return codigo


def gerar_user_story(bug: str):
    prompt = f"""
Gere um JSON válido com:

- user_story
- acceptance_criteria: lista de strings

Retorne apenas JSON.

Bug:
{bug}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}]
    )

    content = limpar(response.choices[0].message.content)

    print("\n=== USER STORY RAW ===\n")
    print(content)
    print("\n======================\n")

    data = safe_json_loads(content)

    if not data:
        return "Erro ao gerar user story", [], {}

    return data.get("user_story", ""), data.get("acceptance_criteria", []), data


def fallback_projeto():
    return {
        "project_name": "fastapi_profissional_fallback",
        "files": {
            "app/main.py": """from fastapi import FastAPI

app = FastAPI(title="API Profissional")

@app.get("/")
def health_check():
    return {"status": "ok"}
""",
            "requirements.txt": "fastapi\nuvicorn\nsqlalchemy\npython-jose[cryptography]\npasslib[bcrypt]\npytest\nhttpx\nemail-validator\n",
            "Dockerfile": """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
            "README.md": "Projeto fallback FastAPI profissional.",
            "tests/test_health.py": """from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
"""
        }
    }


def gerar_api(user_story: str):
    prompt = f"""
Gere apenas código Python FastAPI baseado na User Story.

Regras:
- Código executável
- Sem markdown
- Sem explicações
- Usar Pydantic
- Usar validação
- Não retornar senha
- Mensagens em português

User Story:
{user_story}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}]
    )

    codigo = limpar(response.choices[0].message.content)

    print("\n=== API RAW ===\n")
    print(codigo)
    print("\n================\n")

    codigo = melhorar_codigo_python(codigo)

    if not codigo_python_valido(codigo):
        return fallback_projeto()["files"]["app/main.py"]

    return codigo


def gerar_projeto_completo(user_story: str):
    prompt = f"""
Gere um projeto FastAPI profissional completo.

Retorne APENAS JSON válido neste formato:

{{
  "project_name": "nome_do_projeto",
  "files": {{
    "app/__init__.py": "",
    "app/main.py": "conteúdo",
    "app/database.py": "conteúdo",
    "app/models.py": "conteúdo",
    "app/schemas.py": "conteúdo",
    "app/security.py": "conteúdo",
    "app/routes/__init__.py": "",
    "app/routes/auth.py": "conteúdo",
    "app/routes/users.py": "conteúdo",
    "tests/test_auth.py": "conteúdo",
    "requirements.txt": "conteúdo",
    "Dockerfile": "conteúdo",
    "README.md": "conteúdo"
  }}
}}

Regras obrigatórias:
- FastAPI com arquitetura multi-arquivo
- Banco SQLite com SQLAlchemy
- Autenticação JWT
- Hash de senha com passlib bcrypt
- Endpoint de cadastro de usuário
- Endpoint de login
- Endpoint protegido /users/me
- Validação com Pydantic
- Nunca retornar senha ou hash de senha nas respostas
- Testes com pytest e TestClient
- Dockerfile funcional
- README com instruções de execução
- Sem markdown fora do JSON
- Sem ```json
- Sem explicações fora do JSON

User Story:
{user_story}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}]
    )

    content = limpar(response.choices[0].message.content)

    print("\n=== PROJETO RAW ===\n")
    print(content)
    print("\n===================\n")

    data = safe_json_loads(content)

    if not data or "files" not in data:
        return fallback_projeto()

    files = data["files"]

    if "app/main.py" in files:
        files["app/main.py"] = melhorar_codigo_python(files["app/main.py"])

        if not codigo_python_valido(files["app/main.py"]):
            return fallback_projeto()

    required_files = [
        "app/main.py",
        "requirements.txt",
        "Dockerfile",
        "README.md"
    ]

    for file_name in required_files:
        if file_name not in files:
            return fallback_projeto()

    return data