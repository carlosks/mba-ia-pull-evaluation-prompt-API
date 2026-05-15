from dotenv import load_dotenv
load_dotenv()

import os
import json
import re
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


_llm: Optional[ChatOpenAI] = None


def get_llm() -> ChatOpenAI:
    """
    Cria o LLM somente quando necessário.
    Isso evita erro de import caso a OPENAI_API_KEY ainda não esteja carregada.
    """
    global _llm

    if _llm is None:
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY não encontrada. "
                "Crie o arquivo .env na raiz do projeto e informe OPENAI_API_KEY."
            )

        _llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=0.2,
            api_key=api_key,
        )

    return _llm


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
- Use Pydantic v2.
- Use Pydantic field_validator quando precisar validar campos.
- Nunca use constr(regex=...). Em Pydantic v2 use sempre constr(pattern=...).
- Para expressões regulares em Python, use string raw, por exemplo: constr(pattern=r"^\\d{{14}}$").
- O código Python gerado deve ser importável sem erro com: python -c "from main import app; print('OK')".
- Garanta indentação Python válida em todas as classes, funções e decorators.
- O arquivo main.py deve poder ser executado com: uvicorn main:app --reload --port 8004.
- O código deve conter endpoints coerentes com o bug.
- Se o bug falar de fornecedor, CNPJ, endereço, contatos ou cadastro de fornecedor, gere endpoints de fornecedores.
- Se gerar API de fornecedores, inclua:
  - POST /fornecedores
  - GET /fornecedores
  - GET /fornecedores/cnpj/{{cnpj}}
  - GET /relatorioRespostasFornecedor
  - GET /health
- Para fornecedores, o payload deve ter:
  - razao_social
  - cnpj
  - endereco
  - contatos
- Para fornecedores, valide minimamente se endereço e contatos foram recebidos.
- Para fornecedores, o CNPJ deve ser validado.
- Para fornecedores, não permita cadastro duplicado do mesmo CNPJ.
- Não use banco real neste momento. Use dicionário ou lista em memória.
- Não use dependências além de fastapi, uvicorn e pydantic.
- O README.md deve explicar como executar e testar a API.
- O requirements.txt deve conter exatamente:
fastapi
uvicorn
pydantic
- Não coloque crases markdown envolvendo o JSON final.
- Não retorne texto fora do JSON.

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
    - tenta corrigir barras invertidas inválidas, como C:\\pasta
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


def sanitize_generated_python_code(content: str) -> str:
    """
    Corrige automaticamente padrões comuns gerados pela OpenAI
    que quebram em Pydantic v2 ou Python moderno.
    """
    if not content:
        return ""

    content = re.sub(
        r"constr\(\s*regex\s*=\s*(['\"])(.*?)\1",
        lambda m: f"constr(pattern=r{m.group(1)}{m.group(2)}{m.group(1)}",
        content,
    )

    content = re.sub(
        r"constr\(\s*pattern\s*=\s*(['\"])([^'\"]*\\d[^'\"]*)\1",
        lambda m: f"constr(pattern=r{m.group(1)}{m.group(2)}{m.group(1)}",
        content,
    )

    lines = [line.rstrip() for line in content.splitlines()]

    return "\n".join(lines).strip() + "\n"


