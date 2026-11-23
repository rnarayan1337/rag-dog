"""Tests for ragdog.core.generate (no network: the API client is faked)."""

from ragdog.core.generate import document_blocks
from ragdog.core.retrieve import RetrievedChunk


def make_chunk(text: str = "Error E2210 means the jar is not seated.", page: int = 3) -> RetrievedChunk:
    """A RetrievedChunk with defaults for the fields a test doesn't care about."""
    return RetrievedChunk(
        text=text, filename="acme-handbook.pdf", page=page, chunk_index=0, doc_hash="h", distance=0.2
    )


# --- document_blocks ---


def test_document_blocks_builds_one_cited_text_document_per_chunk() -> None:
    chunk = make_chunk()
    assert document_blocks([chunk]) == [
        {
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": chunk.text},
            "title": "acme-handbook.pdf p.3",
            "citations": {"enabled": True},
        }
    ]


def test_document_blocks_keeps_retrieval_order() -> None:
    chunks = [make_chunk("first", page=2), make_chunk("second", page=1)]
    blocks = document_blocks(chunks)
    assert [b["source"]["data"] for b in blocks] == ["first", "second"]
    assert [b["title"] for b in blocks] == ["acme-handbook.pdf p.2", "acme-handbook.pdf p.1"]


def test_document_blocks_empty_list_gives_no_blocks() -> None:
    assert document_blocks([]) == []
