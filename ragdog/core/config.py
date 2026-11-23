"""Settings for ragdog.core. See specs/001-ingestion/plan.md and specs/002-retrieval/plan.md."""

DB_DIR: str = ".ragdog_db"
COLLECTION: str = "docs"

CHUNK_SIZE: int = 800  # characters; keeps chunks under the model's ~256-token limit
CHUNK_OVERLAP: int = 150  # characters carried into the next chunk

EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # must match for documents and queries

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".md", ".txt"})

TOP_K: int = 5  # chunks returned per question (~1,000 tokens of context for the LLM)
