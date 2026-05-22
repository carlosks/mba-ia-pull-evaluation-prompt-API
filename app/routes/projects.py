from __future__ import annotations

import json
import os
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app import models
from app.security import get_current_user, get_db
from app.services.generator_service import generate_all, generate_solution_project
from app.services.project_builder_service import (
    build_project_response,
    build_solution_project_response,
)
from app.services.usage_service import (
    assert_user_can_generate,
    register_usage,
)


router = APIRouter(
    tags=["Projects"],
)


# Pasta onde os projetos gerados são salvos.
# No Render ficará algo como /app/generated_projects.
# Localmente ficará dentro da raiz do projeto.
GENERATED_PROJECTS_DIR = Path("generated_projects")
GENERATED_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Schemas
# ============================================================

class ProjectGenerateRequest(BaseModel):
    bug: str = Field(
        ...,
        min_length=5,
        description="Descrição do bug que será transformado em User Story, critérios e/ou solução técnica.",
    )


class ProjectGenerateResponse(BaseModel):
    user_story: str
    acceptance_criteria: List[str]


class ProjectGenerateFullResponse(BaseModel):
    project_name: str
    project_path: str
    user_story: str
    acceptance_criteria: List[str]
    files: List[str]


class ProjectGenerateSolutionResponse(BaseModel):
    project_name: Optional[str] = None
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


class ProjectHistoryItem(BaseModel):
    id: int
    project_name: str
    bug: str
    status: Optional[str] = None
    created_at: str


class ProjectHistoryResponse(BaseModel):
    projects: List[ProjectHistoryItem]


# ============================================================
# Funções auxiliares
# ============================================================

def _safe_project_dir(project_name: str) -> Path:
    """
    Retorna o caminho seguro da pasta do projeto gerado.

    Protege contra path traversal, por exemplo:
    ../../arquivo
    """

    if not project_name or project_name.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Nome do projeto não informado.",
        )

    base_dir = GENERATED_PROJECTS_DIR.resolve()
    project_dir = (base_dir / project_name).resolve()

    if not str(project_dir).startswith(str(base_dir)):
        raise HTTPException(
            status_code=400,
            detail="Nome de projeto inválido.",
        )

    if not project_dir.exists() or not project_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Projeto gerado não encontrado: {project_name}",
        )

    return project_dir


def _safe_file_path(project_name: str, filename: str) -> Path:
    """
    Retorna o caminho seguro de um arquivo dentro de um projeto gerado.
    """

    if not filename or filename.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Nome do arquivo não informado.",
        )

    project_dir = _safe_project_dir(project_name)
    file_path = (project_dir / filename).resolve()

    if not str(file_path).startswith(str(project_dir.resolve())):
        raise HTTPException(
            status_code=400,
            detail="Nome de arquivo inválido.",
        )

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Arquivo não encontrado: {filename}",
        )

    return file_path


def _list_files(project_dir: Path) -> List[str]:
    """
    Lista arquivos de um projeto gerado.
    """

    files: List[str] = []

    for path in sorted(project_dir.rglob("*")):
        if path.is_file():
            files.append(str(path.relative_to(project_dir)).replace("\\", "/"))

    return files


def _read_text_file(file_path: Path) -> str:
    """
    Lê arquivo de texto usando UTF-8.
    """

    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return file_path.read_text(encoding="latin-1")


def _markdown_to_word_text(content: str) -> str:
    """
    Converte Markdown simples em texto limpo para copiar no Word.
    """

    if not content:
        return ""

    text = content

    # Remove cercas de código Markdown.
    text = re.sub(r"```[a-zA-Z0-9_-]*", "", text)
    text = text.replace("```", "")

    # Converte títulos Markdown.
    text = re.sub(r"^#\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^##\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^###\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^####\s+", "", text, flags=re.MULTILINE)

    # Remove negrito/itálico simples.
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("*", "")

    # Limpa múltiplas linhas em branco.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _dict_to_clean_text(data: Dict[str, Any]) -> str:
    """
    Converte JSON/dict em texto limpo para Word.
    """

    lines: List[str] = []

    project_name = data.get("project_name")
    filename = data.get("filename")
    content = data.get("content")

    if project_name:
        lines.append(f"Projeto: {project_name}")

    if filename:
        lines.append(f"Arquivo: {filename}")

    if project_name or filename:
        lines.append("")

    if content:
        lines.append(_markdown_to_word_text(str(content)))
    else:
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False, indent=2)
            lines.append(f"{key}: {value}")

    return "\n".join(lines).strip()


def _require_project_owner(
    project_name: str,
    db: Session,
    current_user: models.User,
) -> models.Project:
    """
    Garante que o projeto pertence ao usuário autenticado.

    Nesta versão, o campo zip_path armazena o project_name.
    """

    project = db.query(models.Project).filter(
        models.Project.zip_path == project_name,
        models.Project.owner_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para acessar este projeto.",
        )

    return project


