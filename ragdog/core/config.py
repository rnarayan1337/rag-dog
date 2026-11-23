"""Settings for ragdog.core. See the plan.md files under specs/ (001, 002, 003)."""

DB_DIR: str = ".ragdog_db"
COLLECTION: str = "docs"

CHUNK_SIZE: int = 800  # characters; keeps chunks under the model's ~256-token limit
CHUNK_OVERLAP: int = 150  # characters carried into the next chunk

EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # must match for documents and queries

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".md", ".txt"})

TOP_K: int = 5  # chunks returned per question (~1,000 tokens of context for the LLM)

LLM_MODEL: str = "claude-haiku-5-5"  # cheapest tier; enough for short answers from 5 chunks
LLM_EFFORT: str = "low"  # how much the model thinks; Haiku 5.5 defaults to "medium"
LLM_MAX_TOKENS: int = 16000  # thinking counts toward this, so leave room beyond the answer
