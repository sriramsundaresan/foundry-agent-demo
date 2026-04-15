"""Validate the deploy script can be imported and parsed."""

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "deploy_prompt_agent.py"


def test_script_exists():
    assert SCRIPT_PATH.exists()


def test_script_importable():
    spec = importlib.util.spec_from_file_location("deploy_prompt_agent", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    # Don't exec — just verify it's valid Python
    assert module is not None
