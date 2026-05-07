import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
GENERATED_PROJECTS_DIR = os.path.join(BASE_DIR, "generated_projects")


# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================

def slugify(text: str) -> str:
    """
    Converte texto em nome seguro para pasta/arquivo.
    """
    if not text:
        return "projeto-gerado"

    text = text.lower().strip()

    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }

    for original, replacement in replacements.items():
        text = text.replace(original, replacement)

    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")

    if not text:
        text = "projeto-gerado"

    return text[:60]


def normalize_text(text: str) -> str:
    """
    Normaliza texto para detecção simples de domínio.
    """
    if not text:
        return ""

    text = text.lower()

    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }

    for original, replacement in replacements.items():
        text = text.replace(original, replacement)

    return text


def ensure_generated_dir() -> None:
    """
    Garante que generated_projects exista.
    """
    os.makedirs(GENERATED_PROJECTS_DIR, exist_ok=True)


def build_project_name(bug: str, suffix: Optional[str] = None) -> str:
    """
    Cria nome de projeto a partir do bug.
    """
    slug = slugify(bug)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if suffix:
        suffix_slug = slugify(suffix)
        return f"{slug}_{suffix_slug}_{timestamp}"

    return f"{slug}_{timestamp}"


def write_file(path: str, content: str) -> None:
    """
    Escreve arquivo em UTF-8.
    """
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def safe_filename(filename: str) -> str:
    """
    Evita nomes perigosos vindos do modelo.
    """
    filename = filename.strip().replace("\\", "/")
    filename = filename.split("/")[-1]

    if not filename:
        return "arquivo.txt"

    return filename


def format_acceptance_criteria(criteria: List[str]) -> str:
    """
    Formata critérios em Markdown.
    """
    if not criteria:
        return "Nenhum critério de aceitação gerado."

    lines = []

    for item in criteria:
        item = str(item).strip()
        if item:
            lines.append(f"- {item}")

    return "\n".join(lines)


def detect_domain(bug: str) -> str:
    """
    Detecta domínio simples para o fluxo antigo generate-full.
    """
    text = normalize_text(bug)

    fornecedor_terms = [
        "fornecedor",
        "fornecedores",
        "cnpj",
        "endereco",
        "endereço",
        "contato",
        "contatos",
        "cadastro",
        "cadastrar",
    ]

    if any(term in text for term in fornecedor_terms):
        return "fornecedor"

    return "generic"


# ============================================================
# FLUXO ANTIGO — GERAÇÃO BÁSICA /generate-full
# Mantido para não quebrar endpoints existentes.
# ============================================================

def generate_generic_fastapi_code(
    project_title: str,
    bug: str,
    user_story: str,
    acceptance_criteria: List[str],
) -> str:
    bug_json = json.dumps(bug, ensure_ascii=False)
    user_story_json = json.dumps(user_story, ensure_ascii=False)
    acceptance_criteria_json = json.dumps(
        acceptance_criteria,
        ensure_ascii=False,
        indent=4,
    )

    lines = [
        "from fastapi import FastAPI",
        "from pydantic import BaseModel",
        "from typing import List",
        "",
        "",
        "class UserStoryResponse(BaseModel):",
        "    user_story: str",
        "",
        "",
        "class AcceptanceCriteriaResponse(BaseModel):",
        "    acceptance_criteria: List[str]",
        "",
        "",
        "class MetadataResponse(BaseModel):",
        "    project_name: str",
        "    bug: str",
        "    user_story: str",
        "    acceptance_criteria: List[str]",
        "",
        "",
        f'PROJECT_NAME = "{project_title}"',
        f"BUG = {bug_json}",
        f"USER_STORY = {user_story_json}",
        f"ACCEPTANCE_CRITERIA = {acceptance_criteria_json}",
        "",
        "",
        "app = FastAPI(",
        f'    title="{project_title}",',
        '    description="API gerada automaticamente a partir de uma User Story.",',
        '    version="1.0.0"',
        ")",
        "",
        "",
        '@app.get("/")',
        "def root():",
        '    return {"msg": "Projeto gerado com sucesso 🚀", "project_name": PROJECT_NAME}',
        "",
        "",
        '@app.get("/health")',
        "def health():",
        '    return {"status": "ok"}',
        "",
        "",
        '@app.get("/user-story", response_model=UserStoryResponse)',
        "def get_user_story():",
        '    return {"user_story": USER_STORY}',
        "",
        "",
        '@app.get("/acceptance-criteria", response_model=AcceptanceCriteriaResponse)',
        "def get_acceptance_criteria():",
        '    return {"acceptance_criteria": ACCEPTANCE_CRITERIA}',
        "",
        "",
        '@app.get("/metadata", response_model=MetadataResponse)',
        "def get_metadata():",
        "    return {",
        '        "project_name": PROJECT_NAME,',
        '        "bug": BUG,',
        '        "user_story": USER_STORY,',
        '        "acceptance_criteria": ACCEPTANCE_CRITERIA,',
        "    }",
        "",
    ]

    return "\n".join(lines)


