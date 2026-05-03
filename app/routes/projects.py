from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import models
from app.deps import get_db

router = APIRouter(prefix="/projects")

@router.post("/")
def create_project(bug: str, user_story: str, code: str, db: Session = Depends(get_db)):

    project = models.Project(
        bug=bug,
        user_story=user_story,
        code=code,
        owner_id=1  # depois vira usuário logado
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


@router.get("/")
def list_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()