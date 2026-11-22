"""Tests for ragdog.core.ingest."""

import hashlib
from pathlib import Path

from ragdog.core.ingest import HASH_BLOCK_SIZE, hash_file


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
