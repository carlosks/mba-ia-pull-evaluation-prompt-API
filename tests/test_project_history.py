from datetime import datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base
from app.main import app
from app.security import get_current_user, get_db
from app.routes import projects as projects_routes


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


def test_project_history_returns_created_at_with_explicit_utc_timezone(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    current_user = SimpleNamespace(id=1)

    db = TestingSessionLocal()

    project = models.Project(
        bug="Bug de teste para histórico de projetos",
        user_story="User story de teste",
        acceptance_criteria="[]",
        code="",
        score=None,
        status="success",
        zip_path="timestamp-history-test",
        owner_id=current_user.id,
        created_at=datetime(2026, 8, 20, 13, 0, 0),
    )

    db.add(project)
    db.commit()
    db.close()

    monkeypatch.setattr(
        projects_routes,
        "_load_project_history_from_files",
        lambda existing_project_names: [],
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user

    try:
        client = TestClient(app)

        response = client.get("/projects/history")

        assert response.status_code == 200

        data = response.json()

        assert "projects" in data
        assert len(data["projects"]) == 1

        history_project = data["projects"][0]

        assert history_project["project_name"] == "timestamp-history-test"
        assert history_project["created_at"] == "2026-08-20T13:00:00Z"
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
