"""
Cliente mínimo da API v3 da Asaas.

Documentação: https://docs.asaas.com
- Autenticação pelo cabeçalho "access_token".
- Sandbox e produção têm URLs e chaves diferentes (ver app.config).

Dados de cartão NUNCA passam por este sistema: o cliente paga na página
de fatura da própria Asaas (invoiceUrl), que aceita Pix, boleto e cartão.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app import config

logger = logging.getLogger("app.asaas")

# Substituível nos testes (httpx.MockTransport).
transport: httpx.BaseTransport | None = None


class AsaasError(Exception):
    """Erro retornado pela Asaas ou falha de comunicação."""

    def __init__(self, message: str, status_code: int | None = None, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


def _client() -> httpx.Client:
    if not config.ASAAS_API_KEY:
        raise AsaasError("Cobrança não configurada (ASAAS_API_KEY ausente).")

    return httpx.Client(
        base_url=config.ASAAS_BASE_URL,
        headers={
            "access_token": config.ASAAS_API_KEY,
            "Content-Type": "application/json",
            "User-Agent": "mba-ia-bug-evaluation",
        },
        timeout=20.0,
        transport=transport,
    )


def _request(method: str, path: str, **kwargs) -> dict:
    try:
        with _client() as client:
            response = client.request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        logger.exception("Falha de comunicação com a Asaas: %s %s", method, path)
        raise AsaasError("Não foi possível contatar o provedor de pagamento.") from exc

    if response.status_code >= 400:
        try:
            body = response.json()
        except ValueError:
            body = response.text

        # A Asaas devolve {"errors": [{"code": ..., "description": ...}]}.
        description = None
        if isinstance(body, dict) and body.get("errors"):
            description = body["errors"][0].get("description")

        logger.warning(
            "Asaas respondeu %s em %s %s: %s", response.status_code, method, path, body
        )
        raise AsaasError(
            description or f"Erro {response.status_code} no provedor de pagamento.",
            status_code=response.status_code,
            details=body,
        )

    if not response.content:
        return {}

    return response.json()


def create_customer(name: str, cpf_cnpj: str, email: str, external_reference: str) -> dict:
    return _request(
        "POST",
        "/customers",
        json={
            "name": name,
            "cpfCnpj": cpf_cnpj,
            "email": email,
            "externalReference": external_reference,
        },
    )


def create_subscription(
    customer_id: str,
    value: float,
    next_due_date: str,
    description: str,
    external_reference: str,
) -> dict:
    return _request(
        "POST",
        "/subscriptions",
        json={
            "customer": customer_id,
            # UNDEFINED: o cliente escolhe Pix, boleto ou cartão na fatura.
            "billingType": "UNDEFINED",
            "value": round(value, 2),
            "nextDueDate": next_due_date,
            "cycle": "MONTHLY",
            "description": description,
            "externalReference": external_reference,
        },
    )


def list_subscription_payments(subscription_id: str) -> list[dict]:
    data = _request("GET", f"/subscriptions/{subscription_id}/payments")
    return data.get("data", []) if isinstance(data, dict) else []


def delete_subscription(subscription_id: str) -> dict:
    return _request("DELETE", f"/subscriptions/{subscription_id}")
