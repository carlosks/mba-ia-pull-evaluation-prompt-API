from __future__ import annotations

import os
import re
import json
import zipfile
import tempfile
from pathlib import Path
from typing import List, Optional, Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from app.services.generator_service import generate_all, generate_solution_project
from app.services.project_builder_service import (
    build_project_response,
    build_solution_project_response,
)


router = APIRouter(
    prefix="/projects",
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

    # Remove cercas de código markdown.
    text = re.sub(r"```[a-zA-Z0-9_-]*", "", text)
    text = text.replace("```", "")

    # Converte títulos markdown.
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


# ============================================================
# Endpoints de geração
# ============================================================

@router.post("/generate", response_model=ProjectGenerateResponse)
def generate_project(payload: ProjectGenerateRequest):
    """
    Gera User Story e Critérios de Aceitação a partir de um bug.
    """

    try:
        result = generate_all(payload.bug)

        if not isinstance(result, dict):
            raise ValueError("generate_all não retornou um dicionário válido.")

        return {
            "user_story": result.get("user_story", ""),
            "acceptance_criteria": result.get("acceptance_criteria", []),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar projeto: {str(e)}",
        )


@router.post("/generate-full", response_model=ProjectGenerateFullResponse)
def generate_full_project(payload: ProjectGenerateRequest):
    """
    Gera um projeto básico completo a partir de um bug.
    """

    try:
        result = build_project_response(payload.bug)

        return {
            "project_name": result.get("project_name", ""),
            "project_path": result.get("project_path", ""),
            "user_story": result.get("user_story", ""),
            "acceptance_criteria": result.get("acceptance_criteria", []),
            "files": result.get("files", []),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar projeto completo: {str(e)}",
        )


@router.post("/generate-solution", response_model=ProjectGenerateSolutionResponse)
def generate_solution(payload: ProjectGenerateRequest):
    """
    Gera User Story, Critérios de Aceitação, análise técnica,
    plano de solução e arquivos de projeto.
    """

    try:
        result = build_solution_project_response(payload.bug)

        return {
            "project_name": result.get("project_name"),
            "project_path": result.get("project_path", ""),
            "generation_mode": result.get("generation_mode", "openai_solution"),
            "user_story": result.get("user_story", ""),
            "acceptance_criteria": result.get("acceptance_criteria", []),
            "technical_analysis": result.get("technical_analysis", ""),
            "solution_plan": result.get("solution_plan", []),
            "files": result.get("files", []),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar solução técnica: {str(e)}",
        )


# ============================================================
# Endpoints de consulta dos projetos gerados
# ============================================================

@router.get("/generated", response_model=GeneratedProjectsResponse)
def list_generated_projects():
    """
    Lista todos os projetos gerados.
    """

    GENERATED_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    projects: List[GeneratedProjectSummary] = []

    for project_dir in sorted(GENERATED_PROJECTS_DIR.iterdir()):
        if project_dir.is_dir():
            projects.append(
                GeneratedProjectSummary(
                    project_name=project_dir.name,
                    project_path=str(project_dir.resolve()),
                    files=_list_files(project_dir),
                )
            )

    return {
        "projects": projects
    }


@router.get("/generated/{project_name}/files", response_model=GeneratedProjectFilesResponse)
def list_generated_project_files(project_name: str):
    """
    Lista os arquivos de um projeto gerado específico.
    """

    project_dir = _safe_project_dir(project_name)

    return {
        "project_name": project_name,
        "files": _list_files(project_dir),
    }


@router.get("/generated/{project_name}/files/{filename:path}", response_model=GeneratedProjectFileContentResponse)
def read_generated_project_file(project_name: str, filename: str):
    """
    Lê o conteúdo de um arquivo de um projeto gerado.
    """

    file_path = _safe_file_path(project_name, filename)
    content = _read_text_file(file_path)

    return {
        "project_name": project_name,
        "filename": filename,
        "content": content,
        "size_bytes": file_path.stat().st_size,
    }


@router.get("/generated/{project_name}/files/{filename:path}/word-text")
def read_generated_project_file_as_word_text(project_name: str, filename: str):
    """
    Lê um arquivo gerado e retorna uma versão em texto limpo,
    adequada para copiar e colar no Word.
    """

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


# ============================================================
# Novo endpoint: download ZIP
# ============================================================

@router.get("/generated/{project_name}/download-zip")
def download_generated_project_zip(project_name: str):
    """
    Gera e baixa um arquivo ZIP contendo todos os arquivos
    de um projeto gerado.
    """

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