def generate_fornecedor_fastapi_code(
    project_title: str,
    bug: str,
    user_story: str,
    acceptance_criteria: List[str],
) -> str:
    bug_json = json.dumps(bug, ensure_ascii=False)
    user_story_json = json.dumps(user_story, ensure_ascii=False)
    acceptance_criteria_json = json.dumps(
        acceptance_criteria,
        ensure_ascii=False,
        indent=4,
    )

    lines = [
        "from fastapi import FastAPI, HTTPException",
        "from pydantic import BaseModel, Field",
        "from typing import List, Optional",
        "from uuid import uuid4",
        "",
        "",
        "class Contato(BaseModel):",
        "    nome: str",
        "    email: Optional[str] = None",
        "    telefone: Optional[str] = None",
        "",
        "",
        "class Endereco(BaseModel):",
        "    logradouro: str",
        "    numero: str",
        "    bairro: str",
        "    cidade: str",
        "    uf: str = Field(..., min_length=2, max_length=2)",
        "    cep: str",
        "",
        "",
        "class FornecedorCreate(BaseModel):",
        "    razao_social: str",
        "    cnpj: str = Field(..., min_length=14, max_length=18)",
        "    endereco: Endereco",
        "    contatos: List[Contato]",
        "",
        "",
        "class FornecedorResponse(FornecedorCreate):",
        "    id: str",
        "    mensagem: str",
        "",
        "",
        "class UserStoryResponse(BaseModel):",
        "    user_story: str",
        "",
        "",
        "class AcceptanceCriteriaResponse(BaseModel):",
        "    acceptance_criteria: List[str]",
        "",
        "",
        "class MetadataResponse(BaseModel):",
        "    project_name: str",
        "    bug: str",
        "    user_story: str",
        "    acceptance_criteria: List[str]",
        "",
        "",
        f'PROJECT_NAME = "{project_title}"',
        f"BUG = {bug_json}",
        f"USER_STORY = {user_story_json}",
        f"ACCEPTANCE_CRITERIA = {acceptance_criteria_json}",
        "",
        "fornecedores_db = []",
        "",
        "",
        "app = FastAPI(",
        f'    title="{project_title}",',
        '    description="API gerada automaticamente para cadastro de fornecedores.",',
        '    version="1.0.0"',
        ")",
        "",
        "",
        '@app.get("/")',
        "def root():",
        '    return {"msg": "API de fornecedores gerada com sucesso 🚀", "project_name": PROJECT_NAME}',
        "",
        "",
        '@app.get("/health")',
        "def health():",
        '    return {"status": "ok"}',
        "",
        "",
        '@app.post("/fornecedores", response_model=FornecedorResponse)',
        "def criar_fornecedor(payload: FornecedorCreate):",
        "    fornecedor = payload.model_dump()",
        '    fornecedor["id"] = str(uuid4())',
        '    fornecedor["mensagem"] = "Fornecedor cadastrado com sucesso"',
        "    fornecedores_db.append(fornecedor)",
        "    return fornecedor",
        "",
        "",
        '@app.get("/fornecedores", response_model=List[FornecedorResponse])',
        "def listar_fornecedores():",
        "    return fornecedores_db",
        "",
        "",
        '@app.get("/fornecedores/{fornecedor_id}", response_model=FornecedorResponse)',
        "def obter_fornecedor(fornecedor_id: str):",
        "    for fornecedor in fornecedores_db:",
        '        if fornecedor["id"] == fornecedor_id:',
        "            return fornecedor",
        "    raise HTTPException(status_code=404, detail='Fornecedor não encontrado')",
        "",
        "",
        '@app.get("/user-story", response_model=UserStoryResponse)',
        "def get_user_story():",
        '    return {"user_story": USER_STORY}',
        "",
        "",
        '@app.get("/acceptance-criteria", response_model=AcceptanceCriteriaResponse)',
        "def get_acceptance_criteria():",
        '    return {"acceptance_criteria": ACCEPTANCE_CRITERIA}',
        "",
        "",
        '@app.get("/metadata", response_model=MetadataResponse)',
        "def get_metadata():",
        "    return {",
        '        "project_name": PROJECT_NAME,',
        '        "bug": BUG,',
        '        "user_story": USER_STORY,',
        '        "acceptance_criteria": ACCEPTANCE_CRITERIA,',
        "    }",
        "",
    ]

    return "\n".join(lines)