def _save_project_history(
    db: Session,
    current_user: models.User,
    bug: str,
    user_story: str,
    acceptance_criteria: List[str],
    project_name: Optional[str],
    project_path: str,
    files: List[str],
    technical_analysis: Optional[str] = None,
    solution_plan: Optional[List[str]] = None,
    status: str = "generated",
) -> models.Project:
    """
    Salva o histórico do projeto gerado para o usuário autenticado.
    """

    history = models.Project(
        bug=bug,
        user_story=user_story or "",
        acceptance_criteria=json.dumps(
            acceptance_criteria or [],
            ensure_ascii=False,
        ),
        code=json.dumps(
            {
                "project_name": project_name,
                "project_path": project_path,
                "technical_analysis": technical_analysis,
                "solution_plan": solution_plan or [],
                "files": files or [],
            },
            ensure_ascii=False,
        ),
        score=None,
        status=status,
        zip_path=project_name,
        owner_id=current_user.id,
    )

    db.add(history)
    db.commit()
    db.refresh(history)

    return history


# ============================================================
# Endpoints de geração protegidos com limite mensal
# ============================================================

@router.post("/generate", response_model=ProjectGenerateResponse)
def generate_project(
    payload: ProjectGenerateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Gera User Story e Critérios de Aceitação a partir de um bug.
    Endpoint protegido por autenticação e limite mensal de uso.
    """

    assert_user_can_generate(db, current_user)

    try:
        result = generate_all(payload.bug)

        if not isinstance(result, dict):
            raise ValueError("generate_all não retornou um dicionário válido.")

        register_usage(
            db=db,
            user=current_user,
            endpoint="/projects/generate",
            project_name=None,
            status="success",
        )

        return {
            "user_story": result.get("user_story", ""),
            "acceptance_criteria": result.get("acceptance_criteria", []),
        }

    except HTTPException:
        raise

    except Exception as e:
        register_usage(
            db=db,
            user=current_user,
            endpoint="/projects/generate",
            project_name=None,
            status="failed",
        )

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar projeto: {str(e)}",
        )


@router.post("/generate-full", response_model=ProjectGenerateFullResponse)
def generate_full_project(
    payload: ProjectGenerateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Gera um projeto básico completo a partir de um bug.
    Endpoint protegido por autenticação e limite mensal de uso.
    """

    assert_user_can_generate(db, current_user)

    try:
        result = build_project_response(payload.bug)

        project_name = result.get("project_name", "")
        project_path = result.get("project_path", "")
        user_story = result.get("user_story", "")
        acceptance_criteria = result.get("acceptance_criteria", [])
        files = result.get("files", [])

        _save_project_history(
            db=db,
            current_user=current_user,
            bug=payload.bug,
            user_story=user_story,
            acceptance_criteria=acceptance_criteria,
            project_name=project_name,
            project_path=project_path,
            files=files,
            technical_analysis=None,
            solution_plan=[],
            status="generated_full",
        )

        register_usage(
            db=db,
            user=current_user,
            endpoint="/projects/generate-full",
            project_name=project_name,
            status="success",
        )

        return {
            "project_name": project_name,
            "project_path": project_path,
            "user_story": user_story,
            "acceptance_criteria": acceptance_criteria,
            "files": files,
        }

    except HTTPException:
        raise

    except Exception as e:
        register_usage(
            db=db,
            user=current_user,
            endpoint="/projects/generate-full",
            project_name=None,
            status="failed",
        )

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar projeto completo: {str(e)}",
        )


