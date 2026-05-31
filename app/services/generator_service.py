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
  "test_cases": [
    "Deve validar o comportamento principal descrito no bug.",
    "Deve impedir que o erro volte a ocorrer.",
    "Deve validar entradas inválidas ou incompletas.",
    "Deve confirmar que os dados esperados foram persistidos ou retornados corretamente."
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
- O arquivo main.py deve poder ser executado com: python -m uvicorn main:app --reload --port 8004.
- O código deve conter endpoints coerentes com o bug.
- Se o bug falar de fornecedor, CNPJ, endereço, contatos ou cadastro de fornecedor, gere endpoints de fornecedores.
- Para bugs envolvendo fornecedor, CNPJ, endereço, contatos ou cadastro de fornecedor, use SQLite com arquivo fornecedores.db.
- Para fornecedores, os dados devem continuar disponíveis após reiniciar a API.
- Não use banco externo neste momento. Use SQLite local.
- Se gerar API de fornecedores, inclua:
  - POST /fornecedores
  - GET /fornecedores
  - GET /fornecedores/cnpj/{{cnpj}}
  - PUT /fornecedores/cnpj/{{cnpj}}
  - DELETE /fornecedores/cnpj/{{cnpj}}
  - GET /relatorioRespostasFornecedor
  - GET /health
- Para fornecedores, o payload deve ter:
  - razao_social
  - cnpj
  - endereco
  - contatos
- Para fornecedores, valide se endereço e contatos foram recebidos.
- Para fornecedores, o CNPJ deve ser validado.
- Para fornecedores, não permita cadastro duplicado do mesmo CNPJ.
- O README.md deve explicar como executar e testar a API.
- Gere sempre o campo test_cases com pelo menos 4 casos de teste funcionais.
- Cada caso de teste deve ser escrito em linguagem clara, começando com "Deve".
- Para bugs de fornecedores, os casos de teste devem cobrir cadastro, consulta, duplicidade, CNPJ inválido e persistência.
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
        "python -m uvicorn main:app --reload --port 8004",
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
        "sqlite",
        "banco de dados",
        "persistir",
        "persistência",
        "persistencia",
    ]

    return any(term in text for term in supplier_terms)


def generate_fallback_test_cases(bug: str) -> List[str]:
    if is_supplier_bug(bug):
        return [
            "Deve cadastrar fornecedor com CNPJ válido, razão social, endereço e contatos.",
            "Deve retornar o fornecedor completo ao consultar pelo CNPJ cadastrado.",
            "Deve impedir cadastro duplicado para o mesmo CNPJ.",
            "Deve rejeitar CNPJ inválido.",
            "Deve manter endereço e contatos persistidos após reiniciar a API.",
            "Deve permitir atualizar endereço e contatos do fornecedor pelo CNPJ.",
            "Deve permitir excluir fornecedor pelo CNPJ e retornar 404 em consulta posterior.",
        ]

    return [
        "Deve reproduzir o cenário descrito no bug.",
        "Deve validar que o comportamento corrigido retorna o resultado esperado.",
        "Deve validar entradas inválidas ou incompletas.",
        "Deve garantir que o erro original não volte a ocorrer.",
    ]


