"""
Dados do vendedor e aceite dos Termos de Uso / Política de Privacidade.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import config, models

TERMS_REQUIRED_MESSAGE = (
    "É preciso aceitar os Termos de Uso e a Política de Privacidade para continuar."
)


def format_document(value: str) -> str:
    """Formata CPF (000.000.000-00) ou CNPJ (00.000.000/0000-00)."""
    digits = "".join(ch for ch in value or "" if ch.isdigit())

    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"

    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"

    return value or ""


def document_label(value: str) -> str:
    digits = "".join(ch for ch in value or "" if ch.isdigit())
    return "CNPJ" if len(digits) == 14 else "CPF"


def public_info() -> dict:
    return {
        "seller_name": config.SELLER_NAME,
        "seller_document": format_document(config.SELLER_DOCUMENT),
        "seller_document_label": document_label(config.SELLER_DOCUMENT),
        "seller_city": config.SELLER_CITY,
        "contact_email": config.CONTACT_EMAIL,
        "terms_version": config.TERMS_VERSION,
    }


def has_current_terms(user: models.User) -> bool:
    return bool(user.terms_accepted_at) and user.terms_version == config.TERMS_VERSION


def record_acceptance(user: models.User) -> None:
    """Marca o aceite da versão vigente (sem commit)."""
    user.terms_version = config.TERMS_VERSION
    user.terms_accepted_at = datetime.now(timezone.utc).replace(tzinfo=None)


def require_terms(db: Session, user: models.User, accepted_now: bool) -> None:
    """
    Garante que o usuário aceitou a versão vigente dos termos.
    Se ele marcou o aceite agora, registra; senão, recusa.
    """
    if has_current_terms(user):
        return

    if not accepted_now:
        raise HTTPException(status_code=400, detail=TERMS_REQUIRED_MESSAGE)

    record_acceptance(user)
    db.add(user)
    db.commit()
    db.refresh(user)
