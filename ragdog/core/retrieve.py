"""Retrieval: question → embedding → closest stored chunks."""

from dataclasses import dataclass

from chromadb.api.models.Collection import Collection
from chromadb.api.types import QueryResult

from ragdog.core.config import TOP_K
from ragdog.core.ingest import get_collection


@dataclass(frozen=True)
class RetrievedChunk:
    """One stored chunk returned for a question, with what's needed to cite it."""

    text: str
    filename: str
    page: int
    chunk_index: int
    doc_hash: str
    distance: float  # cosine distance: 0 = same direction, higher = less similar


def to_chunks(result: QueryResult) -> list[RetrievedChunk]:
    """Turn Chroma's result for a single question into RetrievedChunks, closest first.

    Chroma returns one inner list per question; we always send one, so we read index [0].
    """
    documents, metadatas, distances = (
        result["documents"],
        result["metadatas"],
        result["distances"],
    )
    if documents is None or metadatas is None or distances is None:
        raise ValueError('query must include=["documents", "metadatas", "distances"]')
    if not documents:
        return []
    return [
        RetrievedChunk(
            text=text,
            filename=str(meta["filename"]),
            page=int(meta["page"]),
            chunk_index=int(meta["chunk_index"]),
            doc_hash=str(meta["doc_hash"]),
            distance=float(distance),
        )
        for text, meta, distance in zip(documents[0], metadatas[0], distances[0], strict=True)
    ]


def retrieve(
    question: str,
    k: int = TOP_K,
    doc_hash: str | None = None,
    collection: Collection | None = None,
) -> list[RetrievedChunk]:
    """Return up to k stored chunks closest in meaning to the question, closest first.

    If doc_hash is given, only that document's chunks are searched.
    """
    if not question.strip():
        raise ValueError("Question is empty")
    if k < 1:
        raise ValueError(f"k must be at least 1, got {k}")
    if collection is None:
        collection = get_collection()  # same embedding model as ingestion (Rule 4)
    result = collection.query(
        query_texts=[question],
        n_results=k,
        where={"doc_hash": doc_hash} if doc_hash else None,
        include=["documents", "metadatas", "distances"],
    )
    return to_chunks(result)
