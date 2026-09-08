"""Application settings and model metadata."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    label: str
    input_usd_per_million: float
    output_usd_per_million: float
    description: str


MODEL_CATALOG: dict[str, ModelInfo] = {
    "claude-haiku-4-5-20251001": ModelInfo(
        label="Claude Haiku 4.5 · Budget",
        input_usd_per_million=1.0,
        output_usd_per_million=5.0,
        description="Fast and economical for summaries, quizzes, and short guidance.",
    ),
    "claude-sonnet-5": ModelInfo(
        label="Claude Sonnet 5 · Quality",
        input_usd_per_million=2.0,
        output_usd_per_million=10.0,
        description="Stronger reasoning for difficult concepts and nuanced coaching.",
    ),
}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return min(max(value, minimum), maximum)


@dataclass(frozen=True)
class AppConfig:
    default_model: str
    max_file_bytes: int
    max_files: int
    max_pdf_pages: int
    session_request_limit: int
    max_socratic_messages: int
    request_timeout_seconds: int

    @classmethod
    def from_env(cls) -> AppConfig:
        return cls(
            default_model=os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001").strip(),
            max_file_bytes=_env_int("MAX_FILE_MB", 8, 1, 25) * 1024 * 1024,
            max_files=_env_int("MAX_FILES", 5, 1, 10),
            max_pdf_pages=_env_int("MAX_PDF_PAGES", 80, 1, 300),
            session_request_limit=_env_int("SESSION_REQUEST_LIMIT", 12, 1, 100),
            max_socratic_messages=_env_int("MAX_SOCRATIC_MESSAGES", 8, 2, 30),
            request_timeout_seconds=_env_int("REQUEST_TIMEOUT_SECONDS", 90, 10, 300),
        )


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Estimate API cost from the documented list price for known models."""
    info = MODEL_CATALOG.get(model)
    if info is None:
        return None
    return (
        input_tokens * info.input_usd_per_million + output_tokens * info.output_usd_per_million
    ) / 1_000_000