def build_supplier_api_main_py() -> str:
    """
    Gera main.py com persistência SQLite para fornecedores.
    Compatível com Pydantic v2.
    """

    return r'''import sqlite3
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator


DB_PATH = Path("fornecedores.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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
    return "\n".join(contatos)


def text_to_contatos(contatos_texto: str) -> List[str]:
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
    init_db()

    return {
        "status": "ok",
        "database": str(DB_PATH)
    }


@app.post("/fornecedores", response_model=FornecedorResponse)
def criar_fornecedor(fornecedor: Fornecedor):
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

        row = conn.execute(
            """
            SELECT cnpj, razao_social, endereco, contatos
            FROM fornecedores
            WHERE cnpj = ?
            """,
            (fornecedor.cnpj,)
        ).fetchone()

    return fornecedor_from_row(row)


@app.get("/fornecedores", response_model=List[FornecedorResponse])
def listar_fornecedores():
    init_db()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT cnpj, razao_social, endereco, contatos
            FROM fornecedores
            ORDER BY razao_social
            """
        ).fetchall()

    return [fornecedor_from_row(row) for row in rows]


@app.get("/fornecedores/cnpj/{cnpj}", response_model=FornecedorResponse)
def obter_fornecedor_por_cnpj(cnpj: str):
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
            SELECT cnpj, razao_social, endereco, contatos
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
            SET razao_social = ?, endereco = ?, contatos = ?
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
            SELECT cnpj, razao_social, endereco, contatos
            FROM fornecedores
            WHERE cnpj = ?
            """,
            (cnpj_limpo,)
        ).fetchone()

    return fornecedor_from_row(row)


@app.delete("/fornecedores/cnpj/{cnpj}")
def excluir_fornecedor_por_cnpj(cnpj: str):
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
            SELECT cnpj, razao_social, endereco, contatos
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


def generate_supplier_readme_sqlite(bug: str) -> str:
    """
    Gera README.md completo para projetos de fornecedores com SQLite.
    """

    lines = [
        "# API de Fornecedores com SQLite",
        "",
        "Projeto gerado automaticamente a partir do seguinte BUG:",
        "",
        "```text",
        bug,
        "```",
        "",
        "## Objetivo",
        "",
        "Esta API corrige um problema de cadastro de fornecedores em que os dados eram salvos parcialmente ou perdidos após reiniciar a aplicação.",
        "",
        "A solução implementa:",
        "",
        "- Cadastro de fornecedor com CNPJ válido",
        "- Persistência dos dados em banco SQLite",
        "- Consulta de fornecedor por CNPJ",
        "- Validação real dos dígitos verificadores do CNPJ",
        "- Bloqueio de cadastro duplicado do mesmo CNPJ",
        "- Atualização e exclusão de fornecedor",
        "- Consulta simulada de relatório de respostas do fornecedor",
        "",
        "## Tecnologias utilizadas",
        "",
        "- Python",
        "- FastAPI",
        "- Pydantic v2",
        "- SQLite",
        "- Uvicorn",
        "",
        "## Banco de dados",
        "",
        "A API utiliza SQLite local.",
        "",
        "Ao iniciar a aplicação, será criado automaticamente o arquivo:",
        "",
        "```text",
        "fornecedores.db",
        "```",
        "",
        "## Como executar no macOS ou Linux",
        "",
        "```bash",
        "python3 -m venv venv",
        "source venv/bin/activate",
        "pip install -r requirements.txt",
        "python -m uvicorn main:app --reload --port 8004",
        "```",
        "",
        "## Como executar no Windows PowerShell",
        "",
        "```powershell",
        "python -m venv venv",
        ".\\venv\\Scripts\\activate",
        "pip install -r requirements.txt",
        "python -m uvicorn main:app --reload --port 8004",
        "```",
        "",
        "Acesse:",
        "",
        "```text",
        "http://127.0.0.1:8004/docs",
        "```",
        "",
        "## Endpoints disponíveis",
        "",
        "```text",
        "GET    /",
        "GET    /health",
        "POST   /fornecedores",
        "GET    /fornecedores",
        "GET    /fornecedores/cnpj/{cnpj}",
        "PUT    /fornecedores/cnpj/{cnpj}",
        "DELETE /fornecedores/cnpj/{cnpj}",
        "GET    /relatorioRespostasFornecedor",
        "```",
        "",
        "## Testes principais",
        "",
        "- Deve cadastrar fornecedor com CNPJ válido.",
        "- Deve consultar fornecedor por CNPJ.",
        "- Deve bloquear cadastro duplicado.",
        "- Deve rejeitar CNPJ inválido.",
        "- Deve persistir dados após reiniciar a API.",
        "- Deve atualizar fornecedor por CNPJ.",
        "- Deve excluir fornecedor por CNPJ.",
        "",
        "## Observação",
        "",
        "Este projeto usa SQLite local para prototipação.",
        "",
        "Para produção, recomenda-se evoluir para PostgreSQL, SQLAlchemy ou SQLModel, Alembic, autenticação, testes automatizados e logs estruturados.",
        "",
    ]

    return "\n".join(lines)


def build_supplier_api_tests_py() -> str:
    """
    Gera testes automatizados com pytest para a API de fornecedores.
    """

    return r'''import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(autouse=True)
def usar_banco_de_teste(monkeypatch, tmp_path):
    """
    Cada teste usa um banco SQLite temporário próprio.

    No Windows, isso evita PermissionError ao tentar apagar um arquivo
    SQLite que ainda pode estar bloqueado por alguma conexão.
    """
    test_db_path = tmp_path / "test_fornecedores.db"

    monkeypatch.setattr(main, "DB_PATH", test_db_path)

    main.init_db()

    yield


@pytest.fixture
def client():
    return TestClient(main.app)


def fornecedor_valido():
    return {
        "razao_social": "3B-DOCTOR COMERCIO DE PRODUTOS MEDICOS LTDA",
        "cnpj": "04601824000178",
        "endereco": "Rua Exemplo, 100, Centro, Porto Alegre, RS, CEP 90000000",
        "contatos": [
            "Responsável - contato@exemplo.com - 51999999999"
        ],
    }


