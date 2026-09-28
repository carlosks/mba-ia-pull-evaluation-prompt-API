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
