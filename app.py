"""rag-dog's web page: upload documents, ask questions, get answers with their sources.

Run with `make run` (uv run streamlit run app.py). It calls ragdog.core directly (decision 007).
"""

import os
import re
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import streamlit as st
from chromadb.api.models.Collection import Collection
from dotenv import load_dotenv

from ragdog.core.config import SUPPORTED_EXTENSIONS
from ragdog.core.generate import Citation, GenerationError, generate_answer
from ragdog.core.ingest import (
    DocumentInfo,
    already_ingested,
    get_collection,
    hash_file,
    ingest_file,
    list_documents,
)
from ragdog.core.retrieve import retrieve

ASSETS = Path(__file__).resolve().parent / "assets"
UPLOAD_TYPES = sorted(ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS)  # ["md", "pdf", "txt"]
ALL_DOCUMENTS = "All documents"
# Characters Streamlit's markdown would treat as formatting ($ starts maths)
MARKDOWN_SPECIAL = re.compile(r"([\\`*_\[\]<>#$~|])")
NO_KEY_WARNING = (
    "`ANTHROPIC_API_KEY` is not set, so questions can't be answered. "
    "Add it to `.env` and restart the app."
)


@st.cache_resource
def open_collection() -> Collection:
    """Open the database and load the embedding model once per server, not on every rerun."""
    return get_collection()


def has_api_key() -> bool:
    """True if the key is in the environment. The key itself is never read or shown here."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def chunk_count(n: int) -> str:
    """Say "1 chunk" or "4 chunks"."""
    return f"{n} chunk{'' if n == 1 else 's'}"


def ingest_upload(name: str, data: bytes, collection: Collection) -> str:
    """Store one uploaded file and return a one-line status for the sidebar.

    The bytes go to a temp file under the original name, so the stored filename is right,
    and the original name is recorded as its location, since the temp file is deleted.
    """
    filename = Path(name).name  # drop any folder part
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / filename)
        Path(path).write_bytes(data)
        # Checked here so that a 0 from ingest_file can only mean "no text"
        if already_ingested(collection, hash_file(path)):
            return f"↩️ {filename}: already uploaded"
        try:
            added = ingest_file(path, collection, file_location=filename)
        except Exception as e:  # report it and let the other files carry on
            return f"❌ {filename}: couldn't read it ({e})"
    if added == 0:
        return f"⚠️ {filename}: no text found (is it a scanned PDF?)"
    return f"✅ {filename}: added {chunk_count(added)}"


def upload_sidebar(collection: Collection) -> None:
    """The uploader, plus one status line per file in it.

    Streamlit reruns the script on every click and the uploader keeps its files, so each
    file's status is kept in session_state by file_id and each file is ingested only once.
    """
    statuses: dict[str, str] = st.session_state.setdefault("upload_status", {})
    uploads = st.file_uploader(
        "Upload documents", type=UPLOAD_TYPES, accept_multiple_files=True
    )
    for upload in uploads or []:
        if upload.file_id not in statuses:
            with st.spinner(f"Reading {upload.name}…"):
                statuses[upload.file_id] = ingest_upload(
                    upload.name, upload.getvalue(), collection
                )
        st.markdown(statuses[upload.file_id])


def document_labels(documents: list[DocumentInfo]) -> dict[str, str | None]:
    """Map each label to the doc_hash it stands for; "All documents" maps to None.

    Two documents with the same filename (e.g. an edited report.pdf) get the start of
    their hash added, so the labels stay unique.
    """
    repeated = Counter(doc.filename for doc in documents)
    labels: dict[str, str | None] = {ALL_DOCUMENTS: None}
    for doc in documents:
        label = doc.filename
        if repeated[doc.filename] > 1:
            label = f"{doc.filename} ({doc.doc_hash[:8]})"
        labels[label] = doc.doc_hash
    return labels


def documents_sidebar(collection: Collection) -> str | None:
    """List the stored documents and return the doc_hash to search (None = all of them)."""
    st.subheader("Stored")
    documents = list_documents(collection)
    if not documents:
        st.caption("No documents yet.")
        return None
    labels = document_labels(documents)
    chunks = {doc.doc_hash: doc.chunks for doc in documents}
    st.markdown(
        "\n".join(
            f"- {label} · {chunk_count(chunks[doc_hash])}"
            for label, doc_hash in labels.items()
            if doc_hash is not None
        )
    )
    choice = st.selectbox("Search in", list(labels))
    return labels[choice]


def sources(citations: list[Citation]) -> list[str]:
    """One line per distinct quote, in answer order: 'file · p.3 — “quoted text”'.

    Whitespace is collapsed (PDF text keeps its line breaks), and a line already listed is
    skipped, so a sentence cited twice shows once. Plain text: escaping is the caller's job.
    """
    lines: list[str] = []
    for citation in citations:
        quote = " ".join(citation.cited_text.split())
        line = f"{citation.chunk.filename} · p.{citation.chunk.page} — “{quote}”"
        if line not in lines:
            lines.append(line)
    return lines


def escape_markdown(text: str) -> str:
    """Make document text show as typed: "$59 or $129" isn't maths, "*" isn't bold."""
    return MARKDOWN_SPECIAL.sub(r"\\\1", text)


@dataclass(frozen=True)
class ChatMessage:
    """One message in the chat history. Strings only, so session state stays small."""

    role: Literal["user", "assistant"]
    text: str
    sources: tuple[str, ...] = ()
    error: bool = False


def ask(question: str, search_in: str | None, collection: Collection) -> ChatMessage:
    """Retrieve chunks for the question and get Claude's cited answer (or the error)."""
    chunks = retrieve(question, doc_hash=search_in, collection=collection)
    try:
        answer = generate_answer(question, chunks)
    except GenerationError as e:
        return ChatMessage("assistant", str(e), error=True)
    return ChatMessage("assistant", answer.text, sources=tuple(sources(answer.citations)))