@router.post("/generate-solution", response_model=ProjectGenerateSolutionResponse)
def generate_solution(
    payload: ProjectGenerateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Gera User Story, Critérios de Aceitação, análise técnica,
    plano de solução e arquivos de projeto.
    Endpoint protegido por autenticação e limite mensal de uso.
    """

    assert_user_can_generate(db, current_user)

    try:
        solution = generate_solution_project(payload.bug)

        result = build_solution_project_response(
            payload.bug,
            solution.get("user_story", ""),
            solution.get("acceptance_criteria", []),
            solution.get("technical_analysis", ""),
            solution.get("solution_plan", []),
            solution.get("files", {}),
        )

        project_name = result.get("project_name")
        project_path = result.get("project_path", "")
        user_story = result.get("user_story", "")
        acceptance_criteria = result.get("acceptance_criteria", [])
        technical_analysis = result.get("technical_analysis", "")
        solution_plan = result.get("solution_plan", [])
        files = result.get("files", [])

        _save_project_history(
            db=db,
            current_user=current_user,
            bug=payload.bug,
            user_story=user_story,
            acceptance_criteria=acceptance_criteria,
            project_name=project_name,
            project_path=project_path,
            files=files,
            technical_analysis=technical_analysis,
            solution_plan=solution_plan,
            status="generated_solution",
        )

        register_usage(
            db=db,
            user=current_user,
            endpoint="/projects/generate-solution",
            project_name=project_name,
            status="success",
        )

        return {
            "project_name": project_name,
            "project_path": project_path,
            "generation_mode": result.get("generation_mode", "openai_solution"),
            "user_story": user_story,
            "acceptance_criteria": acceptance_criteria,
            "technical_analysis": technical_analysis,
            "solution_plan": solution_plan,
            "files": files,
        }

    except HTTPException:
        raise

    except Exception as e:
        register_usage(
            db=db,
            user=current_user,
            endpoint="/projects/generate-solution",
            project_name=None,
            status="failed",
        )

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar solução técnica: {str(e)}",
        )


# ============================================================
# Histórico do usuário autenticado
# ============================================================

@router.get("/history", response_model=ProjectHistoryResponse)
def get_project_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Lista o histórico de projetos gerados pelo usuário autenticado.
    """

    projects = db.query(models.Project).filter(
        models.Project.owner_id == current_user.id
    ).order_by(models.Project.created_at.desc()).all()

    return {
        "projects": [
            ProjectHistoryItem(
                id=project.id,
                project_name=project.zip_path or "",
                bug=project.bug,
                status=project.status,
                created_at=project.created_at.isoformat()
                if project.created_at
                else "",
            )
            for project in projects
        ]
    }


# ============================================================
# Endpoints de consulta dos projetos gerados protegidos
# ============================================================

@router.get("/generated", response_model=GeneratedProjectsResponse)
def list_generated_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Lista somente os projetos gerados pelo usuário autenticado.
    """

    GENERATED_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    user_projects = db.query(models.Project).filter(
        models.Project.owner_id == current_user.id
    ).order_by(models.Project.created_at.desc()).all()

    projects: List[GeneratedProjectSummary] = []

    for project in user_projects:
        project_name = project.zip_path

        if not project_name:
            continue

        project_dir = GENERATED_PROJECTS_DIR / project_name

        if project_dir.exists() and project_dir.is_dir():
            projects.append(
                GeneratedProjectSummary(
                    project_name=project_name,
                    project_path=str(project_dir.resolve()),
                    files=_list_files(project_dir),
                )
            )

    return {
        "projects": projects
    }


@router.get("/generated/{project_name}/files", response_model=GeneratedProjectFilesResponse)
def list_generated_project_files(
    project_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Lista os arquivos de um projeto gerado específico,
    desde que ele pertença ao usuário autenticado.
    """

    _require_project_owner(project_name, db, current_user)

    project_dir = _safe_project_dir(project_name)

    return {
        "project_name": project_name,
        "files": _list_files(project_dir),
    }


@router.get("/generated/{project_name}/files/{filename:path}/word-text")
def read_generated_project_file_as_word_text(
    project_name: str,
    filename: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Lê um arquivo gerado e retorna uma versão em texto limpo,
    adequada para copiar e colar no Word,
    desde que o projeto pertença ao usuário autenticado.
    """

    _require_project_owner(project_name, db, current_user)

    file_path = _safe_file_path(project_name, filename)
    content = _read_text_file(file_path)

    # Se o conteúdo for JSON, tenta converter em texto limpo.
    try:
        parsed = json.loads(content)

        if isinstance(parsed, dict):
            clean_text = _dict_to_clean_text(parsed)
        else:
            clean_text = json.dumps(parsed, ensure_ascii=False, indent=2)

    except json.JSONDecodeError:
        clean_text = _markdown_to_word_text(content)

    return {
        "project_name": project_name,
        "filename": filename,
        "content": clean_text,
        "size_bytes": len(clean_text.encode("utf-8")),
    }


@router.get("/generated/{project_name}/files/{filename:path}", response_model=GeneratedProjectFileContentResponse)
def read_generated_project_file(
    project_name: str,
    filename: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Lê o conteúdo de um arquivo de um projeto gerado,
    desde que ele pertença ao usuário autenticado.
    """

    _require_project_owner(project_name, db, current_user)

    file_path = _safe_file_path(project_name, filename)
    content = _read_text_file(file_path)

    return {
        "project_name": project_name,
        "filename": filename,
        "content": content,
        "size_bytes": file_path.stat().st_size,
    }


# ============================================================
# Download ZIP protegido
# ============================================================

@router.get("/generated/{project_name}/download-zip")
def download_generated_project_zip(
    project_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Gera e baixa um arquivo ZIP contendo todos os arquivos
    de um projeto gerado, desde que pertença ao usuário autenticado.
    """

    _require_project_owner(project_name, db, current_user)

    project_dir = _safe_project_dir(project_name)

    zip_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    zip_path = zip_temp.name
    zip_temp.close()

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in project_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(project_dir)
                    zip_file.write(file_path, arcname=str(arcname))

        download_filename = f"{project_name}.zip"

        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=download_filename,
            background=BackgroundTask(
                lambda: os.remove(zip_path) if os.path.exists(zip_path) else None
            ),
        )

    except Exception as e:
        if os.path.exists(zip_path):
            os.remove(zip_path)

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar ZIP do projeto: {str(e)}",
        )