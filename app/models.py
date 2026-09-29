from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Plano comercial do usuário.
    # Valores previstos:
    # free, pro, team, admin
    plan = Column(String, nullable=False, default="free")

    # Limite mensal de gerações.
    # Free = 5
    # Pro = 100
    # Team = 1000
    # Admin = -1, ilimitado
    monthly_generation_limit = Column(Integer, nullable=False, default=5)

    # Controle administrativo.
    is_active = Column(Boolean, nullable=False, default=True)
    is_admin = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=utc_now)

    projects = relationship(
        "Project",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    usage_logs = relationship(
        "UsageLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    bug = Column(Text, nullable=False)
    user_story = Column(Text, nullable=False)
    acceptance_criteria = Column(Text)

    code = Column(Text, nullable=False)

    score = Column(String)
    status = Column(String)

    # Nesta aplicação, zip_path também é usado para armazenar o project_name.
    zip_path = Column(String)

    created_at = Column(DateTime, default=utc_now)

    owner_id = Column(Integer, ForeignKey("users.id"))


    owner = relationship("User", back_populates="projects")


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Endpoint que consumiu uso:
    # /projects/generate
    # /projects/generate-full
    # /projects/generate-solution
    endpoint = Column(String, nullable=False)

    # Nome do projeto gerado, quando existir.
    project_name = Column(String)

    # Status do uso:
    # success, failed, blocked
    status = Column(String, nullable=False, default="success")

    # Consumo do LLM nesta geração (para medir margem por plano).
    model = Column(String)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    cost_usd = Column(Float)
    duration_ms = Column(Integer)

    created_at = Column(DateTime, default=utc_now, index=True)

    user = relationship("User", back_populates="usage_logs")


class GenerationJob(Base):
    """
    Geração executada em segundo plano.

    O cliente cria o job, recebe o id na hora e consulta o status
    até ficar succeeded ou failed. Assim a requisição HTTP não fica
    presa esperando o LLM.
    """

    __tablename__ = "generation_jobs"

    id = Column(String(36), primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # generate | generate-full | generate-solution
    kind = Column(String, nullable=False)

    # queued | running | succeeded | failed
    status = Column(String, nullable=False, default="queued", index=True)

    bug = Column(Text, nullable=False)

    # Resposta completa (JSON) quando succeeded.
    result_json = Column(Text)

    # Mensagem amigável quando failed (sem detalhes internos).
    error_message = Column(Text)

    project_name = Column(String)

    created_at = Column(DateTime, default=utc_now, index=True)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)