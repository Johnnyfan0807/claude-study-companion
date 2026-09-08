"""Small, testable wrapper around the official Anthropic Python SDK."""

from __future__ import annotations

from dataclasses import dataclass

import anthropic
from anthropic import Anthropic


class ClaudeServiceError(RuntimeError):
    """A safe, user-facing Claude API error."""


@dataclass(frozen=True)
class GenerationResult:
    text: str
    input_tokens: int
    output_tokens: int
    stop_reason: str | None
    request_id: str | None


class ClaudeService:
    def __init__(self, api_key: str, model: str, timeout_seconds: int = 90) -> None:
        if not api_key or len(api_key.strip()) < 20:
            raise ClaudeServiceError("Please provide a valid Claude API key.")
        self.model = model
        try:
            self.client = Anthropic(
                api_key=api_key.strip(),
                timeout=float(timeout_seconds),
                max_retries=2,
            )
        except Exception as exc:
            raise self._safe_error(exc, operation="initialize the Claude client") from None

    def close(self) -> None:
        close = getattr(self.client, "close", None)
        if callable(close):
            close()

    def count_tokens(self, *, system: str, messages: list[dict[str, str]]) -> int:
        try:
            result = self.client.messages.count_tokens(
                model=self.model,
                system=system,
                messages=messages,
            )
            return int(result.input_tokens)
        except Exception as exc:  # mapped below; keeps credentials out of the UI
            raise self._safe_error(exc, operation="count tokens") from None

    def generate(
        self,
        *,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
    ) -> GenerationResult:
        try:
            message = self.client.messages.create(
                model=self.model,
                system=system,
                messages=messages,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            raise self._safe_error(exc, operation="generate a response") from None

        text = "".join(
            getattr(block, "text", "")
            for block in message.content
            if getattr(block, "type", "") == "text"
        ).strip()
        if not text:
            raise ClaudeServiceError("Claude returned no text. Please try again.")

        return GenerationResult(
            text=text,
            input_tokens=int(message.usage.input_tokens),
            output_tokens=int(message.usage.output_tokens),
            stop_reason=getattr(message, "stop_reason", None),
            request_id=getattr(message, "_request_id", None),
        )

    @staticmethod
    def _safe_error(exc: Exception, *, operation: str) -> ClaudeServiceError:
        if isinstance(exc, anthropic.AuthenticationError):
            return ClaudeServiceError("Claude rejected the API key. Check the key and try again.")
        if isinstance(exc, anthropic.RateLimitError):
            return ClaudeServiceError(
                "The Claude API rate limit was reached. Wait briefly and try again."
            )
        if isinstance(exc, anthropic.APIConnectionError):
            return ClaudeServiceError(
                "Could not reach the Claude API. Check your internet connection."
            )
        if isinstance(exc, anthropic.BadRequestError):
            return ClaudeServiceError(
                "Claude could not process this request. Reduce the note or token limit."
            )
        if isinstance(exc, anthropic.APIStatusError):
            request_id = getattr(exc, "request_id", None)
            suffix = f" Reference: {request_id}." if request_id else ""
            return ClaudeServiceError(f"Claude API error while trying to {operation}.{suffix}")
        return ClaudeServiceError(
            f"Unexpected error while trying to {operation}. Please try again."
        )
