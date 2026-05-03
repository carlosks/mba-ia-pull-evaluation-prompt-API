# app/models/project.py

from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    bug_description = Column(Text)
    user_story = Column(Text)
    files_json = Column(Text)  # salva estrutura