def build_supplier_api_main_py() -> str:
    """
    Gera um main.py padronizado para bugs envolvendo cadastro de fornecedor,
    CNPJ, endereço e contatos.

    Esta versão usa SQLite para persistir os fornecedores em banco local.
    Compatível com Pydantic v2.
    """

    return r'''import sqlite3
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator


DB_PATH = Path("fornecedores.db")


def get_connection():
    """
    Cria uma conexão SQLite.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Cria a tabela de fornecedores, caso ainda não exista.
    """

    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fornecedores (
                cnpj TEXT PRIMARY KEY,
                razao_social TEXT NOT NULL,
                endereco TEXT NOT NULL,
                contatos TEXT NOT NULL
            )
            """
        )
        conn.commit()


def somente_digitos(valor: str) -> str:
    return "".join(ch for ch in valor if ch.isdigit())


def validar_cnpj(cnpj: str) -> bool:
    """
    Valida CNPJ usando os dígitos verificadores oficiais.
    Aceita CNPJ com ou sem máscara.
    """

    cnpj = somente_digitos(cnpj)

    if len(cnpj) != 14:
        return False

    if cnpj == cnpj[0] * 14:
        return False

    pesos_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    soma_1 = sum(int(cnpj[i]) * pesos_1[i] for i in range(12))
    resto_1 = soma_1 % 11
    digito_1 = 0 if resto_1 < 2 else 11 - resto_1

    soma_2 = sum(int(cnpj[i]) * pesos_2[i] for i in range(13))
    resto_2 = soma_2 % 11
    digito_2 = 0 if resto_2 < 2 else 11 - resto_2

    return int(cnpj[12]) == digito_1 and int(cnpj[13]) == digito_2


def contatos_to_text(contatos: List[str]) -> str:
    """
    Converte lista de contatos para texto persistível.
    """
    return "\n".join(contatos)


def text_to_contatos(contatos_texto: str) -> List[str]:
    """
    Converte texto do banco para lista de contatos.
    """
    if not contatos_texto:
        return []

    return [
        contato.strip()
        for contato in contatos_texto.splitlines()
        if contato.strip()
    ]


class Fornecedor(BaseModel):
    razao_social: str
    cnpj: str
    endereco: str
    contatos: List[str]

    @field_validator("cnpj")
    @classmethod
    def cnpj_deve_ser_valido(cls, value: str) -> str:
        cnpj_limpo = somente_digitos(value)

        if not validar_cnpj(cnpj_limpo):
            raise ValueError("CNPJ inválido.")

        return cnpj_limpo

    @field_validator("razao_social")
    @classmethod
    def razao_social_obrigatoria(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Razão social é obrigatória.")
        return value.strip()

    @field_validator("endereco")
    @classmethod
    def endereco_obrigatorio(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Endereço é obrigatório.")
        return value.strip()

    @field_validator("contatos")
    @classmethod
    def contatos_obrigatorios(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("Informe pelo menos um contato.")

        contatos_validos = [
            contato.strip()
            for contato in value
            if contato and contato.strip()
        ]

        if not contatos_validos:
            raise ValueError("Informe pelo menos um contato válido.")

        return contatos_validos


class FornecedorResponse(BaseModel):
    razao_social: str
    cnpj: str
    endereco: str
    contatos: List[str]


def fornecedor_from_row(row: sqlite3.Row) -> FornecedorResponse:
    """
    Converte uma linha SQLite em resposta da API.
    """

    return FornecedorResponse(
        razao_social=row["razao_social"],
        cnpj=row["cnpj"],
        endereco=row["endereco"],
        contatos=text_to_contatos(row["contatos"]),
    )


app = FastAPI(
    title="API de Fornecedores",
    description="API gerada automaticamente para cadastro e consulta de fornecedores com persistência SQLite.",
    version="1.0.0",
)


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/")
def root():
    return {
        "msg": "API de fornecedores com SQLite rodando 🚀"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "database": str(DB_PATH)
    }


@app.post("/fornecedores")
def criar_fornecedor(fornecedor: Fornecedor):
    """
    Cadastra um novo fornecedor.
    O CNPJ deve ser válido e não pode estar duplicado.
    Os dados são persistidos em SQLite.
    """

    init_db()

    with get_connection() as conn:
        existente = conn.execute(
            "SELECT cnpj FROM fornecedores WHERE cnpj = ?",
            (fornecedor.cnpj,)
        ).fetchone()

        if existente:
            raise HTTPException(
                status_code=409,
                detail="Fornecedor já cadastrado para este CNPJ.",
            )

        conn.execute(
            """
            INSERT INTO fornecedores (
                cnpj,
                razao_social,
                endereco,
                contatos
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                fornecedor.cnpj,
                fornecedor.razao_social,
                fornecedor.endereco,
                contatos_to_text(fornecedor.contatos),
            )
        )

        conn.commit()

    return {
        "message": "Fornecedor criado com sucesso",
        "fornecedor": fornecedor,
    }


@app.get("/fornecedores", response_model=List[FornecedorResponse])
def listar_fornecedores():
    """
    Lista todos os fornecedores cadastrados no banco SQLite.
    """

    init_db()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                cnpj,
                razao_social,
                endereco,
                contatos
            FROM fornecedores
            ORDER BY razao_social
            """
        ).fetchall()

    return [
        fornecedor_from_row(row)
        for row in rows
    ]


@app.get("/fornecedores/cnpj/{cnpj}", response_model=FornecedorResponse)
def obter_fornecedor_por_cnpj(cnpj: str):
    """
    Consulta um fornecedor pelo CNPJ.
    """

    init_db()

    cnpj_limpo = somente_digitos(cnpj)

    if not validar_cnpj(cnpj_limpo):
        raise HTTPException(
            status_code=400,
            detail="CNPJ inválido.",
        )

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                cnpj,
                razao_social,
                endereco,
                contatos
            FROM fornecedores
            WHERE cnpj = ?
            """,
            (cnpj_limpo,)
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Fornecedor não encontrado.",
        )

    return fornecedor_from_row(row)


@app.put("/fornecedores/cnpj/{cnpj}", response_model=FornecedorResponse)
def atualizar_fornecedor_por_cnpj(cnpj: str, fornecedor: Fornecedor):
    """
    Atualiza um fornecedor existente pelo CNPJ.
    """

    init_db()

    cnpj_limpo = somente_digitos(cnpj)

    if not validar_cnpj(cnpj_limpo):
        raise HTTPException(
            status_code=400,
            detail="CNPJ inválido.",
        )

    if cnpj_limpo != fornecedor.cnpj:
        raise HTTPException(
            status_code=400,
            detail="O CNPJ da URL deve ser igual ao CNPJ do corpo da requisição.",
        )

    with get_connection() as conn:
        existente = conn.execute(
            "SELECT cnpj FROM fornecedores WHERE cnpj = ?",
            (cnpj_limpo,)
        ).fetchone()

        if not existente:
            raise HTTPException(
                status_code=404,
                detail="Fornecedor não encontrado.",
            )

        conn.execute(
            """
            UPDATE fornecedores
            SET
                razao_social = ?,
                endereco = ?,
                contatos = ?
            WHERE cnpj = ?
            """,
            (
                fornecedor.razao_social,
                fornecedor.endereco,
                contatos_to_text(fornecedor.contatos),
                cnpj_limpo,
            )
        )

        conn.commit()

        row = conn.execute(
            """
            SELECT
                cnpj,
                razao_social,
                endereco,
                contatos
            FROM fornecedores
            WHERE cnpj = ?
            """,
            (cnpj_limpo,)
        ).fetchone()

    return fornecedor_from_row(row)


@app.delete("/fornecedores/cnpj/{cnpj}")
def excluir_fornecedor_por_cnpj(cnpj: str):
    """
    Exclui um fornecedor pelo CNPJ.
    """

    init_db()

    cnpj_limpo = somente_digitos(cnpj)

    if not validar_cnpj(cnpj_limpo):
        raise HTTPException(
            status_code=400,
            detail="CNPJ inválido.",
        )

    with get_connection() as conn:
        existente = conn.execute(
            "SELECT cnpj FROM fornecedores WHERE cnpj = ?",
            (cnpj_limpo,)
        ).fetchone()

        if not existente:
            raise HTTPException(
                status_code=404,
                detail="Fornecedor não encontrado.",
            )

        conn.execute(
            "DELETE FROM fornecedores WHERE cnpj = ?",
            (cnpj_limpo,)
        )

        conn.commit()

    return {
        "message": "Fornecedor excluído com sucesso",
        "cnpj": cnpj_limpo,
    }


@app.get("/relatorioRespostasFornecedor")
def relatorio_respostas_fornecedor(
    pCnpj: str,
    pData: str,
    pRazaoSocial: str,
):
    """
    Simula a consulta do relatório de respostas do fornecedor.
    """

    init_db()

    cnpj_limpo = somente_digitos(pCnpj)

    if not validar_cnpj(cnpj_limpo):
        raise HTTPException(
            status_code=400,
            detail="CNPJ inválido.",
        )

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                cnpj,
                razao_social,
                endereco,
                contatos
            FROM fornecedores
            WHERE cnpj = ?
            """,
            (cnpj_limpo,)
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Fornecedor não encontrado.",
        )

    fornecedor = fornecedor_from_row(row)

    if fornecedor.razao_social.strip().upper() != pRazaoSocial.strip().upper():
        raise HTTPException(
            status_code=404,
            detail="Fornecedor não encontrado para a razão social informada.",
        )

    return {
        "cnpj": fornecedor.cnpj,
        "data": pData,
        "razao_social": fornecedor.razao_social,
        "endereco": fornecedor.endereco,
        "contatos": fornecedor.contatos,
        "status": "Relatório encontrado",
    }
'''


