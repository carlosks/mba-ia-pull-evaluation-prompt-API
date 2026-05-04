# 🚀 Bug → User Story SaaS

SaaS que transforma bugs em:
- User Stories
- APIs FastAPI
- Avaliação automática (score)
- Projeto completo exportável (ZIP)

## 🔐 Funcionalidades

- Auth JWT
- Geração via IA
- Avaliação automática
- Histórico (SQLite)
- Download de projeto completo

## ▶️ Rodar local

```bash
python -m venv venv
venv\Scripts\activate  # Windows

pip install -r requirements.txt
uvicorn app.main:app --reload