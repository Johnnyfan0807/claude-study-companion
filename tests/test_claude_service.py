from types import SimpleNamespace

import pytest

from src.claude_service import ClaudeService, ClaudeServiceError


class _FakeMessages:
    def count_tokens(self, **kwargs):
        assert kwargs["model"] == "test-model"
        return SimpleNamespace(input_tokens=42)

    def create(self, **kwargs):
        assert kwargs["max_tokens"] == 500
        assert "temperature" not in kwargs
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="Study response")],
            usage=SimpleNamespace(input_tokens=42, output_tokens=9),
            stop_reason="end_turn",
            _request_id="req_test",
        )


class _FakeClient:
    def __init__(self, **kwargs):
        assert kwargs["api_key"] == "x" * 24
        self.messages = _FakeMessages()


def test_service_counts_and_generates(monkeypatch) -> None:
    monkeypatch.setattr("src.claude_service.Anthropic", _FakeClient)
    service = ClaudeService("x" * 24, "test-model")
    messages = [{"role": "user", "content": "hello"}]
    assert service.count_tokens(system="system", messages=messages) == 42
    result = service.generate(system="system", messages=messages, max_tokens=500)
    assert result.text == "Study response"
    assert result.output_tokens == 9


def test_service_rejects_short_key() -> None:
    with pytest.raises(ClaudeServiceError, match="valid Claude API key"):
        ClaudeService("short", "test-model")
