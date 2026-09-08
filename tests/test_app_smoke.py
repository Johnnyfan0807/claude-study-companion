from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_renders_without_api_key() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=20)
    assert len(app.exception) == 0
