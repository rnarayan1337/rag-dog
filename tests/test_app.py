"""UI tests for app.py, using Streamlit's AppTest. No model download, no network, no cost."""

import tomllib
from pathlib import Path

import dotenv
import pytest
import streamlit as st
from chromadb.api.models.Collection import Collection
from streamlit.testing.v1 import AppTest

import app
import ragdog.core.generate
import ragdog.core.ingest
from ragdog.core.generate import Answer, Citation, GenerationError
from ragdog.core.ingest import DocumentInfo, upsert_chunks
from ragdog.core.retrieve import RetrievedChunk

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
    return status_lines(at)


STATUS_ICONS = ("✅", "↩️", "⚠️", "❌")


def status_lines(at: AppTest) -> list[str]:
    """The uploader's per-file lines (the document list is markdown too, so filter by icon)."""
    return [md.value for md in at.sidebar.markdown if md.value.startswith(STATUS_ICONS)]


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
    assert status_lines(at) == first == ["✅ handbook.txt: added 1 chunk"]
    assert fake_db.count() == 1


# --- document list and "Search in" ---


def test_document_labels_unique_filenames() -> None:
    documents = [DocumentInfo("a.pdf", "1111aaaa", 3), DocumentInfo("b.txt", "2222bbbb", 1)]
    assert app.document_labels(documents) == {
        "All documents": None,
        "a.pdf": "1111aaaa",
        "b.txt": "2222bbbb",
    }


def test_document_labels_same_filename_adds_hash() -> None:
    documents = [
        DocumentInfo("report.pdf", "aaaa1111ffff", 3),
        DocumentInfo("report.pdf", "bbbb2222ffff", 4),
    ]
    assert list(app.document_labels(documents)) == [
        "All documents",
        "report.pdf (aaaa1111)",
        "report.pdf (bbbb2222)",
    ]


def test_no_documents_yet() -> None:
    at = run_app()
    assert at.sidebar.caption[-1].value == "No documents yet."
    assert len(at.sidebar.selectbox) == 0


def test_stored_documents_listed_on_first_visit(fake_db: Collection) -> None:
    """The list is read from the database, so it survives a restart (criterion 2)."""
    upsert_chunks(fake_db, [(1, 0, "One."), (2, 1, "Two.")], "hash-a", "manual.pdf")
    at = run_app()
    assert at.sidebar.markdown[-1].value == "- manual.pdf · 2 chunks"
    assert at.sidebar.selectbox[0].options == ["All documents", "manual.pdf"]
    assert at.sidebar.selectbox[0].value == "All documents"


def test_upload_appears_in_list_straight_away() -> None:
    at = run_app()
    upload(at, ("handbook.txt", TEXT))
    assert at.sidebar.markdown[-1].value == "- handbook.txt · 1 chunk"
    assert at.sidebar.selectbox[0].options == ["All documents", "handbook.txt"]


# --- sources ---


def cite(quote: str, filename: str = "acme-handbook.pdf", page: int = 3) -> Citation:
    chunk = RetrievedChunk(quote, filename, page, chunk_index=0, doc_hash="h", distance=0.3)
    return Citation(chunk=chunk, cited_text=quote)


def test_sources_none() -> None:
    assert app.sources([]) == []


def test_sources_format_and_whitespace() -> None:
    lines = app.sources([cite("Error E2210 means\nthe jar is  not seated. ")])
    assert lines == ["acme-handbook.pdf · p.3 — “Error E2210 means the jar is not seated.”"]


def test_sources_drops_repeats_keeps_order() -> None:
    lines = app.sources(
        [
            cite("Descale the machine.", page=3),
            cite("Opened products: 14 days.", page=1),
            cite("Descale the machine.", page=3),
        ]
    )
    assert lines == [
        "acme-handbook.pdf · p.3 — “Descale the machine.”",
        "acme-handbook.pdf · p.1 — “Opened products: 14 days.”",
    ]


def test_sources_same_quote_in_two_places_is_kept_twice() -> None:
    """A footer repeated on two pages is two sources, not one."""
    lines = app.sources([cite("Acme Ltd.", page=1), cite("Acme Ltd.", page=2)])
    assert len(lines) == 2


# --- chat ---


class FakeGenerate:
    """Stands in for generate_answer: records each call and returns a canned answer.

    The answer cites the first chunk twice, to check the sources are de-duplicated.
    """

    def __init__(self, text: str = "E2210 means the jar is not seated.", error: str = "") -> None:
        self.text = text
        self.error = error
        self.calls: list[tuple[str, list[RetrievedChunk]]] = []

    def __call__(self, question: str, chunks: list[RetrievedChunk]) -> Answer:
        self.calls.append((question, chunks))
        if self.error:
            raise GenerationError(self.error)
        citations = [Citation(chunks[0], chunks[0].text)] * 2 if chunks else []
        return Answer(self.text, citations, input_tokens=100, output_tokens=20)


