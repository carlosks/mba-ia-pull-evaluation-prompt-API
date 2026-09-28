"""
Mede tokens e custo das chamadas ao LLM feitas dentro de um bloco.

Uso:
    with measure_llm_usage() as usage:
        ... chamadas LangChain ...
    usage.cost_usd  # custo estimado da execução
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

from langchain_core.callbacks import get_usage_metadata_callback

from app.config import LLM_MODEL, LLM_PRICE_INPUT_PER_1M, LLM_PRICE_OUTPUT_PER_1M


@dataclass
class LLMUsage:
    model: str = LLM_MODEL
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0
    per_model: dict = field(default_factory=dict)

    @property
    def cost_usd(self) -> float:
        cost = (
            self.input_tokens * LLM_PRICE_INPUT_PER_1M
            + self.output_tokens * LLM_PRICE_OUTPUT_PER_1M
        ) / 1_000_000
        return round(cost, 6)

    def as_log_fields(self) -> dict:
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "duration_ms": self.duration_ms,
        }


@contextmanager
def measure_llm_usage() -> Iterator[LLMUsage]:
    usage = LLMUsage()
    started = time.perf_counter()

    with get_usage_metadata_callback() as callback:
        try:
            yield usage
        finally:
            usage.duration_ms = int((time.perf_counter() - started) * 1000)
            usage.per_model = dict(callback.usage_metadata or {})
            for model_name, metadata in usage.per_model.items():
                usage.input_tokens += int(metadata.get("input_tokens", 0) or 0)
                usage.output_tokens += int(metadata.get("output_tokens", 0) or 0)
                usage.model = model_name
