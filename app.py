"""rag-dog's web page: upload documents, ask questions, get answers with their sources.

Run with `make run` (uv run streamlit run app.py). It calls ragdog.core directly (decision 007).
"""

import os
from pathlib import Path

import streamlit as st
from chromadb.api.models.Collection import Collection
from dotenv import load_dotenv

from ragdog.core.ingest import get_collection

ASSETS = Path(__file__).resolve().parent / "assets"
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

    with st.sidebar:
        st.header("Documents")

    st.chat_input("Ask a question about your documents", disabled=not key_set)


if __name__ == "__main__":
    main()