def test_health_retorna_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_cadastrar_fornecedor_com_cnpj_valido(client):
    payload = fornecedor_valido()

    response = client.post("/fornecedores", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["razao_social"] == payload["razao_social"]
    assert data["cnpj"] == payload["cnpj"]
    assert data["endereco"] == payload["endereco"]
    assert data["contatos"] == payload["contatos"]


def test_consultar_fornecedor_por_cnpj(client):
    payload = fornecedor_valido()

    client.post("/fornecedores", json=payload)

    response = client.get(f"/fornecedores/cnpj/{payload['cnpj']}")

    assert response.status_code == 200

    data = response.json()

    assert data["cnpj"] == payload["cnpj"]
    assert data["razao_social"] == payload["razao_social"]
    assert data["endereco"] == payload["endereco"]
    assert data["contatos"] == payload["contatos"]


def test_bloqueia_cnpj_duplicado(client):
    payload = fornecedor_valido()

    primeira_resposta = client.post("/fornecedores", json=payload)
    segunda_resposta = client.post("/fornecedores", json=payload)

    assert primeira_resposta.status_code == 200
    assert segunda_resposta.status_code == 409
    assert segunda_resposta.json()["detail"] == "Fornecedor já cadastrado para este CNPJ."


def test_rejeita_cnpj_invalido(client):
    payload = fornecedor_valido()
    payload["cnpj"] = "11111111111111"

    response = client.post("/fornecedores", json=payload)

    assert response.status_code == 422


def test_atualizar_fornecedor_por_cnpj(client):
    payload = fornecedor_valido()

    client.post("/fornecedores", json=payload)

    payload_atualizado = {
        "razao_social": "3B-DOCTOR COMERCIO DE PRODUTOS MEDICOS LTDA",
        "cnpj": "04601824000178",
        "endereco": "Rua Atualizada, 200, Porto Alegre, RS",
        "contatos": [
            "Responsável Atualizado - atualizado@exemplo.com - 51988888888"
        ],
    }

    response = client.put(
        f"/fornecedores/cnpj/{payload['cnpj']}",
        json=payload_atualizado,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["cnpj"] == payload_atualizado["cnpj"]
    assert data["razao_social"] == payload_atualizado["razao_social"]
    assert data["endereco"] == payload_atualizado["endereco"]
    assert data["contatos"] == payload_atualizado["contatos"]


def test_excluir_fornecedor_por_cnpj(client):
    payload = fornecedor_valido()

    client.post("/fornecedores", json=payload)

    delete_response = client.delete(f"/fornecedores/cnpj/{payload['cnpj']}")

    assert delete_response.status_code == 200
    assert delete_response.json()["cnpj"] == payload["cnpj"]

    get_response = client.get(f"/fornecedores/cnpj/{payload['cnpj']}")

    assert get_response.status_code == 404


def test_persistencia_sqlite_apos_nova_conexao(client):
    payload = fornecedor_valido()

    response = client.post("/fornecedores", json=payload)

    assert response.status_code == 200
    assert main.DB_PATH.exists()

    response = client.get(f"/fornecedores/cnpj/{payload['cnpj']}")

    assert response.status_code == 200
    assert response.json()["cnpj"] == payload["cnpj"]
'''


def ensure_files(files: Any, bug: str) -> Dict[str, str]:
    if not isinstance(files, dict):
        files = {}

    main_py = files.get("main.py")
    readme_md = files.get("README.md")
    requirements_txt = files.get("requirements.txt")

    if is_supplier_bug(bug):
        main_py = build_supplier_api_main_py()
        readme_md = generate_supplier_readme_sqlite(bug)
        files["test_fornecedores.py"] = build_supplier_api_tests_py()

    if is_supplier_bug(bug):
        requirements_txt = "fastapi\nuvicorn\npydantic\npytest\nhttpx\n"
    elif not requirements_txt:
        requirements_txt = "fastapi\nuvicorn\npydantic\n"

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
    test_cases = ensure_list(data.get("test_cases", []))

    if not test_cases:
        test_cases = ensure_list(data.get("tests", []))

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
                "E ao reiniciar a API os dados devem continuar persistidos no banco SQLite",
            ]

        if not technical_analysis:
            technical_analysis = (
                "O bug indica persistência parcial de fornecedor e perda de dados após reinício. "
                "A solução deve validar o CNPJ, impedir duplicidade e garantir que razão social, "
                "endereço e contatos sejam armazenados e recuperados corretamente usando SQLite."
            )

        if not solution_plan:
            solution_plan = [
                "Criar modelo de fornecedor com razão social, CNPJ, endereço e contatos.",
                "Implementar validação real de CNPJ.",
                "Criar banco SQLite fornecedores.db com tabela fornecedores.",
                "Implementar POST /fornecedores com bloqueio de CNPJ duplicado.",
                "Implementar GET /fornecedores para listagem.",
                "Implementar GET /fornecedores/cnpj/{cnpj} para consulta por CNPJ.",
                "Implementar PUT e DELETE por CNPJ.",
                "Testar cadastro, consulta, duplicidade, CNPJ inválido e persistência após reinício.",
            ]

        if not test_cases:
            test_cases = generate_fallback_test_cases(bug)

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

    if not test_cases:
        test_cases = generate_fallback_test_cases(bug)

    return {
        "user_story": user_story,
        "acceptance_criteria": acceptance_criteria,
        "technical_analysis": technical_analysis,
        "solution_plan": solution_plan,
        "test_cases": test_cases,
        "files": files,
    }