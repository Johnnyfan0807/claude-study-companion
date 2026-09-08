import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_anthropic_key_is_present_in_repository() -> None:
    key_pattern = re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")
    excluded_parts = {".git", ".venv", "__pycache__"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in excluded_parts for part in path.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        assert key_pattern.search(content) is None, f"Possible API key in {path}"


def test_real_secret_files_are_gitignored() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".streamlit/secrets.toml" in ignore
    assert ".env" in ignore
