from dotenv import load_dotenv
load_dotenv()

import os
import json
import re
from typing import Any, Dict, List

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    temperature=0.2
)


prompt = ChatPromptTemplate.from_template("""
Você é um especialista sênior em análise de requisitos e user stories.

Transforme o BUG abaixo em uma User Story e critérios de aceitação.

FORMATO OBRIGATÓRIO DA USER STORY:
Como um <tipo de usuário>, eu quero <ação relacionada diretamente ao bug>, para que <benefício esperado>.

REGRAS OBRIGATÓRIAS:
- A User Story deve conter explicitamente as palavras mais importantes do bug.
- Se o bug mencionar "erro 500", a User Story deve conter "erro 500".
- Se o bug mencionar "login" ou "logar", a User Story deve conter "login" ou "logar".
- Se o bug mencionar "perfil", "perfis" ou "múltiplos perfis", a User Story deve preservar essa expressão.
- Se o bug mencionar "formulário", a User Story deve conter "formulário".
- Se o bug mencionar "salva" ou "salvar", a User Story deve conter "salvar".
- Se o bug mencionar "dashboard", a User Story deve conter "dashboard".
- Se o bug mencionar "tela em branco", a User Story deve conter literalmente "tela em branco".
- Não invente funcionalidades que não estejam no bug.
- Não use markdown.
- Não escreva títulos como "User Story:" ou "Critérios de Aceitação:".
- Responda somente com a User Story e os critérios.

FORMATO EXATO DA RESPOSTA:

Como um <tipo de usuário>, eu quero <ação>, para que <benefício>.

Dado que <contexto>
Quando <ação>
Então <resultado esperado>
E <validação adicional>

BUG:
{bug}
""")


solution_prompt = ChatPromptTemplate.from_template("""
Você é um arquiteto de software sênior e desenvolvedor Python/FastAPI.

Sua tarefa é receber um BUG e gerar uma solução técnica implementável.

Você deve retornar EXCLUSIVAMENTE um JSON válido, sem markdown, sem explicações fora do JSON, sem ```json.

O JSON deve seguir exatamente esta estrutura:

{{
  "user_story": "Como um usuário..., eu quero..., para que...",
  "acceptance_criteria": [
    "Dado que ...",
    "Quando ...",
    "Então ...",
    "E ..."
  ],
  "technical_analysis": "Explique tecnicamente a causa provável do bug e o que precisa ser corrigido.",
  "solution_plan": [
    "Passo 1 da solução",
    "Passo 2 da solução",
    "Passo 3 da solução"
  ],
  "files": {{
    "main.py": "conteúdo completo do arquivo main.py",
    "README.md": "conteúdo completo do README.md",
    "requirements.txt": "conteúdo completo do requirements.txt"
  }}
}}

REGRAS OBRIGATÓRIAS:
- Gere código Python completo e funcional.
- Use FastAPI.
- Use Pydantic.
- O arquivo main.py deve poder ser executado com: uvicorn main:app --reload --port 8004.
- O código deve conter endpoints coerentes com o bug.
- Se o bug falar de fornecedor, CNPJ, endereço, contatos ou cadastro de fornecedor, gere endpoints de fornecedores.
- Se gerar API de fornecedores, inclua:
  - POST /fornecedores
  - GET /fornecedores
  - GET /fornecedores/{{fornecedor_id}}
  - GET /health
- Para fornecedores, o payload deve ter:
  - razao_social
  - cnpj
  - endereco
  - contatos
- Para fornecedores, valide minimamente se endereço e contatos foram recebidos.
- Não use banco real neste momento. Use lista em memória.
- Não use dependências além de fastapi, uvicorn e pydantic.
- O README.md deve explicar como executar e testar a API.
- O requirements.txt deve conter exatamente:
fastapi
uvicorn
pydantic
- Não coloque crases markdown envolvendo o JSON final.
- Não retorne texto fora do JSON.
- Use Pydantic v2.
- Para validação de strings, use constr(pattern=...) e nunca constr(regex=...).

BUG:
{bug}
""")


def clean_user_story(text: str) -> str:
    if not text:
        return ""

    text = text.replace("User Story:", "")
    text = text.replace("História de Usuário:", "")
    text = text.replace("Historia de Usuario:", "")
    text = text.replace("Critérios de Aceitação:", "")
    text = text.replace("Criterios de Aceitacao:", "")

    return text.strip()


