"""Tests for ragdog.core.retrieve."""

from typing import Any

import pytest

from ragdog.core.retrieve import RetrievedChunk, to_chunks


def query_result(**overrides: Any) -> Any:
    """A Chroma-shaped query result for one question with two hits."""
    result = {
        "ids": [["abc:2", "abc:0"]],
        "documents": [["Error E2210 means the jar is loose.", "Welcome to Acme."]],
        "metadatas": [
            [
                {"filename": "acme.pdf", "page": 3, "chunk_index": 2, "doc_hash": "abc"},
                {"filename": "acme.pdf", "page": 1, "chunk_index": 0, "doc_hash": "abc"},
            ]
        ],
        "distances": [[0.41, 0.93]],
        "embeddings": None,
        "uris": None,
        "data": None,
        "included": ["documents", "metadatas", "distances"],
    }
    result.update(overrides)
    return result


def test_to_chunks_maps_fields_in_order() -> None:
    assert to_chunks(query_result()) == [
        RetrievedChunk("Error E2210 means the jar is loose.", "acme.pdf", 3, 2, "abc", 0.41),
        RetrievedChunk("Welcome to Acme.", "acme.pdf", 1, 0, "abc", 0.93),
    ]


def test_to_chunks_no_hits_is_empty() -> None:
    empty = query_result(ids=[[]], documents=[[]], metadatas=[[]], distances=[[]])
    assert to_chunks(empty) == []


def test_to_chunks_missing_field_says_what_to_include() -> None:
    with pytest.raises(ValueError, match="include="):
        to_chunks(query_result(distances=None))