def is_supplier_bug(bug: str) -> bool:
    if not bug:
        return False

    text = bug.lower()

    supplier_terms = [
        "fornecedor",
        "fornecedores",
        "cnpj",
        "endereço",
        "endereco",
        "contato",
        "contatos",
        "cadastro de fornecedor",
        "cadastrar fornecedor",
    ]

    return any(term in text for term in supplier_terms)


def ensure_files(files: Any, bug: str) -> Dict[str, str]:
    if not isinstance(files, dict):
        files = {}

    main_py = files.get("main.py")
    readme_md = files.get("README.md")
    requirements_txt = files.get("requirements.txt")

    if is_supplier_bug(bug):
        main_py = build_supplier_api_main_py()

    if not main_py:
        main_py = generate_fallback_main_py()

    if not readme_md:
        readme_md = generate_fallback_readme(bug)

    if not requirements_txt:
        requirements_txt = "fastapi\nuvicorn\npydantic\n"

    files["main.py"] = sanitize_generated_python_code(str(main_py))
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
    chain = prompt | get_llm()

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
    chain = solution_prompt | get_llm()

    response = chain.invoke({"bug": bug})
    raw_text = response.content.strip()

    data = extract_json_from_text(raw_text)

    user_story = str(data.get("user_story", "")).strip()
    acceptance_criteria = ensure_list(data.get("acceptance_criteria", []))
    technical_analysis = str(data.get("technical_analysis", "")).strip()
    solution_plan = ensure_list(data.get("solution_plan", []))
    files = ensure_files(data.get("files", {}), bug)

    if is_supplier_bug(bug):
        if not user_story:
            user_story = (
                "Como um usuário, eu quero cadastrar fornecedores com CNPJ válido, "
                "endereço e contatos, para que todos os dados sejam persistidos corretamente."
            )

        if not acceptance_criteria:
            acceptance_criteria = [
                "Dado que eu tenha um CNPJ válido, uma razão social, um endereço e contatos para o fornecedor",
                "Quando eu enviar uma requisição POST para /fornecedores com esses dados",
                "Então o fornecedor deve ser cadastrado com todos os dados corretamente",
                "E eu devo conseguir recuperar o fornecedor cadastrado através do endpoint GET /fornecedores/cnpj/{cnpj}",
                "E o sistema deve impedir cadastro duplicado do mesmo CNPJ",
            ]

        if not technical_analysis:
            technical_analysis = (
                "O bug indica persistência parcial de fornecedor. "
                "A solução deve validar o CNPJ, impedir duplicidade e garantir que razão social, "
                "endereço e contatos sejam armazenados e recuperados corretamente."
            )

        if not solution_plan:
            solution_plan = [
                "Criar modelo de fornecedor com razão social, CNPJ, endereço e contatos.",
                "Implementar validação real de CNPJ.",
                "Implementar POST /fornecedores com bloqueio de CNPJ duplicado.",
                "Implementar GET /fornecedores para listagem.",
                "Implementar GET /fornecedores/cnpj/{cnpj} para consulta por CNPJ.",
                "Testar cadastro, consulta e duplicidade.",
            ]

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