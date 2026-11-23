"""Tests for ragdog.core.ingest."""

import hashlib
from pathlib import Path

import pytest
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

from ragdog.core.config import COLLECTION, EMBEDDING_MODEL
from ragdog.core.ingest import (
    HASH_BLOCK_SIZE,
    already_ingested,
    get_collection,
    hash_file,
    read_document,
)


def test_hash_file_same_bytes_same_hash(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "renamed.txt"
    a.write_bytes(b"hello rag-dog")
    b.write_bytes(b"hello rag-dog")
    assert hash_file(str(a)) == hash_file(str(b))


def test_hash_file_different_bytes_different_hash(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_bytes(b"hello rag-dog")
    b.write_bytes(b"hello rag-cat")
    assert hash_file(str(a)) != hash_file(str(b))


def test_hash_file_spanning_blocks_matches_whole_file_hash(tmp_path: Path) -> None:
    data = b"x" * (HASH_BLOCK_SIZE * 2 + 123)  # forces 3 reads, last one partial
    path = tmp_path / "big.bin"
    path.write_bytes(data)
    assert hash_file(str(path)) == hashlib.sha256(data).hexdigest()


def test_get_collection_uses_cosine_and_configured_model(tmp_path: Path) -> None:
    col = get_collection(str(tmp_path))
    assert col.name == COLLECTION
    assert col.configuration["hnsw"]["space"] == "cosine"
    assert ONNXMiniLM_L6_V2.MODEL_NAME == EMBEDDING_MODEL  # rule 4: one model


def test_get_collection_persists_across_clients(tmp_path: Path) -> None:
    get_collection(str(tmp_path)).add(ids=["x"], documents=["hi"], embeddings=[[0.0] * 384])
    assert get_collection(str(tmp_path)).count() == 1


def test_already_ingested_true_only_for_stored_hash(tmp_path: Path) -> None:
    col = get_collection(str(tmp_path))
    assert not already_ingested(col, "abc")
    col.add(
        ids=["abc:0"],
        documents=["chunk"],
        embeddings=[[0.0] * 384],
        metadatas=[{"doc_hash": "abc"}],
    )
    assert already_ingested(col, "abc")
    assert not already_ingested(col, "def")


@pytest.mark.parametrize("name", ["notes.txt", "README.md", "SHOUTY.TXT"])
def test_read_document_text_files_are_one_page(tmp_path: Path, name: str) -> None:
    path = tmp_path / name
    path.write_text("# Title\n\nFirst paragraph.\n\nSecond — with a dash.", encoding="utf-8")
    assert read_document(str(path)) == [(1, "# Title\n\nFirst paragraph.\n\nSecond — with a dash.")]


@pytest.mark.parametrize("name", ["report.docx", "no_extension"])
def test_read_document_rejects_unsupported_types(tmp_path: Path, name: str) -> None:
    path = tmp_path / name
    path.write_bytes(b"whatever")
    with pytest.raises(ValueError, match="Unsupported file type"):
        read_document(str(path))


SAMPLE_PDF = Path(__file__).parent / "fixtures" / "sample-3-pages.pdf"


def test_read_document_pdf_keeps_page_numbers() -> None:
    pages = read_document(str(SAMPLE_PDF))
    assert [number for number, _ in pages] == [1, 2, 3]
    assert "Bulldogs were bred in England." in pages[0][1]
    assert "Retrieval finds the chunks." in pages[1][1]  # "ﬁ" ligature normalised
    assert "Generation writes the answer." in pages[1][1]
    assert "Citations name the page." in pages[2][1]
