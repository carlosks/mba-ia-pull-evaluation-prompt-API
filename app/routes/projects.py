from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.generator_service import generate_all, generate_solution_project
from app.services.project_builder_service import (
    build_project_response,
    build_solution_project_response,
)


router = APIRouter(prefix="/projects", tags=["Projects"])


BASE_DIR = Path(__file__).resolve().parents[2]
GENERATED_PROJECTS_DIR = BASE_DIR / "generated_projects"


class ProjectGenerateRequest(BaseModel):
    bug: str


class ProjectGenerateResponse(BaseModel):
    user_story: str
    acceptance_criteria: List[str]


class ProjectGenerateFullResponse(BaseModel):
    project_name: str
    project_path: str
    domain: Optional[str] = None
    user_story: str
    acceptance_criteria: List[str]
    files: List[str]
    endpoints: Optional[List[str]] = None


class ProjectGenerateSolutionResponse(BaseModel):
    project_name: str
    project_path: str
    generation_mode: str
    user_story: str
    acceptance_criteria: List[str]
    technical_analysis: str
    solution_plan: List[str]
    files: List[str]


class GeneratedProjectSummary(BaseModel):
    project_name: str
    project_path: str
    files: List[str]


class GeneratedProjectsResponse(BaseModel):
    projects: List[GeneratedProjectSummary]


class GeneratedProjectFilesResponse(BaseModel):
    project_name: str
    files: List[str]


class GeneratedProjectFileContentResponse(BaseModel):
    project_name: str
    filename: str
    content: str
    size_bytes: int


def get_project_path(project_name: str) -> Path:
    project_path = GENERATED_PROJECTS_DIR / project_name

    if not project_path.exists() or not project_path.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Projeto gerado não encontrado: {project_name}",
        )

    return project_path


def list_project_files(project_path: Path) -> List[str]:
    return sorted([
        item.name
        for item in project_path.iterdir()
        if item.is_file()
    ])


@router.post("/generate", response_model=ProjectGenerateResponse)
def generate_project(payload: ProjectGenerateRequest):
    """
    Gera apenas User Story e Critérios de Aceitação a partir de um bug.
    """
    try:
        result = generate_all(payload.bug)

        return {
            "user_story": result.get("user_story", ""),
            "acceptance_criteria": result.get("acceptance_criteria", []),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar User Story: {str(e)}",
        )


@router.post("/generate-full", response_model=ProjectGenerateFullResponse)
def generate_full_project(payload: ProjectGenerateRequest):
    """
    Gera User Story, Critérios de Aceitação e cria uma estrutura de projeto
    dentro da pasta generated_projects/.
    """
    try:
        result = generate_all(payload.bug)

        user_story = result.get("user_story", "")
        acceptance_criteria = result.get("acceptance_criteria", [])

        project_response = build_project_response(
            bug=payload.bug,
            user_story=user_story,
            acceptance_criteria=acceptance_criteria,
        )

        return project_response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar projeto completo: {str(e)}",
        )


@router.post("/generate-solution", response_model=ProjectGenerateSolutionResponse)
def generate_solution(payload: ProjectGenerateRequest):
    """
    Gera uma solução técnica com código usando OpenAI e grava os arquivos
    dentro da pasta generated_projects/.
    """
    try:
        result = generate_solution_project(payload.bug)

        project_response = build_solution_project_response(
            bug=payload.bug,
            user_story=result.get("user_story", ""),
            acceptance_criteria=result.get("acceptance_criteria", []),
            technical_analysis=result.get("technical_analysis", ""),
            solution_plan=result.get("solution_plan", []),
            files=result.get("files", {}),
        )

        return project_response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar solução técnica: {str(e)}",
        )


@router.get("/generated", response_model=GeneratedProjectsResponse)
def list_generated_projects():
    """
    Lista todos os projetos gerados dentro de generated_projects/.
    """
    if not GENERATED_PROJECTS_DIR.exists():
        return {"projects": []}

    projects = []

    for item in sorted(GENERATED_PROJECTS_DIR.iterdir(), key=lambda p: p.name):
        if item.is_dir():
            projects.append({
                "project_name": item.name,
                "project_path": str(item),
                "files": list_project_files(item),
            })

    return {"projects": projects}


@router.get("/generated/{project_name}/files", response_model=GeneratedProjectFilesResponse)
def list_generated_project_files(project_name: str):
    """
    Lista os arquivos de um projeto gerado específico.
    """
    project_path = get_project_path(project_name)

    return {
        "project_name": project_name,
        "files": list_project_files(project_path),
    }


@router.get(
    "/generated/{project_name}/files/{filename}",
    response_model=GeneratedProjectFileContentResponse,
)
def read_generated_project_file(project_name: str, filename: str):
    """
    Lê o conteúdo de um arquivo gerado, como README.md, main.py ou metadata.json.
    """
    if "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=400,
            detail="Nome de arquivo inválido.",
        )

    project_path = get_project_path(project_name)
    file_path = project_path / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Arquivo não encontrado: {filename}",
        )

    allowed_extensions = {
        ".md",
        ".py",
        ".txt",
        ".json",
        ".yml",
        ".yaml",
    }

    if file_path.suffix.lower() not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não permitido para visualização: {file_path.suffix}",
        )

    content = file_path.read_text(encoding="utf-8")

    return {
        "project_name": project_name,
        "filename": filename,
        "content": content,
        "size_bytes": file_path.stat().st_size,
    }