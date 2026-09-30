"""
Configuração central da aplicação.

Todos os valores sensíveis ou dependentes de ambiente vêm de variáveis
de ambiente. Nenhum segredo deve ficar escrito no código.
"""

from __future__ import annotations

import logging
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("app.config")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    return value.strip().lower() in {"1", "true", "yes", "sim", "on"}


def _env_list(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]


# ------------------------------------------------------------
# Ambiente
# ------------------------------------------------------------

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()

# O Render define RENDER=true em todos os serviços. Tratamos isso como
# produção mesmo que ENVIRONMENT não tenha sido configurado, para que um
# deploy esquecido nunca rode com configurações de desenvolvimento.
IS_PRODUCTION = ENVIRONMENT == "production" or os.getenv("RENDER", "").lower() == "true"


# ------------------------------------------------------------
# Autenticação (JWT)
# ------------------------------------------------------------

def _load_secret_key() -> str:
    value = os.getenv("SECRET_KEY", "").strip()

    if value:
        if IS_PRODUCTION and len(value) < 32:
            raise RuntimeError(
                "SECRET_KEY muito curta para produção. Use pelo menos 32 caracteres "
                "(ex.: python -c \"import secrets; print(secrets.token_urlsafe(48))\")."
            )
        return value

    if IS_PRODUCTION:
        raise RuntimeError(
            "SECRET_KEY não definida. Configure a variável de ambiente SECRET_KEY "
            "antes de subir em produção."
        )

    # Em desenvolvimento geramos uma chave aleatória por processo.
    # Consequência: tokens deixam de valer quando o servidor reinicia.
    logger.warning(
        "SECRET_KEY não definida; usando chave aleatória temporária (apenas desenvolvimento)."
    )
    return secrets.token_urlsafe(48)


SECRET_KEY = _load_secret_key()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))


# ------------------------------------------------------------
# Admin de desenvolvimento
# ------------------------------------------------------------

# Nunca é criado em produção, independentemente de CREATE_DEV_ADMIN.
CREATE_DEV_ADMIN = (not IS_PRODUCTION) and _env_bool("CREATE_DEV_ADMIN", default=False)
DEV_ADMIN_EMAIL = os.getenv("DEV_ADMIN_EMAIL", "admin@exemplo.com")
DEV_ADMIN_PASSWORD = os.getenv("DEV_ADMIN_PASSWORD", "")


# ------------------------------------------------------------
# HTTP
# ------------------------------------------------------------

# Origens autorizadas a chamar a API a partir de outro domínio.
# O frontend atual é servido pela própria API, então por padrão é vazio.
CORS_ORIGINS = _env_list("CORS_ORIGINS")

# Swagger (/docs) e OpenAPI ficam desligados em produção por padrão.
DOCS_ENABLED = _env_bool("DOCS_ENABLED", default=not IS_PRODUCTION)


# ------------------------------------------------------------
# Limites de requisição (formato do slowapi: "N/period")
# ------------------------------------------------------------

RATE_LIMIT_ENABLED = _env_bool("RATE_LIMIT_ENABLED", default=True)
RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "10/minute")
RATE_LIMIT_REGISTER = os.getenv("RATE_LIMIT_REGISTER", "5/minute")
RATE_LIMIT_GENERATE = os.getenv("RATE_LIMIT_GENERATE", "6/minute")


# ------------------------------------------------------------
# LLM e custo
# ------------------------------------------------------------

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Preço em US$ por 1 milhão de tokens do modelo configurado.
# Padrões = preço público do gpt-4o-mini; confira a tabela da OpenAI
# e ajuste ao trocar de modelo.
LLM_PRICE_INPUT_PER_1M = float(os.getenv("LLM_PRICE_INPUT_PER_1M", "0.15"))
LLM_PRICE_OUTPUT_PER_1M = float(os.getenv("LLM_PRICE_OUTPUT_PER_1M", "0.60"))


