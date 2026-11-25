"""rag-dog's web page: upload documents, ask questions, get answers with their sources.

Run with `make run` (uv run streamlit run app.py). It calls ragdog.core directly (decision 007).
"""

import os
import tempfile
from pathlib import Path

import streamlit as st
from chromadb.api.models.Collection import Collection
from dotenv import load_dotenv

from ragdog.core.config import SUPPORTED_EXTENSIONS
from ragdog.core.ingest import already_ingested, get_collection, hash_file, ingest_file

ASSETS = Path(__file__).resolve().parent / "assets"
UPLOAD_TYPES = sorted(ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS)  # ["md", "pdf", "txt"]
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
    return f"✅ {filename}: added {added} chunk{'' if added == 1 else 's'}"


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

    st.chat_input("Ask a question about your documents", disabled=not key_set)


if __name__ == "__main__":
    main()
