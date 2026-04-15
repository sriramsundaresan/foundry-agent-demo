"""Validate the prompt file before deployment."""

from pathlib import Path


PROMPT_FILE = Path(__file__).parent.parent / "agents" / "prompt.md"


def test_prompt_file_exists():
    assert PROMPT_FILE.exists(), f"Prompt file not found: {PROMPT_FILE}"


def test_prompt_not_empty():
    content = PROMPT_FILE.read_text(encoding="utf-8").strip()
    assert len(content) > 0, "Prompt file is empty"


def test_prompt_has_guidelines():
    content = PROMPT_FILE.read_text(encoding="utf-8")
    assert "##" in content, "Prompt should have at least one section heading"


def test_prompt_reasonable_length():
    content = PROMPT_FILE.read_text(encoding="utf-8")
    assert len(content) < 50_000, "Prompt file is too large (>50KB)"
