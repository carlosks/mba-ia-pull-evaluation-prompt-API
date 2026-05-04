from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import uuid
import zipfile

from app import models
from app.deps import get_db
from app.security import get_current_user
from app.schemas.project import ProjectOut, BugRequest
from app.services.generator_service import generate_all

router = APIRouter(tags=["Projects"])  # 🚨 sem prefix aqui


# =========================
# GERAR PROJETO
# =========================
@router.post("/generate", response_model=ProjectOut)
def generate_project(
    request: BugRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    try:
        # 🔥 gerar tudo (IA + evaluator)
        result = generate_all(request.description)

        # salvar no banco
        project = models.Project(
            bug=result["bug"],
            user_story=result["user_story"],
            code=result["api_code"],
            score=str(result["evaluation"]["score"]),
            status=result["evaluation"]["status"],
            owner_id=current_user.id
        )

        db.add(project)
        db.commit()
        db.refresh(project)

        return project

    except Exception as e:
        print("❌ ERRO NO GENERATE:", e)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar projeto: {str(e)}"
        )


# =========================
# LISTAR PROJETOS
# =========================
@router.get("/", response_model=list[ProjectOut])
def list_my_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return db.query(models.Project).filter(
        models.Project.owner_id == current_user.id
    ).all()


# =========================
# DETALHAR PROJETO
# =========================
@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado"
        )

    return project


# =========================
# DELETAR PROJETO
# =========================
@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado"
        )

    db.delete(project)
    db.commit()

    return {"message": "Projeto removido com sucesso"}


# =========================
# DOWNLOAD ZIP DO PROJETO
# =========================
@router.get("/{project_id}/download")
def download_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Projeto não encontrado"
        )

    # pasta temporária
    folder_name = f"generated/{uuid.uuid4()}"
    os.makedirs(folder_name, exist_ok=True)

    # arquivo python
    file_path = os.path.join(folder_name, "app.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(project.code)

    # zip
    zip_path = f"{folder_name}.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        zipf.write(file_path, arcname="app.py")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="project.zip"
    )