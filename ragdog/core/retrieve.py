"""Retrieval: question → embedding → closest stored chunks."""

from dataclasses import dataclass

from chromadb.api.types import QueryResult


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