@pytest.fixture
def fake_generate(monkeypatch: pytest.MonkeyPatch) -> FakeGenerate:
    """No API call: app.py imports generate_answer when it runs, so it gets this one."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    fake = FakeGenerate()
    monkeypatch.setattr(ragdog.core.generate, "generate_answer", fake)
    return fake


def ask(at: AppTest, question: str) -> AppTest:
    at.chat_input[0].set_value(question).run()
    assert not at.exception
    return at


def store_two_documents(collection: Collection) -> None:
    upsert_chunks(collection, [(3, 0, "Error E2210: jar not seated.")], "hash-a", "handbook.pdf")
    upsert_chunks(collection, [(1, 0, "Lunch is at noon.")], "hash-b", "notes.txt")


def test_question_gets_answer_and_sources(
    fake_db: Collection, fake_generate: FakeGenerate
) -> None:
    upsert_chunks(fake_db, [(3, 0, "Error E2210: jar not seated.")], "hash-a", "handbook.pdf")
    at = ask(run_app(), "What does E2210 mean?")
    question, reply = at.chat_message
    assert (question.name, question.markdown[0].value) == ("user", "What does E2210 mean?")
    assert reply.name == "assistant"
    assert reply.markdown[0].value == "E2210 means the jar is not seated."
    assert reply.caption[0].value == "Sources"
    assert reply.markdown[1].value == "1. handbook.pdf · p.3 — “Error E2210: jar not seated.”"


def test_history_kept_between_questions(fake_db: Collection, fake_generate: FakeGenerate) -> None:
    store_two_documents(fake_db)
    at = ask(ask(run_app(), "First?"), "Second?")
    assert [m.name for m in at.chat_message] == ["user", "assistant", "user", "assistant"]
    assert [q for q, _ in fake_generate.calls] == ["First?", "Second?"]


def test_search_in_one_document(fake_db: Collection, fake_generate: FakeGenerate) -> None:
    store_two_documents(fake_db)
    at = run_app()
    at.sidebar.selectbox[0].select("notes.txt").run()
    ask(at, "When is lunch?")
    _, chunks = fake_generate.calls[-1]
    assert {chunk.doc_hash for chunk in chunks} == {"hash-b"}


def test_search_all_documents_by_default(fake_db: Collection, fake_generate: FakeGenerate) -> None:
    store_two_documents(fake_db)
    ask(run_app(), "Anything?")
    _, chunks = fake_generate.calls[-1]
    assert {chunk.doc_hash for chunk in chunks} == {"hash-a", "hash-b"}


def test_no_documents_passes_no_chunks(fake_generate: FakeGenerate) -> None:
    """generate_answer then gives its fixed "no documents" answer without calling the API."""
    ask(run_app(), "Anything?")
    assert fake_generate.calls == [("Anything?", [])]


def test_generation_error_shown_and_app_keeps_working(
    fake_db: Collection, fake_generate: FakeGenerate
) -> None:
    store_two_documents(fake_db)
    fake_generate.error = "Claude API call failed: overloaded"
    at = ask(run_app(), "First?")
    assert at.chat_message[1].error[0].value == "Claude API call failed: overloaded"
    fake_generate.error = ""
    ask(at, "Second?")
    assert at.chat_message[3].markdown[0].value == "E2210 means the jar is not seated."


def test_blank_question_is_ignored(fake_generate: FakeGenerate) -> None:
    at = ask(run_app(), "   ")
    assert len(at.chat_message) == 0
    assert fake_generate.calls == []


def test_dollar_signs_are_not_maths(fake_db: Collection, fake_generate: FakeGenerate) -> None:
    upsert_chunks(fake_db, [(2, 0, "Mini $59, Turbo $129.")], "hash-a", "price_list.pdf")
    fake_generate.text = "The Mini is $59 and the Turbo is $129."
    reply = ask(run_app(), "Prices?").chat_message[1]
    assert reply.markdown[0].value == r"The Mini is \$59 and the Turbo is \$129."
    assert reply.markdown[1].value == r"1. price\_list.pdf · p.2 — “Mini \$59, Turbo \$129.”"


def test_escape_markdown() -> None:
    assert app.escape_markdown("*a* _b_ $1 <x> [y] #z") == r"\*a\* \_b\_ \$1 \<x\> \[y\] \#z"


# --- Streamlit settings ---


def streamlit_config() -> dict:
    """The committed `.streamlit/config.toml`, parsed."""
    config_file = Path(APP).parent / ".streamlit" / "config.toml"
    return tomllib.loads(config_file.read_text(encoding="utf-8"))


def test_streamlit_config_turns_usage_stats_off() -> None:
    """Streamlit sends anonymous usage statistics unless told not to (005)."""
    config = streamlit_config()
    assert config["browser"]["gatherUsageStats"] is False
    assert config["client"]["toolbarMode"] == "viewer"


def test_streamlit_config_listens_on_this_machine_only() -> None:
    """`make run` isn't reachable from the network: others could spend the key (005)."""
    assert streamlit_config()["server"]["address"] == "localhost"
