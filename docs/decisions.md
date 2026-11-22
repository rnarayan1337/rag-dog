# Decision Log

Each entry records what we chose, why, what we gave up, and when to revisit it.
Add a new entry whenever a decision is made or changed — in the same PR as the code.

---

## 001 — Build without a framework (no LangChain)
*2026-11-21*

- **Decision:** Plain Anthropic SDK + ChromaDB.
- **Why:** The whole loop is ~100 lines. Writing it by hand means every step can be explained.
- **Trade-off:** More code to write; no ready-made integrations.
- **Revisit when:** v1 works — rebuilding in LangChain/LlamaIndex is a good comparison exercise.

## 002 — Vector store: ChromaDB, persistent mode
*2026-11-21*

- **Decision:** ChromaDB `PersistentClient`, cosine distance.
- **Why:** Open source, runs in-process, no account or server. Persistent mode keeps embeddings across restarts.
- **Trade-off:** Not built for large-scale production (vs. Pinecone, pgvector, etc.).
- **Note:** Distance metric is fixed when the collection is created.
- **Revisit when:** Multi-user or millions of chunks.

## 003 — Embedding model: all-MiniLM-L6-v2
*2026-11-21*

- **Decision:** ChromaDB's default local model (384 dimensions).
- **Why:** Free, local, private, fast, no API key.
- **Trade-off:** Moderate quality, English-centric, ~256-token input limit (longer text is silently truncated).
- **Rule:** The same model must embed both documents and queries.
- **Revisit when:** The golden set shows retrieval misses. Shortlist from MTEB Retrieval, compare on recall@k.
- **Migration plan:** Blue/green — re-embed into a new collection, evaluate, switch, drop old.

## 004 — Chunking: recursive, per page
*2026-11-21*

- **Decision:** Recursive splitting (paragraph → sentence → word), ~800 chars, ~150 overlap, within each page.
- **Why:** Respects natural boundaries; fits the embedding model's token limit; overlap keeps ideas that straddle a boundary intact; per-page gives page numbers for citations.
- **Trade-off:** Chunks never cross page boundaries.
- **Revisit when:** Answers miss context that spans pages (fix: concatenate with a page-offset map).

## 005 — Chunk ID and metadata schema
*2026-11-21*

- **Decision:** `id = f"{doc_hash}:{chunk_index}"`
- **Metadata:** `doc_hash`, `filename`, `file_location`, `chunk_index`, `page`, `embedding_model`
- **Why:** Unique and stable. A pure chunk-text hash was rejected: identical text in two documents (footers, disclaimers) would collide and overwrite citations.
- **Note:** Chunk text is stored alongside its vector, so re-embedding doesn't need the original files.

## 006 — Dedup by content hash
*2026-11-21*

- **Decision:** SHA-256 of file bytes, read in 1 MB blocks.
- **Why:** Same content → same hash regardless of filename. Streaming keeps memory flat for large files.
- **Rejected:** File metadata (size/mtime) — unreliable, and browser uploads don't provide mtime.
- **Open:** Updated document with the same filename → delete old chunks for that filename (not in v1).

## 007 — Architecture: monolith with a UI-free core
*2026-11-21*

- **Decision:** Streamlit calls `ragdog/core/` directly. `core/` never imports UI or HTTP code.
- **Why:** Fastest path to v1, while keeping a clean seam for a FastAPI layer later.
- **Trade-off:** No API for other clients in v1.
- **Revisit when:** A second client (CLI, Slack bot) is needed — see roadmap 009.

## 008 — v1 ingestion: browser upload
*2026-11-21*

- **Decision:** Users upload files through the UI (not a mounted folder).
- **Why:** Zero setup for someone trying the demo.
- **Note:** Parsing and chunking happen in Python either way.

## 009 — v1 scope: happy path only
*2026-11-21*

- **Decision:** No guardrails, re-ranking, or eval in v1.
- **Why:** Get the full loop working end to end first, then harden.

## 010 — Tooling
*2026-11-21*

- **Decision:** `uv` for environment and dependencies; signed commits required on `main`.
- **Why:** Fast, single tool with a lockfile; signed commits prove authorship.
