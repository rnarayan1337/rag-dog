"""Ingestion: file → hash → pages → chunks → ChromaDB."""

import hashlib
import unicodedata
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
from pypdf import PdfReader

from ragdog.core.config import COLLECTION, DB_DIR, SUPPORTED_EXTENSIONS

HASH_BLOCK_SIZE: int = 1024 * 1024  # 1 MB


def hash_file(path: str) -> str:
    """Return the SHA-256 hex digest of a file's bytes, read in 1 MB blocks."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(HASH_BLOCK_SIZE):
            digest.update(block)
    return digest.hexdigest()


def get_collection(db_dir: str = DB_DIR) -> Collection:
    """Open (or create) the persistent chunk collection, using cosine distance."""
    client = chromadb.PersistentClient(path=db_dir)
    return client.get_or_create_collection(
        name=COLLECTION,
        configuration={"hnsw": {"space": "cosine"}},  # fixed at creation
        embedding_function=ONNXMiniLM_L6_V2(),  # all-MiniLM-L6-v2, see EMBEDDING_MODEL
    )


def already_ingested(collection: Collection, doc_hash: str) -> bool:
    """Return True if any chunk from the document with this hash is stored."""
    found = collection.get(where={"doc_hash": doc_hash}, limit=1, include=[])
    return len(found["ids"]) > 0


def read_text(path: str) -> list[tuple[int, str]]:
    """Read a .txt or .md file as a single page 1."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return [(1, text)]


def read_pdf(path: str) -> list[tuple[int, str]]:
    """Read a PDF as one (page, text) pair per page, numbered from 1."""
    reader = PdfReader(path)
    return [
        # NFKC turns ligatures like "ﬁ" back into plain "fi"
        (number, unicodedata.normalize("NFKC", page.extract_text() or ""))
        for number, page in enumerate(reader.pages, start=1)
    ]


def read_document(path: str) -> list[tuple[int, str]]:
    """Return a document's text as (page, text) pairs; raise ValueError if unsupported."""
    ext = Path(path).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type {ext or '(none)'!r}; expected one of {supported}")
    if ext == ".pdf":
        return read_pdf(path)
    return read_text(path)
