"""Tests for ragdog.core.retrieve."""

from typing import Any

import pytest
from chromadb.api.models.Collection import Collection

import ragdog.core.retrieve as retrieve_module
from ragdog.core.config import TOP_K
from ragdog.core.ingest import upsert_chunks
from ragdog.core.retrieve import RetrievedChunk, retrieve, to_chunks


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


def store(collection: Collection, texts: list[str]) -> None:
    """Store texts as one document's chunks, one per page."""
    chunks = [(index + 1, index, text) for index, text in enumerate(texts)]  # page = index + 1
    upsert_chunks(collection, chunks, "abc", "docs/sample.txt")


def test_retrieve_returns_closest_first_with_all_fields(fake_collection: Collection) -> None:
    # FakeEmbedding encodes length, so the text of exactly the question's length is closest
    store(fake_collection, ["x" * 5, "y" * 20, "z" * 100])
    results = retrieve("q" * 20, k=3, collection=fake_collection)
    assert results[0].text == "y" * 20
    assert [r.distance for r in results] == sorted(r.distance for r in results)
    assert results[0] == RetrievedChunk("y" * 20, "sample.txt", 2, 1, "abc", results[0].distance)


def test_retrieve_defaults_to_top_k(fake_collection: Collection) -> None:
    store(fake_collection, [f"chunk {'.' * n}" for n in range(TOP_K + 2)])
    assert len(retrieve("question", collection=fake_collection)) == TOP_K


def test_retrieve_k_larger_than_collection_returns_all(fake_collection: Collection) -> None:
    store(fake_collection, ["one", "two words"])
    assert len(retrieve("question", k=10, collection=fake_collection)) == 2


def test_retrieve_empty_collection_returns_nothing(fake_collection: Collection) -> None:
    assert retrieve("anything?", collection=fake_collection) == []


@pytest.mark.parametrize("question", ["", "   ", "\n"])
def test_retrieve_rejects_blank_question(fake_collection: Collection, question: str) -> None:
    with pytest.raises(ValueError, match="empty"):
        retrieve(question, collection=fake_collection)


def test_retrieve_rejects_k_below_one(fake_collection: Collection) -> None:
    with pytest.raises(ValueError, match="k must be"):
        retrieve("question", k=0, collection=fake_collection)


def test_retrieve_without_collection_uses_get_collection(
    fake_collection: Collection, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[bool] = []

    def fake_get_collection() -> Collection:
        calls.append(True)
        return fake_collection

    monkeypatch.setattr(retrieve_module, "get_collection", fake_get_collection)
    retrieve("question")
    assert calls == [True]


def test_retrieve_doc_hash_filter_searches_one_document(fake_collection: Collection) -> None:
    upsert_chunks(fake_collection, [(1, 0, "a" * 20), (2, 1, "b" * 30)], "doc-a", "a.txt")
    upsert_chunks(fake_collection, [(1, 0, "c" * 20), (2, 1, "d" * 30)], "doc-b", "b.txt")
    everything = retrieve("q" * 20, k=10, collection=fake_collection)
    only_b = retrieve("q" * 20, k=10, doc_hash="doc-b", collection=fake_collection)
    assert {r.doc_hash for r in everything} == {"doc-a", "doc-b"}
    assert [r.filename for r in only_b] == ["b.txt", "b.txt"]
    assert {r.doc_hash for r in only_b} == {"doc-b"}


def test_retrieve_unknown_doc_hash_returns_nothing(fake_collection: Collection) -> None:
    store(fake_collection, ["some text"])
    assert retrieve("question", doc_hash="not-stored", collection=fake_collection) == []
