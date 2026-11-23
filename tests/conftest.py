"""Shared pytest fixtures."""

from pathlib import Path

import chromadb
import pytest
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings


class FakeEmbedding(EmbeddingFunction[Documents]):
    """Tiny stand-in for the real model, so tests need no download."""

    def __init__(self) -> None:
        pass

    def __call__(self, input: Documents) -> Embeddings:
        return [[float(len(text)), 1.0, 0.0] for text in input]

    @staticmethod
    def name() -> str:
        return "fake"

    def get_config(self) -> dict[str, object]:
        return {}

    @staticmethod
    def build_from_config(config: dict[str, object]) -> "FakeEmbedding":
        return FakeEmbedding()


@pytest.fixture
def fake_collection(tmp_path: Path) -> Collection:
    """An empty collection in a temp dir that embeds with FakeEmbedding."""
    client = chromadb.PersistentClient(path=str(tmp_path / "db"))
    return client.get_or_create_collection("test-docs", embedding_function=FakeEmbedding())
