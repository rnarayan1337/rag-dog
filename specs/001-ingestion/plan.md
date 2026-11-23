# 001 — Ingestion: Plan

## Module

`ragdog/core/ingest.py`

## Flow

```
ingest_file(path, collection=None)
  ├─ if collection is None: collection = get_collection()
  ├─ doc_hash = hash_file(path)
  ├─ if already_ingested(collection, doc_hash): return 0
  ├─ pages  = read_document(path)
  ├─ chunks = chunk_pages(pages)
  └─ return upsert_chunks(collection, chunks, doc_hash, path)
```

## Functions

| Function | Signature | Notes |
|---|---|---|
| `hash_file` | `(path: str) -> str` | SHA-256, read in 1 MB blocks |
| `get_collection` | `(db_dir: str = DB_DIR) -> Collection` | Persistent client, cosine distance, `ONNXMiniLM_L6_V2` embeddings; `db_dir` lets tests use a temp dir |
| `already_ingested` | `(collection: Collection, doc_hash: str) -> bool` | `collection.get(where={"doc_hash": h}, limit=1, include=[])`; caller passes the collection so it is opened once |
| `read_document` | `(path: str) -> list[tuple[int, str]]` | Checks the extension (`ValueError` if unsupported), then calls the reader for that type; all return `(page, text)` |
| `read_text` | `(path: str) -> list[tuple[int, str]]` | `.txt` / `.md`: UTF-8 (bad bytes replaced), one page `1` |
| `read_pdf` | `(path: str) -> list[tuple[int, str]]` | One pair per page, numbered from 1; text NFKC-normalised (ligatures like `ﬁ` → `fi`) |
| `split_text` | `(text, size, separators=SEPARATORS) -> list[str]` | Recursive split; separators stay attached so `"".join(pieces) == text`; hard cut if no separator left |
| `overlap_tail` | `(chunk, overlap) -> str` | Last `overlap` chars, trimmed to start at a word |
| `pack_pieces` | `(pieces, size, overlap) -> list[str]` | Packs pieces up to `size`; each new chunk starts with the previous tail; drops blank chunks |
| `chunk_pages` | `(pages, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP) -> list[tuple[int, int, str]]` | Returns `(page, chunk_index, text)`; split + pack per page |
| `upsert_chunks` | `(collection, chunks, doc_hash: str, path: str, batch_size=UPSERT_BATCH_SIZE) -> int` | Builds ids + metadata; `upsert` in batches of 500 (re-running replaces, never duplicates); returns count stored |
| `ingest_file` | `(path: str, collection: Collection \| None = None) -> int` | Orchestrator; opens the default collection if none given (tests pass a fake one); `0` if duplicate — also `0` if the file has no text |

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
- `pypdf` — `PdfReader(path).pages[i].extract_text()`; may return ligature characters, so normalise with `unicodedata.normalize("NFKC", ...)`
- Test fixture: `tests/fixtures/sample-3-pages.pdf` (known text on each page, made with headless Chrome)
- `chromadb` (1.5.9) — `PersistentClient`; cosine is set with
  `configuration={"hnsw": {"space": "cosine"}}` (reopening ignores a different value).

## Chunking approach

Recursive split, written by hand (no LangChain):
1. Try to split on paragraphs (`\n\n`).
2. Any piece still longer than `CHUNK_SIZE` → split on sentences (`. `).
3. Still too long → split on spaces.
4. Pack the pieces into chunks up to `CHUNK_SIZE`, carrying the last `CHUNK_OVERLAP`
   characters into the next chunk.

`chunk_index` counts across the whole document, not per page.

## Testing

`pytest`, with a temporary ChromaDB directory per test. Tests that store text use a fake
embedding function (`tests/conftest.py`), so they need no model download.

- `hash_file`: same bytes → same hash; different bytes → different hash
- `chunk_pages`: sizes within limit; overlap present; page numbers preserved
- `ingest_file`: second call returns `0`; renamed copy is a duplicate
