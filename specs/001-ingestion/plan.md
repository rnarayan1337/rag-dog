# 001 — Ingestion: Plan

## Module

`ragdog/core/ingest.py`

## Flow

```
ingest_file(path)
  ├─ doc_hash = hash_file(path)
  ├─ if already_ingested(doc_hash): return 0
  ├─ pages  = read_document(path)
  ├─ chunks = chunk_pages(pages)
  └─ return upsert_chunks(chunks, doc_hash, path)
```

## Functions

| Function | Signature | Notes |
|---|---|---|
| `hash_file` | `(path: str) -> str` | SHA-256, read in 1 MB blocks |
| `get_collection` | `() -> Collection` | Persistent client, cosine distance |
| `already_ingested` | `(doc_hash: str) -> bool` | `collection.get(where={"doc_hash": h}, limit=1)` |
| `read_document` | `(path: str) -> list[tuple[int, str]]` | One reader per file type; all return `(page, text)` |
| `chunk_pages` | `(pages) -> list[tuple[int, int, str]]` | Returns `(page, chunk_index, text)`; recursive split per page |
| `upsert_chunks` | `(chunks, doc_hash: str, path: str) -> int` | Builds ids + metadata; returns count stored |
| `ingest_file` | `(path: str) -> int` | Orchestrator; `0` if duplicate |

## Settings (`ragdog/core/config.py`)

| Setting | Value |
|---|---|
| `DB_DIR` | `.ragdog_db` |
| `COLLECTION` | `docs` |
| `CHUNK_SIZE` | 800 characters |
| `CHUNK_OVERLAP` | 150 characters |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` |
| `SUPPORTED_EXTENSIONS` | `.pdf`, `.md`, `.txt` |

## Libraries

- `hashlib` (stdlib) — hashing
- `pypdf` — `PdfReader(path).pages[i].extract_text()`
- `chromadb` — `PersistentClient`; cosine is set through collection metadata or
  configuration depending on the Chroma version — check the installed version's docs.

## Chunking approach

Recursive split, written by hand (no LangChain):
1. Try to split on paragraphs (`\n\n`).
2. Any piece still longer than `CHUNK_SIZE` → split on sentences (`. `).
3. Still too long → split on spaces.
4. Pack the pieces into chunks up to `CHUNK_SIZE`, carrying the last `CHUNK_OVERLAP`
   characters into the next chunk.

`chunk_index` counts across the whole document, not per page.

## Testing

`pytest`, with a temporary ChromaDB directory per test.

- `hash_file`: same bytes → same hash; different bytes → different hash
- `chunk_pages`: sizes within limit; overlap present; page numbers preserved
- `ingest_file`: second call returns `0`; renamed copy is a duplicate
