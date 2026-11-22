"""Ingestion: file → hash → pages → chunks → ChromaDB."""

import hashlib

HASH_BLOCK_SIZE: int = 1024 * 1024  # 1 MB


def hash_file(path: str) -> str:
    """Return the SHA-256 hex digest of a file's bytes, read in 1 MB blocks."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(HASH_BLOCK_SIZE):
            digest.update(block)
    return digest.hexdigest()
