from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, constr

from pathlib import Path
from textwrap import dedent
from datetime import datetime
import zipfile
import shutil
import uuid

from src.pipeline import gerar_user_story, gerar_api


app = FastAPI(title="Gerador de Projetos SaaS 🚀")


class User(BaseModel):
    username: str
    password: constr(min_length=3)


class BugRequest(BaseModel):
    description: constr(min_length=5)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Dados inválidos",
            "details": [
                {
                    "campo": err["loc"][-1],
                    "mensagem": err["msg"]
                }
                for err in exc.errors()
            ]
        },
    )


@app.get("/")
def root():
    return {"msg": "API funcionando 🚀"}


@app.post("/create-account/")
async def create_account(user: User):
    return {
        "message": "Conta criada com sucesso!",
        "username": user.username
    }


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def build_readme(user_story: str, criteria: list[str]) -> str:
    criteria_text = "\n".join([f"- {item}" for item in criteria]) if criteria else "- Nenhum critério informado"

    return dedent(f"""
    # Generated API

    ## User Story

    {user_story}

    ## Acceptance Criteria

    {criteria_text}

    ## Como rodar

    Instale as dependências:

    pip install -r requirements.txt

    Execute a API:

    uvicorn app.main:app --reload

    Acesse a documentação:

    http://127.0.0.1:8000/docs
    """)


def create_project_files(project_path: Path, user_story: str, criteria: list[str], api_code: str):
    write_file(project_path / "app" / "__init__.py", "")

    write_file(
        project_path / "app" / "main.py",
        """
from fastapi import FastAPI
from app.routes.api import router

app = FastAPI(title="Generated API")

app.include_router(router, prefix="/api", tags=["Generated"])

@app.get("/")
def root():
    return {"message": "API running 🚀"}
        """
    )

    write_file(project_path / "app" / "routes" / "__init__.py", "")

    write_file(
        project_path / "app" / "routes" / "api.py",
        api_code if api_code else """
from fastapi import APIRouter

router = APIRouter()

@router.post("/execute")
def execute():
    return {"message": "Endpoint funcionando"}
        """
    )

    write_file(
        project_path / "app" / "models.py",
        """
from pydantic import BaseModel

class Input(BaseModel):
    data: str
        """
    )

    write_file(
        project_path / "app" / "database.py",
        """
def connect():
    return "connected"
        """
    )

    write_file(
        project_path / "tests" / "test_basic.py",
        """
def test_basic():
    assert True
        """
    )

    write_file(
        project_path / "requirements.txt",
        """
fastapi
uvicorn
pydantic
        """
    )

    write_file(
        project_path / "Dockerfile",
        """
FROM python:3.11

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
        """
    )

    write_file(project_path / "README.md", build_readme(user_story, criteria))


def zip_project(project_path: Path) -> Path:
    zip_path = project_path.with_suffix(".zip")

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in project_path.rglob("*"):
            if file_path.is_file():
                zipf.write(file_path, arcname=file_path.relative_to(project_path))

    return zip_path


@app.post("/generate-project")
def generate_project(data: BugRequest):
    try:
        bug = data.description

        user_story, criteria, raw = gerar_user_story(bug)
        api_code = gerar_api(user_story)

        return {
            "bug": bug,
            "user_story": user_story,
            "acceptance_criteria": criteria,
            "api_code": api_code
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/download-project")
def download_project(data: BugRequest):
    try:
        bug = data.description

        user_story, criteria, raw = gerar_user_story(bug)
        api_code = gerar_api(user_story)

        project_id = str(uuid.uuid4())
        base_dir = Path("generated")
        project_path = base_dir / f"project_{project_id}"

        if project_path.exists():
            shutil.rmtree(project_path)

        create_project_files(project_path, user_story, criteria, api_code)
        zip_path = zip_project(project_path)

        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename="project.zip"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))