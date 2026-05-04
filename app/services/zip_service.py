from pathlib import Path
import shutil
import zipfile
import uuid


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def create_project_zip(api_code: str, project_name: str = "generated_api") -> str:
    project_id = str(uuid.uuid4())

    base_dir = Path("generated")
    project_path = base_dir / f"project_{project_id}"

    if project_path.exists():
        shutil.rmtree(project_path)

    # Pastas
    (project_path / "app" / "routes").mkdir(parents=True, exist_ok=True)
    (project_path / "tests").mkdir(parents=True, exist_ok=True)

    # app/__init__.py
    write_file(project_path / "app" / "__init__.py", "")

    # app/main.py
    write_file(
        project_path / "app" / "main.py",
        """
from fastapi import FastAPI
from app.routes.generated import router as generated_router

app = FastAPI(title="Generated API")

app.include_router(generated_router, prefix="/api", tags=["Generated"])


@app.get("/")
def root():
    return {"message": "Generated API running 🚀"}


@app.get("/health")
def health():
    return {"status": "ok"}
        """
    )

    # app/routes/__init__.py
    write_file(project_path / "app" / "routes" / "__init__.py", "")

    # app/routes/generated.py
    cleaned_api_code = api_code.replace("app = FastAPI()", "").strip()

    write_file(
        project_path / "app" / "routes" / "generated.py",
        f"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, constr

router = APIRouter()

# Código gerado pela IA adaptado para rota modular.
# Revise este arquivo antes de usar em produção.

{cleaned_api_code}
        """
    )

    # requirements.txt
    write_file(
        project_path / "requirements.txt",
        """
fastapi
uvicorn
pydantic
email-validator
        """
    )

    # README.md
    write_file(
        project_path / "README.md",
        f"""
# {project_name}

Projeto FastAPI gerado automaticamente pelo Bug → User Story SaaS.

## Como rodar

1. Criar ambiente virtual:

python -m venv venv

2. Ativar ambiente virtual:

Windows PowerShell:

.\\venv\\Scripts\\Activate.ps1

Linux/Mac:

source venv/bin/activate

3. Instalar dependências:

pip install -r requirements.txt

4. Rodar API:

uvicorn app.main:app --reload

5. Abrir documentação:

http://127.0.0.1:8000/docs
        """
    )

    # .env.example
    write_file(
        project_path / ".env.example",
        """
APP_ENV=development
        """
    )

    # Dockerfile
    write_file(
        project_path / "Dockerfile",
        """
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
        """
    )

    # docker-compose.yml
    write_file(
        project_path / "docker-compose.yml",
        """
services:
  api:
    build: .
    container_name: generated_api
    ports:
      - "8000:8000"
    env_file:
      - .env.example
        """
    )

    # tests/test_basic.py
    write_file(
        project_path / "tests" / "test_basic.py",
        """
def test_basic():
    assert True
        """
    )

    # ZIP
    zip_path = project_path.with_suffix(".zip")

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in project_path.rglob("*"):
            if file_path.is_file():
                zipf.write(file_path, arcname=file_path.relative_to(project_path))

    return str(zip_path)