"""Retrieval: question → embedding → closest stored chunks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedChunk:
    """One stored chunk returned for a question, with what's needed to cite it."""

    text: str
    filename: str
    page: int
    chunk_index: int
    doc_hash: str
    distance: float  # cosine distance: 0 = same direction, higher = less similar
