from src.prompts import ANSWER_KEY_MARKER, base_system_prompt, notes_block, quiz_message


def test_system_prompt_marks_notes_as_untrusted() -> None:
    prompt = base_system_prompt(language="English", academic_level="undergraduate")
    assert "untrusted source material" in prompt
    assert "Respond in clear English" in prompt


def test_notes_boundary_changes_with_content() -> None:
    assert notes_block("alpha") != notes_block("beta")


def test_quiz_requests_hidden_answer_marker() -> None:
    prompt = quiz_message(
        "notes",
        count=5,
        difficulty="Intermediate",
        question_types=["Short answer"],
        focus="",
    )
    assert ANSWER_KEY_MARKER in prompt
    assert "exactly 5" in prompt
