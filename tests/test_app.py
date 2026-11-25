"""UI tests for app.py, using Streamlit's AppTest. No model download, no network, no cost."""

from pathlib import Path

import dotenv
import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test sets the environment itself, so app.py must not load the real .env."""
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)


def run_app() -> AppTest:
    """Run app.py once, the way a browser's first visit does, and fail on any exception."""
    at = AppTest.from_file(APP)
    at.run()
    assert not at.exception
    return at


def test_page_loads_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    at = run_app()
    assert at.title[0].value == "rag-dog"
    assert len(at.warning) == 0
    assert not at.chat_input[0].proto.disabled


def test_missing_key_warns_and_disables_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    at = run_app()
    assert "ANTHROPIC_API_KEY" in at.warning[0].value
    assert at.chat_input[0].proto.disabled
