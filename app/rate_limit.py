"""
Limite de requisições por IP (proteção contra força bruta e abuso de custo).

Usa armazenamento em memória, suficiente para uma única instância.
Com mais de uma instância, configure RATE_LIMIT_STORAGE_URI=redis://...
"""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import RATE_LIMIT_ENABLED

limiter = Limiter(
    key_func=get_remote_address,
    enabled=RATE_LIMIT_ENABLED,
    storage_uri=os.getenv("RATE_LIMIT_STORAGE_URI", "memory://"),
)
