from src.study import (
    approximate_token_count,
    prepare_with_budget,
    split_quiz_output,
    trim_socratic_history,
)


def test_multilingual_token_preview_counts_cjk_conservatively() -> None:
    assert approximate_token_count("概率") >= 2
    assert approximate_token_count("probability") >= 1


def test_budget_reduces_long_notes() -> None:
    notes = "paragraph " * 5_000

    def messages(value: str) -> list[dict[str, str]]:
        return [{"role": "user", "content": value}]

    def counter(system: str, payload: list[dict[str, str]]) -> int:
        del system
        return len(payload[0]["content"]) // 4

    prepared = prepare_with_budget(
        notes=notes,
        system="system",
        message_factory=messages,
        count_tokens=counter,
        max_input_tokens=2_000,
    )
    assert prepared.notes_truncated is True
    assert prepared.input_tokens <= 2_000
    assert "material omitted" in prepared.notes_used


def test_quiz_answer_key_is_split() -> None:
    questions, answers = split_quiz_output("Questions\n---ANSWER-KEY---\nAnswers")
    assert questions == "Questions"
    assert answers == "Answers"


def test_socratic_history_keeps_recent_assistant_first() -> None:
    history = [
        {"role": "assistant", "content": "q1"},
        {"role": "user", "content": "a1"},
        {"role": "assistant", "content": "q2"},
        {"role": "user", "content": "a2"},
        {"role": "assistant", "content": "q3"},
    ]
    trimmed = trim_socratic_history(history, 3)
    assert trimmed[0]["role"] == "assistant"
    assert len(trimmed) == 3
