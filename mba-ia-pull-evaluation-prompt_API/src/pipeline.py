# src/pipeline.py

from dotenv import load_dotenv
from langchain import hub
from langchain.prompts import ChatPromptTemplate
from src.utils import get_llm
import yaml
import os
import subprocess

load_dotenv()

llm = get_llm()


# =========================================================
# CARREGAR PROMPT (HUB + LOCAL + JINJA2)
# =========================================================
def carregar_prompt(nome: str):
    owner = os.getenv("LANGSMITH_HUB_OWNER", "carlosks")

    # 🔹 tentar Hub
    try:
        print(f"🌐 Tentando Hub: {owner}/{nome}")
        return hub.pull(f"{owner}/{nome}")
    except Exception:
        print("⚠️ Hub não encontrado → usando local")

    # 🔹 fallback local
    path = f"prompts/{nome}.yml"

    if not os.path.exists(path):
        raise FileNotFoundError(f"Prompt não encontrado: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    messages = [(p["role"], p["content"]) for p in data["prompts"]]

    print(f"📁 Usando local: {path}")

    return ChatPromptTemplate.from_messages(
        messages,
        template_format="jinja2"  # evita erro com {}
    )


# =========================================================
# BUG → USER STORY
# =========================================================
def gerar_user_story(bug_report: str) -> str:
    prompt = carregar_prompt("bug_to_user_story_v18")

    result = (prompt | llm).invoke({
        "bug_report": bug_report
    })

    return result.content


# =========================================================
# USER STORY → API
# =========================================================
def gerar_api(user_story: str) -> str:
    prompt = carregar_prompt("user_story_to_api_v1")

    result = (prompt | llm).invoke({
        "user_story": user_story
    })

    return result.content


# =========================================================
# USER STORY → CÓDIGO SIMPLES
# =========================================================
def gerar_codigo(user_story: str) -> str:
    prompt = carregar_prompt("user_story_to_code_v1")

    result = (prompt | llm).invoke({
        "user_story": user_story
    })

    return result.content


# =========================================================
# SALVAR ARQUIVOS GERADOS
# =========================================================
def salvar_arquivos(codigo: str):
    arquivos = {}
    atual = None
    buffer = []

    for linha in codigo.split("\n"):

        if linha.startswith("###"):
            if atual and buffer:
                arquivos[atual] = "\n".join(buffer).strip()
                buffer = []

            atual = linha.replace("###", "").strip()
            continue

        if "```" in linha:
            continue

        if atual:
            buffer.append(linha)

    if atual and buffer:
        arquivos[atual] = "\n".join(buffer).strip()

    for path, conteudo in arquivos.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(conteudo)

    print("\n✅ Arquivos gerados:")
    for path in arquivos:
        print(f" - {path}")


# =========================================================
# GERAR REQUIREMENTS.TXT
# =========================================================
def gerar_requirements():
    conteudo = """fastapi
uvicorn
pydantic
sqlalchemy
pytest
"""

    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(conteudo)

    print("\n📦 requirements.txt gerado!")


# =========================================================
# PIPELINE PRINCIPAL
# =========================================================
def executar_pipeline():

    print("\n========================================")
    print("🚀 PIPELINE: Bug → API AUTOMÁTICA")
    print("========================================")

    bug_report = input("\n🪲 Digite o bug:\n\n")

    # 1. USER STORY
    print("\n🔄 Gerando User Story...\n")
    user_story = gerar_user_story(bug_report)
    print(user_story)

    # 2. ESCOLHA
    print("\nEscolha:")
    print("1 - API completa")
    print("2 - Código simples")

    opcao = input("\nOpção: ").strip()

    # 3. GERAÇÃO
    if opcao == "1":
        print("\n🔄 Gerando API...\n")
        codigo = gerar_api(user_story)
    else:
        print("\n🔄 Gerando código...\n")
        codigo = gerar_codigo(user_story)

    # 4. RESULTADO
    print("\n================ RESULTADO ================\n")
    print(codigo)

    # 5. SALVAR
    salvar = input("\n💾 Salvar arquivos? (s/n): ").lower()

    if salvar == "s":
        salvar_arquivos(codigo)
        gerar_requirements()


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    executar_pipeline()