# ------------------------------------------------------------
# Fila de gerações
# ------------------------------------------------------------

# Quantas gerações rodam ao mesmo tempo nesta instância.
JOB_WORKERS = int(os.getenv("JOB_WORKERS", "2"))

# Quantas gerações o mesmo usuário pode ter na fila ao mesmo tempo.
MAX_PENDING_JOBS_PER_USER = int(os.getenv("MAX_PENDING_JOBS_PER_USER", "2"))


# ------------------------------------------------------------
# Armazenamento dos projetos gerados
# ------------------------------------------------------------

# Pasta local (cache de trabalho). No Render, aponte para um Disk
# persistente ou configure o armazenamento S3 abaixo.
# Caminhos relativos são resolvidos a partir da raiz do repositório.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATED_PROJECTS_DIR = os.path.join(
    _REPO_ROOT, os.getenv("GENERATED_PROJECTS_DIR", "generated_projects")
)

# Armazenamento de objetos compatível com S3 (AWS S3, Cloudflare R2, MinIO...).
# Se STORAGE_BUCKET ficar vazio, os projetos ficam só no disco local.
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "").strip()
STORAGE_ENDPOINT_URL = os.getenv("STORAGE_ENDPOINT_URL", "").strip() or None
STORAGE_REGION = os.getenv("STORAGE_REGION", "auto")
STORAGE_PREFIX = os.getenv("STORAGE_PREFIX", "generated_projects/").strip()


# ------------------------------------------------------------
# Cobrança (Asaas)
# ------------------------------------------------------------

# Sandbox: https://api-sandbox.asaas.com/v3  |  Produção: https://api.asaas.com/v3
# As chaves de sandbox e produção são diferentes e não funcionam trocadas.
ASAAS_BASE_URL = os.getenv("ASAAS_BASE_URL", "https://api-sandbox.asaas.com/v3").rstrip("/")
ASAAS_API_KEY = os.getenv("ASAAS_API_KEY", "").strip()

# Token que a Asaas envia no cabeçalho "asaas-access-token" de cada webhook.
# Defina o mesmo valor no painel da Asaas (Integrações → Webhooks).
ASAAS_WEBHOOK_TOKEN = os.getenv("ASAAS_WEBHOOK_TOKEN", "").strip()

# Preço mensal (R$) de cada plano pago. Os limites de geração ficam em
# app/services/usage_service.py (PLAN_LIMITS).
PLAN_PRICES = {
    "pro": float(os.getenv("PLAN_PRICE_PRO", "49.90")),
    "team": float(os.getenv("PLAN_PRICE_TEAM", "199.90")),
}

# Dias de tolerância após o fim do período pago antes de voltar ao plano free
# (cobre atraso de compensação de boleto e retentativas de cartão).
BILLING_GRACE_DAYS = int(os.getenv("BILLING_GRACE_DAYS", "3"))


def billing_enabled() -> bool:
    return bool(ASAAS_API_KEY)


# ------------------------------------------------------------
# Dados do vendedor e documentos legais
# ------------------------------------------------------------

# Exibidos no rodapé, nos Termos de Uso e na Política de Privacidade.
# O Decreto 7.962/2013 (comércio eletrônico) exige nome e CPF/CNPJ do
# fornecedor visíveis no site. Ficam em variáveis de ambiente para não
# gravar dados pessoais no repositório (que é público).
SELLER_NAME = os.getenv("SELLER_NAME", "").strip()
SELLER_DOCUMENT = os.getenv("SELLER_DOCUMENT", "").strip()
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "").strip()
SELLER_CITY = os.getenv("SELLER_CITY", "Porto Alegre/RS").strip()

# Versão vigente dos Termos/Política. Ao mudar o texto de forma relevante,
# altere esta data: quem aceitou uma versão anterior precisa aceitar de
# novo antes de contratar um plano.
TERMS_VERSION = os.getenv("TERMS_VERSION", "2026-09-30").strip()
