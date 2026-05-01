from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import shutil
import zipfile

# 🔥 IMPORT DO PIPELINE REAL
from src.pipeline import gerar_user_story, gerar_projeto_completo

router = APIRouter()

# =========================
# INPUT
# =========================
class BugRequest(BaseModel):
    bug: str


# =========================
# GERAR PROJETO (PIPELINE REAL)
# =========================
@router.post("/generate-project")
def generate_project(data: BugRequest):

    bug = data.bug

    # 🔥 ETAPA 1 — GERAR USER STORY
    user_story, acceptance_criteria, _ = gerar_user_story(bug)

    # fallback se falhar
    if not user_story:
        user_story = f"Como usuário, quero corrigir: {bug}"

    if not acceptance_criteria:
        acceptance_criteria = [
            "Sistema deve validar corretamente",
            "Erro deve ser tratado",
            "Resposta deve ser clara"
        ]

    # 🔥 ETAPA 2 — GERAR PROJETO COMPLETO
    resultado = gerar_projeto_completo(user_story)

    files = resultado.get("files", {})

    base_path = "generated"

    # 🔥 LIMPA PROJETO ANTERIOR
    if os.path.exists(base_path):
        shutil.rmtree(base_path)

    os.makedirs(base_path, exist_ok=True)

    # 🔥 SALVA ARQUIVOS GERADOS
    for path, content in files.items():
        full_path = os.path.join(base_path, path)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Erro ao salvar {path}: {e}")

    return {
        "user_story": user_story,
        "acceptance_criteria": acceptance_criteria,
        "message": "Projeto gerado com sucesso"
    }


# =========================
# LISTAR ARQUIVOS
# =========================
@router.get("/get-project-files")
def get_project_files():

    base_path = "generated"
    files = {}

    if not os.path.exists(base_path):
        return {"files": {}}

    for root, _, filenames in os.walk(base_path):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, base_path)

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    files[rel_path] = f.read()
            except Exception as e:
                files[rel_path] = f"[erro ao ler arquivo: {str(e)}]"

    return {"files": files}


# =========================
# DOWNLOAD ZIP
# =========================
@router.get("/download-project")
def download_project():

    base_path = "generated"
    zip_path = "project.zip"

    # remove zip antigo
    if os.path.exists(zip_path):
        os.remove(zip_path)

    # cria zip
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for root, _, files in os.walk(base_path):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, base_path)
                zipf.write(full_path, arcname)

    return FileResponse(
        path=zip_path,
        filename="project.zip",
        media_type="application/zip"
    )