def show_message(message: ChatMessage) -> None:
    """Draw one chat message, with its numbered sources under an answer."""
    with st.chat_message(message.role):
        if message.error:
            st.error(message.text)
            return
        if message.role == "user":
            st.markdown(escape_markdown(message.text))
            return
        # Claude's own formatting (bold, lists) is kept; only "$" is escaped, so prices
        # aren't drawn as maths.
        st.markdown(message.text.replace("$", r"\$"))
        if message.sources:
            st.caption("Sources")
            st.markdown(
                "\n".join(
                    f"{number}. {escape_markdown(line)}"
                    for number, line in enumerate(message.sources, start=1)
                )
            )


def main() -> None:
    """Draw the page. Streamlit runs this top to bottom on every interaction."""
    load_dotenv()  # entry point only, never ragdog/core (Rule 8)
    st.set_page_config(page_title="rag-dog", page_icon=str(ASSETS / "favicon.png"))
    st.logo(str(ASSETS / "logo.png"))
    st.title("rag-dog")
    st.caption("Upload documents, ask questions, get answers with their sources.")

    key_set = has_api_key()
    if not key_set:
        st.warning(NO_KEY_WARNING)

    collection = open_collection()
    with st.sidebar:
        st.header("Documents")
        upload_sidebar(collection)
        search_in = documents_sidebar(collection)  # after uploads, so new files are listed

    messages: list[ChatMessage] = st.session_state.setdefault("messages", [])
    for message in messages:  # the page is redrawn from scratch on every rerun
        show_message(message)

    question = st.chat_input("Ask a question about your documents", disabled=not key_set)
    if question and question.strip():
        asked = ChatMessage("user", question)
        messages.append(asked)
        show_message(asked)
        with st.spinner("Searching your documents and asking Claude…"):
            reply = ask(question, search_in, collection)
        messages.append(reply)
        show_message(reply)


if __name__ == "__main__":
    main()