def generate_fastapi_code(
    project_title: str,
    bug: str,
    user_story: str,
    acceptance_criteria: List[str],
) -> str:
    domain = detect_domain(bug)

    if domain == "fornecedor":
        return generate_fornecedor_fastapi_code(
            project_title=project_title,
            bug=bug,
            user_story=user_story,
            acceptance_criteria=acceptance_criteria,
        )

    return generate_generic_fastapi_code(
        project_title=project_title,
        bug=bug,
        user_story=user_story,
        acceptance_criteria=acceptance_criteria,
    )


def generate_readme(
    project_name: str,
    bug: str,
    user_story: str,
    acceptance_criteria: List[str],
) -> str:
    domain = detect_domain(bug)
    criteria_md = format_acceptance_criteria(acceptance_criteria)

    endpoints = [
        "- `GET /`",
        "- `GET /health`",
        "- `GET /user-story`",
        "- `GET /acceptance-criteria`",
        "- `GET /metadata`",
    ]

    if domain == "fornecedor":
        endpoints.insert(2, "- `POST /fornecedores`")
        endpoints.insert(3, "- `GET /fornecedores`")
        endpoints.insert(4, "- `GET /fornecedores/{fornecedor_id}`")

    lines = [
        f"# {project_name}",
        "",
        "Projeto gerado automaticamente a partir de um bug informado na API.",
        "",
        "## Bug original",
        "",
        "```text",
        bug,
        "```",
        "",
        "## User Story",
        "",
        "```text",
        user_story,
        "```",
        "",
        "## Critérios de Aceitação",
        "",
        criteria_md,
        "",
        "## Endpoints disponíveis",
        "",
        *endpoints,
        "",
        "## Como executar",
        "",
        "```bash",
        "pip install -r requirements.txt",
        "uvicorn main:app --reload --port 8004",
        "```",
        "",
        "Acesse:",
        "",
        "```text",
        "http://127.0.0.1:8004/docs",
        "```",
        "",
    ]

    return "\n".join(lines)


