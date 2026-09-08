from src.config import estimate_cost_usd


def test_known_model_cost_is_calculated() -> None:
    cost = estimate_cost_usd("claude-haiku-4-5-20251001", 1_000_000, 1_000_000)
    assert cost == 6.0


def test_unknown_model_cost_is_not_guessed() -> None:
    assert estimate_cost_usd("future-model", 100, 100) is None
