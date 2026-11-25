"""UI tests for app.py, using Streamlit's AppTest. No model download, no network, no cost."""

from pathlib import Path

import dotenv
import pytest
import streamlit as st
from chromadb.api.models.Collection import Collection
from streamlit.testing.v1 import AppTest

import app
import ragdog.core.ingest

APP = str(Path(__file__).resolve().parent.parent / "app.py")
TEXT = b"Error E2210 means the jar is not seated correctly. Lift the jar and seat it again."


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test sets the environment itself, so app.py must not load the real .env."""
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)


@pytest.fixture(autouse=True)
def fake_db(monkeypatch: pytest.MonkeyPatch, fake_collection: Collection) -> Collection:
    """The app gets a temp collection with a fake embedding, not .ragdog_db and the real model.

    The cache is cleared so one test's collection doesn't leak into the next.
    """
    st.cache_resource.clear()
    monkeypatch.setattr(ragdog.core.ingest, "get_collection", lambda: fake_collection)
    return fake_collection


def run_app() -> AppTest:
    """Run app.py once, the way a browser's first visit does, and fail on any exception."""
    at = AppTest.from_file(APP)
    at.run()
    assert not at.exception
    return at


def upload(at: AppTest, *files: tuple[str, bytes]) -> list[str]:
    """Put files in the uploader, rerun, and return the sidebar's status lines."""
    at.sidebar.file_uploader[0].set_value([(name, data, "text/plain") for name, data in files])
    at.run()
    assert not at.exception
    return sidebar_lines(at)


def sidebar_lines(at: AppTest) -> list[str]:
    return [element.value for element in at.sidebar.markdown]


# --- page ---


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


# --- ingest_upload, called directly ---


def test_ingest_upload_stores_original_name_not_temp_path(fake_db: Collection) -> None:
    status = app.ingest_upload("handbook.txt", TEXT, fake_db)
    assert status == "✅ handbook.txt: added 1 chunk"
    [meta] = fake_db.get(include=["metadatas"])["metadatas"]
    assert (meta["filename"], meta["file_location"]) == ("handbook.txt", "handbook.txt")


def test_ingest_upload_drops_folder_part_of_name(fake_db: Collection) -> None:
    assert app.ingest_upload("../../etc/notes.txt", TEXT, fake_db).startswith("✅ notes.txt:")


def test_ingest_upload_tells_duplicate_from_no_text(fake_db: Collection) -> None:
    app.ingest_upload("handbook.txt", TEXT, fake_db)
    assert app.ingest_upload("renamed.txt", TEXT, fake_db) == "↩️ renamed.txt: already uploaded"
    assert app.ingest_upload("blank.txt", b"  \n\n ", fake_db) == (
        "⚠️ blank.txt: no text found (is it a scanned PDF?)"
    )
    assert fake_db.count() == 1


def test_ingest_upload_reports_unreadable_file(fake_db: Collection) -> None:
    status = app.ingest_upload("broken.pdf", b"not really a PDF", fake_db)
    assert status.startswith("❌ broken.pdf: couldn't read it")
    assert fake_db.count() == 0


# --- uploader, through the page ---


def test_upload_shows_one_status_per_file(fake_db: Collection) -> None:
    at = run_app()
    lines = upload(at, ("handbook.txt", TEXT), ("copy.txt", TEXT), ("blank.txt", b""))
    assert lines == [
        "✅ handbook.txt: added 1 chunk",
        "↩️ copy.txt: already uploaded",
        "⚠️ blank.txt: no text found (is it a scanned PDF?)",
    ]
    assert fake_db.count() == 1


def test_rerun_does_not_ingest_again(fake_db: Collection) -> None:
    """Any click reruns the script with the files still in the uploader."""
    at = run_app()
    first = upload(at, ("handbook.txt", TEXT))
    at.run()
    assert sidebar_lines(at) == first == ["✅ handbook.txt: added 1 chunk"]
    assert fake_db.count() == 1
