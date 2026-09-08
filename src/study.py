"""Token-budget preparation and output helpers."""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass

from src.prompts import ANSWER_KEY_MARKER

MessageFactory = Callable[[str], list[dict[str, str]]]
TokenCounter = Callable[[str, list[dict[str, str]]], int]


class TokenBudgetError(ValueError):
    """Raised when a request cannot fit within the selected input budget."""


@dataclass(frozen=True)
class PreparedRequest:
    messages: list[dict[str, str]]
    input_tokens: int
    notes_used: str
    notes_truncated: bool


def approximate_token_count(text: str) -> int:
    """Conservative local preview; exact enforcement uses Claude's API."""
    if not text:
        return 0
    cjk = len(re.findall(r"[\u3400-\u9fff\uf900-\ufaff]", text))
    non_cjk = max(len(text) - cjk, 0)
    return max(1, cjk + math.ceil(non_cjk / 3.6))


def _evenly_reduce(text: str, target_chars: int) -> str:
    """Keep excerpts across the whole source when a strict budget is selected."""
    if target_chars >= len(text):
        return text
    if target_chars < 600:
        return text[:target_chars]

    marker = "\n\n[... material omitted to respect the selected token budget ...]\n\n"
    segment_count = min(6, max(2, target_chars // 2_000))
    usable = target_chars - len(marker) * (segment_count - 1)
    if usable < segment_count * 100:
        return text[:target_chars]
    segment_size = usable // segment_count
    max_start = max(len(text) - segment_size, 0)
    starts = [round(index * max_start / (segment_count - 1)) for index in range(segment_count)]
    pieces = [text[start : start + segment_size].strip() for start in starts]
    return marker.join(piece for piece in pieces if piece)


def prepare_with_budget(
    *,
    notes: str,
    system: str,
    message_factory: MessageFactory,
    count_tokens: TokenCounter,
    max_input_tokens: int,
) -> PreparedRequest:
    """Use the official counter and reduce note excerpts if the cap is exceeded."""
    if not notes.strip():
        raise TokenBudgetError("Add lecture notes before generating.")
    if max_input_tokens < 1_000:
        raise TokenBudgetError("The input-token budget must be at least 1,000.")

    notes_used = notes
    messages = message_factory(notes_used)
    input_tokens = count_tokens(system, messages)
    truncated = False

    for _ in range(3):
        if input_tokens <= max_input_tokens:
            return PreparedRequest(messages, input_tokens, notes_used, truncated)
        ratio = max_input_tokens / max(input_tokens, 1)
        target_chars = max(500, int(len(notes_used) * ratio * 0.82))
        if target_chars >= len(notes_used):
            break
        notes_used = _evenly_reduce(notes_used, target_chars)
        truncated = True
        messages = message_factory(notes_used)
        input_tokens = count_tokens(system, messages)

    if input_tokens > max_input_tokens:
        raise TokenBudgetError(
            "The request still exceeds the selected token budget. Increase the budget "
            "or use shorter notes/instructions."
        )
    return PreparedRequest(messages, input_tokens, notes_used, truncated)


def split_quiz_output(text: str) -> tuple[str, str | None]:
    if ANSWER_KEY_MARKER not in text:
        return text.strip(), None
    questions, answers = text.split(ANSWER_KEY_MARKER, maxsplit=1)
    return questions.strip(), answers.strip() or None


def trim_socratic_history(history: list[dict[str, str]], max_messages: int) -> list[dict[str, str]]:
    """Keep recent turns while preserving an assistant-first history when possible."""
    if len(history) <= max_messages:
        return list(history)
    trimmed = list(history[-max_messages:])
    while trimmed and trimmed[0]["role"] == "user":
        trimmed.pop(0)
    return trimmed