def clean_acceptance_line(text: str) -> str:
    if not text:
        return ""

    text = text.strip()
    text = text.lstrip("-").strip()
    text = text.lstrip("*").strip()

    return text


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Extrai JSON da resposta do modelo.

    Aceita:
    - JSON puro
    - JSON cercado por ```json
    - JSON com algum texto antes/depois
    - tenta corrigir barras invertidas inválidas, como C:\pasta
    """
    if not text:
        raise ValueError("Resposta vazia da OpenAI.")

    cleaned = text.strip()

    cleaned = cleaned.replace("```json", "")
    cleaned = cleaned.replace("```", "")
    cleaned = cleaned.strip()

    def try_load_json(value: str) -> Dict[str, Any]:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # Corrige barras invertidas inválidas em JSON:
            # Exemplo: C:\Prompts vira C:\\Prompts
            repaired = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", value)
            return json.loads(repaired)

    try:
        return try_load_json(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)

    if not match:
        raise ValueError("Não foi possível encontrar um JSON válido na resposta da OpenAI.")

    json_text = match.group(0)

    try:
        return try_load_json(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON retornado pela OpenAI é inválido: {str(e)}")


def ensure_list(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        return lines if lines else [value.strip()]

    return [str(value).strip()]


def generate_fallback_main_py() -> str:
    lines = [
        "from fastapi import FastAPI",
        "",
        "app = FastAPI(",
        '    title="Projeto Gerado",',
        '    description="API gerada automaticamente para solução de bug.",',
        '    version="1.0.0"',
        ")",
        "",
        "",
        '@app.get("/")',
        "def root():",
        '    return {"msg": "Projeto gerado com sucesso 🚀"}',
        "",
        "",
        '@app.get("/health")',
        "def health():",
        '    return {"status": "ok"}',
        "",
    ]

    return "\n".join(lines)


def generate_fallback_readme(bug: str) -> str:
    lines = [
        "# Projeto Gerado",
        "",
        "Projeto gerado automaticamente a partir do bug:",
        "",
        "```text",
        bug,
        "```",
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


def ensure_files(files: Any, bug: str) -> Dict[str, str]:
    if not isinstance(files, dict):
        files = {}

    main_py = files.get("main.py")
    readme_md = files.get("README.md")
    requirements_txt = files.get("requirements.txt")

    if not main_py:
        main_py = generate_fallback_main_py()

    if not readme_md:
        readme_md = generate_fallback_readme(bug)

    if not requirements_txt:
        requirements_txt = "fastapi\nuvicorn\npydantic\n"

    files["main.py"] = str(main_py)
    files["README.md"] = str(readme_md)
    files["requirements.txt"] = str(requirements_txt)

    return {
        str(filename): str(content)
        for filename, content in files.items()
    }


def generate_all(bug: str) -> Dict[str, Any]:
    """
    Gera User Story e Critérios de Aceitação a partir de um bug.
    Usada pelos endpoints:
    - POST /projects/generate
    - POST /projects/generate-full
    """
    chain = prompt | llm

    response = chain.invoke({"bug": bug})
    text = response.content.strip()

    parts = text.split("Dado")

    user_story = clean_user_story(parts[0])

    acceptance_criteria = []

    if len(parts) > 1:
        criteria_text = "Dado" + parts[1]

        acceptance_criteria = [
            clean_acceptance_line(line)
            for line in criteria_text.splitlines()
            if clean_acceptance_line(line)
        ]

    return {
        "user_story": user_story,
        "acceptance_criteria": acceptance_criteria,
    }


def generate_solution_project(bug: str) -> Dict[str, Any]:
    """
    Gera solução técnica completa para o bug, incluindo código.
    """
    chain = solution_prompt | llm

    response = chain.invoke({"bug": bug})
    raw_text = response.content.strip()

    data = extract_json_from_text(raw_text)

    user_story = str(data.get("user_story", "")).strip()
    acceptance_criteria = ensure_list(data.get("acceptance_criteria", []))
    technical_analysis = str(data.get("technical_analysis", "")).strip()
    solution_plan = ensure_list(data.get("solution_plan", []))
    files = ensure_files(data.get("files", {}), bug)

    if not user_story:
        fallback = generate_all(bug)
        user_story = fallback.get("user_story", "")
        acceptance_criteria = fallback.get("acceptance_criteria", acceptance_criteria)

    if not technical_analysis:
        technical_analysis = (
            "A análise técnica não foi retornada pelo modelo. "
            "Verifique o bug informado e refine o prompt de geração."
        )

    if not solution_plan:
        solution_plan = [
            "Analisar o comportamento descrito no bug.",
            "Identificar os dados que não estão sendo persistidos corretamente.",
            "Implementar endpoints e validações para tratar o fluxo esperado.",
            "Testar o comportamento com payloads válidos e inválidos.",
        ]

    return {
        "user_story": user_story,
        "acceptance_criteria": acceptance_criteria,
        "technical_analysis": technical_analysis,
        "solution_plan": solution_plan,
        "files": files,
    }