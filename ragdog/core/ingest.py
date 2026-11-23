"""Ingestion: file → hash → pages → chunks → ChromaDB."""

import hashlib

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

from ragdog.core.config import COLLECTION, DB_DIR

HASH_BLOCK_SIZE: int = 1024 * 1024  # 1 MB


def hash_file(path: str) -> str:
    """Return the SHA-256 hex digest of a file's bytes, read in 1 MB blocks."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(HASH_BLOCK_SIZE):
            digest.update(block)
    return digest.hexdigest()


def get_collection(db_dir: str = DB_DIR) -> Collection:
    """Open (or create) the persistent chunk collection, using cosine distance."""
    client = chromadb.PersistentClient(path=db_dir)
    return client.get_or_create_collection(
        name=COLLECTION,
        configuration={"hnsw": {"space": "cosine"}},  # fixed at creation
        embedding_function=ONNXMiniLM_L6_V2(),  # all-MiniLM-L6-v2, see EMBEDDING_MODEL
    )
