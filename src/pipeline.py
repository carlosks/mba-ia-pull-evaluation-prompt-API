import os
import json
import yaml
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate
from src.utils import get_llm

# ================================
# CONFIG
# ================================
load_dotenv()
llm = get_llm()


# ================================
# CARREGAR PROMPT (Hub + Local)
# ================================
def carregar_prompt(nome):
    try:
        print(f"\n🌐 Tentando Hub: carlosks/{nome}")
        return hub.pull(f"carlosks/{nome}")
    except Exception:
        print("⚠️ Hub não encontrado → usando local")

    path = f"prompts/{nome}.yml"

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    print(f"📁 Usando local: {path}")

    return ChatPromptTemplate.from_messages([
        (msg["role"], msg["content"])
        for msg in data["prompts"]
    ])


# ================================
# GERAR USER STORY (JSON)
# ================================
def gerar_user_story(bug_report):
    prompt = carregar_prompt("bug_to_user_story_v18")

    result = (prompt | llm).invoke({
        "bug_report": bug_report
    })

    try:
        data = json.loads(result.content)

        user_story = data["user_story"]
        criterios = data["acceptance_criteria"]

        return user_story, criterios, data

    except Exception as e:
        print("\n❌ Erro ao converter JSON:")
        print(e)
        print("\n📦 Resposta bruta:\n", result.content)
        return None, None, None


# ================================
# GERAR API
# ================================
def gerar_api(user_story):
    prompt = carregar_prompt("user_story_to_api_v1")

    result = (prompt | llm).invoke({
        "user_story": user_story
    })

    return result.content


# ================================
# SALVAR ARQUIVOS GERADOS
# ================================
def salvar_arquivos(codigo):
    arquivos = {
        "app/schemas.py": "",
        "app/service.py": "",
        "app/main.py": "",
        "tests/test_api.py": ""
    }

    current_file = None

    for line in codigo.split("\n"):
        if "### app/schemas.py" in line:
            current_file = "app/schemas.py"
            continue
        elif "### app/service.py" in line:
            current_file = "app/service.py"
            continue
        elif "### app/main.py" in line:
            current_file = "app/main.py"
            continue
        elif "### tests/test_api.py" in line:
            current_file = "tests/test_api.py"
            continue

        if current_file and not line.startswith("```"):
            arquivos[current_file] += line + "\n"

    # criar pastas
    os.makedirs("app", exist_ok=True)
    os.makedirs("tests", exist_ok=True)

    # salvar arquivos
    for path, content in arquivos.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip())

    print("\n✅ Arquivos gerados:")
    for path in arquivos:
        print(f" - {path}")


# ================================
# GERAR REQUIREMENTS
# ================================
def gerar_requirements():
    content = """fastapi
uvicorn
pydantic
pytest
python-dotenv
langchain
openai
jinja2
"""

    with open("requirements.txt", "w") as f:
        f.write(content)

    print("\n📦 requirements.txt gerado!")


# ================================
# PIPELINE PRINCIPAL
# ================================
def executar_pipeline():
    print("\n🔥 USANDO MODELO:", llm.model_name)
    print("\n========================================")
    print("🚀 PIPELINE: Bug → API AUTOMÁTICA")
    print("========================================\n")

    bug_report = input("🪲 Digite o bug:\n\n")

    # ===== USER STORY =====
    print("\n🔄 Gerando User Story...\n")

    user_story, criterios, data = gerar_user_story(bug_report)

    if not user_story:
        return

    print("\n📘 USER STORY:\n")
    print(user_story)

    print("\n✅ CRITÉRIOS DE ACEITAÇÃO:\n")
    for c in criterios:
        print(f"- {c}")

    # salvar JSON estruturado
    os.makedirs("output", exist_ok=True)

    with open("output/user_story.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("\n💾 JSON salvo em: output/user_story.json")

    # ===== ESCOLHA =====
    print("\nEscolha:")
    print("1 - API completa")
    print("2 - Código simples\n")

    opcao = input("Opção: ")

    if opcao != "1":
        print("\n⚠️ Opção inválida ou não implementada")
        return

    # ===== GERAR API =====
    print("\n🔄 Gerando API...\n")

    codigo = gerar_api(user_story)

    print("\n================ RESULTADO ================\n")
    print(codigo)

    salvar = input("\n💾 Salvar arquivos? (s/n): ")

    if salvar.lower() == "s":
        salvar_arquivos(codigo)
        gerar_requirements()


# ================================
# EXECUTAR
# ================================
if __name__ == "__main__":
    executar_pipeline()