def create_project_files(
    bug: str,
    user_story: str,
    acceptance_criteria: List[str],
) -> Dict[str, Any]:
    """
    Fluxo antigo: gera projeto com código baseado em templates.
    """
    ensure_generated_dir()

    project_name = build_project_name(bug)
    project_path = os.path.join(GENERATED_PROJECTS_DIR, project_name)

    os.makedirs(project_path, exist_ok=True)

    domain = detect_domain(bug)

    readme_content = generate_readme(
        project_name=project_name,
        bug=bug,
        user_story=user_story,
        acceptance_criteria=acceptance_criteria,
    )

    user_story_content = "\n".join([
        "# User Story",
        "",
        user_story,
        "",
    ])

    acceptance_criteria_content = "\n".join([
        "# Critérios de Aceitação",
        "",
        format_acceptance_criteria(acceptance_criteria),
        "",
    ])

    requirements_content = "\n".join([
        "fastapi",
        "uvicorn",
        "pydantic",
        "",
    ])

    main_py_content = generate_fastapi_code(
        project_title=project_name,
        bug=bug,
        user_story=user_story,
        acceptance_criteria=acceptance_criteria,
    )

    endpoints = [
        "GET /",
        "GET /health",
        "GET /user-story",
        "GET /acceptance-criteria",
        "GET /metadata",
    ]

    if domain == "fornecedor":
        endpoints.insert(2, "POST /fornecedores")
        endpoints.insert(3, "GET /fornecedores")
        endpoints.insert(4, "GET /fornecedores/{fornecedor_id}")

    metadata = {
        "project_name": project_name,
        "created_at": datetime.now().isoformat(),
        "generation_mode": "template",
        "domain": domain,
        "bug": bug,
        "user_story": user_story,
        "acceptance_criteria": acceptance_criteria,
        "files": [
            "README.md",
            "user_story.md",
            "acceptance_criteria.md",
            "main.py",
            "requirements.txt",
            "metadata.json",
        ],
        "endpoints": endpoints,
    }

    write_file(os.path.join(project_path, "README.md"), readme_content)
    write_file(os.path.join(project_path, "user_story.md"), user_story_content)
    write_file(
        os.path.join(project_path, "acceptance_criteria.md"),
        acceptance_criteria_content,
    )
    write_file(os.path.join(project_path, "main.py"), main_py_content)
    write_file(os.path.join(project_path, "requirements.txt"), requirements_content)
    write_file(
        os.path.join(project_path, "metadata.json"),
        json.dumps(metadata, ensure_ascii=False, indent=2),
    )

    return {
        "project_name": project_name,
        "project_path": project_path,
        "files": metadata["files"],
        "metadata": metadata,
    }


def build_project_response(
    bug: str,
    user_story: str,
    acceptance_criteria: List[str],
) -> Dict[str, Any]:
    """
    Usado pelo endpoint /projects/generate-full.
    """
    project = create_project_files(
        bug=bug,
        user_story=user_story,
        acceptance_criteria=acceptance_criteria,
    )

    return {
        "project_name": project["project_name"],
        "project_path": project["project_path"],
        "domain": project["metadata"]["domain"],
        "user_story": user_story,
        "acceptance_criteria": acceptance_criteria,
        "files": project["files"],
        "endpoints": project["metadata"]["endpoints"],
    }


# ============================================================
# NOVO FLUXO — SOLUÇÃO TÉCNICA GERADA PELA OPENAI
# Usado pelo futuro endpoint /projects/generate-solution
# ============================================================

def build_solution_readme(
    project_name: str,
    bug: str,
    user_story: str,
    acceptance_criteria: List[str],
    technical_analysis: str,
    solution_plan: List[str],
    original_readme: Optional[str] = None,
) -> str:
    """
    Gera README consolidado para o projeto solução.
    Se a OpenAI retornar README.md, ele será preservado ao final.
    """
    criteria_md = format_acceptance_criteria(acceptance_criteria)

    plan_lines = []
    for item in solution_plan:
        item = str(item).strip()
        if item:
            plan_lines.append(f"- {item}")

    plan_md = "\n".join(plan_lines) if plan_lines else "Plano de solução não informado."

    lines = [
        f"# {project_name}",
        "",
        "Projeto gerado automaticamente pela OpenAI para propor uma solução técnica ao bug informado.",
        "",
        "## Bug original",
        "",
        "```text",
        bug,
        "```",
        "",
        "## User Story",
        "",
        "```text",
        user_story,
        "```",
        "",
        "## Critérios de Aceitação",
        "",
        criteria_md,
        "",
        "## Análise Técnica",
        "",
        technical_analysis or "Análise técnica não informada.",
        "",
        "## Plano de Solução",
        "",
        plan_md,
        "",
        "## Como executar",
        "",
        "```bash",
        "pip install -r requirements.txt",
        "uvicorn main:app --reload --port 8004",
        "```",
        "",
        "Acesse:",
        "",
        "```text",
        "http://127.0.0.1:8004/docs",
        "```",
        "",
    ]

    if original_readme:
        lines.extend([
            "---",
            "",
            "## README gerado originalmente pela OpenAI",
            "",
            original_readme,
            "",
        ])

    return "\n".join(lines)


