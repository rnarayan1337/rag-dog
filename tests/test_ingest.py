"""Tests for ragdog.core.ingest."""

import hashlib
from pathlib import Path

from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

from ragdog.core.config import COLLECTION, EMBEDDING_MODEL
from ragdog.core.ingest import HASH_BLOCK_SIZE, get_collection, hash_file


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
