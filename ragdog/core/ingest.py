"""Ingestion: file → hash → pages → chunks → ChromaDB."""

import hashlib
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
from pypdf import PdfReader

from ragdog.core.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION,
    DB_DIR,
    EMBEDDING_MODEL,
    SUPPORTED_EXTENSIONS,
)

HASH_BLOCK_SIZE: int = 1024 * 1024  # 1 MB
UPSERT_BATCH_SIZE: int = 500  # chunks embedded and stored per call
SEPARATORS: tuple[str, ...] = ("\n\n", ". ", " ")  # paragraph → sentence → word


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


@dataclass(frozen=True)
class DocumentInfo:
    """One stored document, as the UI lists it."""

    filename: str
    doc_hash: str
    chunks: int


def list_documents(collection: Collection | None = None) -> list[DocumentInfo]:
    """Return one entry per stored document, read from chunk metadata, sorted by filename."""
    if collection is None:
        collection = get_collection()
    metadatas = collection.get(include=["metadatas"])["metadatas"] or []
    counts: Counter[str] = Counter()
    filenames: dict[str, str] = {}
    for meta in metadatas:
        doc_hash = str(meta["doc_hash"])
        counts[doc_hash] += 1
        filenames[doc_hash] = str(meta["filename"])
    documents = [DocumentInfo(filenames[h], h, n) for h, n in counts.items()]
    return sorted(documents, key=lambda d: (d.filename, d.doc_hash))


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


def split_text(text: str, size: int, separators: tuple[str, ...] = SEPARATORS) -> list[str]:
    """Split text into pieces of at most `size` chars, trying separators in order.

    Separators stay attached to the end of each piece, so "".join(pieces) == text.
    """
    if len(text) <= size:
        return [text]
    if not separators:  # no natural boundary left: cut at exactly `size`
        return [text[i : i + size] for i in range(0, len(text), size)]
    sep, finer = separators[0], separators[1:]
    parts = text.split(sep)
    parts = [part + sep for part in parts[:-1]] + [parts[-1]]
    pieces: list[str] = []
    for part in parts:
        pieces.extend(split_text(part, size, finer))
    return pieces


def overlap_tail(chunk: str, overlap: int) -> str:
    """Return the last `overlap` chars of a chunk, starting at a word boundary."""
    if overlap <= 0:
        return ""
    tail = chunk[-overlap:]
    if " " in tail and len(chunk) > overlap:  # drop the cut-off word at the front
        tail = tail[tail.index(" ") + 1 :]
    return tail


def pack_pieces(pieces: list[str], size: int, overlap: int) -> list[str]:
    """Join pieces into chunks of at most `size` chars; each new chunk starts with
    the tail of the previous one."""
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) > size:
            chunks.append(current)
            room = size - len(piece)
            tail = overlap_tail(current, min(overlap, room))
            current = tail
        current += piece
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk.strip()]


def chunk_pages(
    pages: list[tuple[int, str]],
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[tuple[int, int, str]]:
    """Chunk each page separately; return (page, chunk_index, text).

    chunk_index counts across the whole document, not per page.
    """
    chunks: list[tuple[int, int, str]] = []
    for page, text in pages:
        for chunk in pack_pieces(split_text(text, size), size, overlap):
            chunks.append((page, len(chunks), chunk))
    return chunks


def upsert_chunks(
    collection: Collection,
    chunks: list[tuple[int, int, str]],
    doc_hash: str,
    path: str,
    batch_size: int = UPSERT_BATCH_SIZE,
    file_location: str | None = None,
) -> int:
    """Embed and store chunks with their ids and metadata; return how many were stored.

    file_location is stored instead of path when given (an upload's temp path is deleted).
    """
    filename = Path(path).name
    location = file_location or path
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        collection.upsert(
            ids=[f"{doc_hash}:{index}" for _, index, _ in batch],
            documents=[text for _, _, text in batch],
            metadatas=[
                {
                    "doc_hash": doc_hash,
                    "filename": filename,
                    "file_location": location,
                    "chunk_index": index,
                    "page": page,
                    "embedding_model": EMBEDDING_MODEL,
                }
                for page, index, _ in batch
            ],
        )
    return len(chunks)


def ingest_file(
    path: str,
    collection: Collection | None = None,
    file_location: str | None = None,
) -> int:
    """Hash, read, chunk, and store a file; return chunks stored (0 if already ingested).

    file_location overrides what's recorded as the file's location (default: path).
    """
    if collection is None:
        collection = get_collection()
    doc_hash = hash_file(path)
    if already_ingested(collection, doc_hash):
        return 0
    pages = read_document(path)
    chunks = chunk_pages(pages)
    return upsert_chunks(collection, chunks, doc_hash, path, file_location=file_location)