def create_solution_project_files(
    bug: str,
    user_story: str,
    acceptance_criteria: List[str],
    technical_analysis: str,
    solution_plan: List[str],
    files: Dict[str, str],
) -> Dict[str, Any]:
    """
    Novo fluxo: grava arquivos gerados pela OpenAI.
    """
    ensure_generated_dir()

    project_name = build_project_name(bug, suffix="solution")
    project_path = os.path.join(GENERATED_PROJECTS_DIR, project_name)

    os.makedirs(project_path, exist_ok=True)

    if not isinstance(files, dict):
        files = {}

    normalized_files: Dict[str, str] = {}

    for filename, content in files.items():
        filename = safe_filename(str(filename))
        normalized_files[filename] = str(content)

    if "requirements.txt" not in normalized_files:
        normalized_files["requirements.txt"] = "fastapi\nuvicorn\npydantic\n"

    if "main.py" not in normalized_files:
        normalized_files["main.py"] = generate_generic_fastapi_code(
            project_title=project_name,
            bug=bug,
            user_story=user_story,
            acceptance_criteria=acceptance_criteria,
        )

    original_readme = normalized_files.get("README.md", "")

    normalized_files["README.md"] = build_solution_readme(
        project_name=project_name,
        bug=bug,
        user_story=user_story,
        acceptance_criteria=acceptance_criteria,
        technical_analysis=technical_analysis,
        solution_plan=solution_plan,
        original_readme=original_readme,
    )

    normalized_files["user_story.md"] = "\n".join([
        "# User Story",
        "",
        user_story,
        "",
    ])

    normalized_files["acceptance_criteria.md"] = "\n".join([
        "# Critérios de Aceitação",
        "",
        format_acceptance_criteria(acceptance_criteria),
        "",
    ])

    normalized_files["technical_analysis.md"] = "\n".join([
        "# Análise Técnica",
        "",
        technical_analysis or "Análise técnica não informada.",
        "",
    ])

    solution_plan_md = []
    for item in solution_plan:
        item = str(item).strip()
        if item:
            solution_plan_md.append(f"- {item}")

    normalized_files["solution_plan.md"] = "\n".join([
        "# Plano de Solução",
        "",
        "\n".join(solution_plan_md) if solution_plan_md else "Plano de solução não informado.",
        "",
    ])

    metadata = {
        "project_name": project_name,
        "created_at": datetime.now().isoformat(),
        "generation_mode": "openai_solution",
        "bug": bug,
        "user_story": user_story,
        "acceptance_criteria": acceptance_criteria,
        "technical_analysis": technical_analysis,
        "solution_plan": solution_plan,
        "files": sorted(list(normalized_files.keys()) + ["metadata.json"]),
    }

    normalized_files["metadata.json"] = json.dumps(metadata, ensure_ascii=False, indent=2)

    for filename, content in normalized_files.items():
        write_file(os.path.join(project_path, filename), content)

    return {
        "project_name": project_name,
        "project_path": project_path,
        "files": sorted(normalized_files.keys()),
        "metadata": metadata,
    }


def build_solution_project_response(
    bug: str,
    user_story: str,
    acceptance_criteria: List[str],
    technical_analysis: str,
    solution_plan: List[str],
    files: Dict[str, str],
) -> Dict[str, Any]:
    """
    Usado pelo endpoint /projects/generate-solution.
    """
    project = create_solution_project_files(
        bug=bug,
        user_story=user_story,
        acceptance_criteria=acceptance_criteria,
        technical_analysis=technical_analysis,
        solution_plan=solution_plan,
        files=files,
    )

    return {
        "project_name": project["project_name"],
        "project_path": project["project_path"],
        "generation_mode": project["metadata"]["generation_mode"],
        "user_story": user_story,
        "acceptance_criteria": acceptance_criteria,
        "technical_analysis": technical_analysis,
        "solution_plan": solution_plan,
        "files": project["files"],
    }