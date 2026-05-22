from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


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

    created_at = Column(DateTime, default=datetime.utcnow)

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

    created_at = Column(DateTime, default=datetime.utcnow)

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

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="usage_logs")