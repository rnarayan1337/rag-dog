# 002 — Retrieval: Plan

## Module

`ragdog/core/retrieve.py`

## Flow

```
retrieve(question, k=TOP_K, doc_hash=None, collection=None)
  ├─ reject a blank question (ValueError)
  ├─ if collection is None: collection = get_collection()   # same model as ingestion
  ├─ result = collection.query(query_texts=[question], n_results=k,
  │                            where={"doc_hash": doc_hash} if doc_hash else None,
  │                            include=["documents", "metadatas", "distances"])
  └─ return to_chunks(result)                                # list[RetrievedChunk]
```

## Types and functions

| Name | Signature | Notes |
|---|---|---|
| `RetrievedChunk` | frozen `@dataclass` | Fields from the spec's result model |
| `retrieve` | `(question: str, k: int = TOP_K, doc_hash: str \| None = None, collection: Collection \| None = None) -> list[RetrievedChunk]` | Entry point used by 003 and the UI |
| `to_chunks` | `(result: QueryResult) -> list[RetrievedChunk]` | Unpacks Chroma's nested lists (one list per query; we send one) |

Why a dataclass rather than a dict: named fields (`chunk.page`) are checked by type hints and
editors, and 003 can't misspell a key.

## Settings (`ragdog/core/config.py`)

| Setting | Value |
|---|---|
| `TOP_K` | 5 |

## Chroma behaviour (checked on 1.5.9)

- `query` returns nested lists: `result["documents"][0]` holds the results for the first
  (only) question.
- `n_results` larger than the collection returns everything stored; an empty collection
  returns `[[]]`.
- With cosine space, `distance = 1 − cosine similarity` (range 0–2; lower is closer).
- `query_texts` is embedded by the collection's embedding function — the pinned
  all-MiniLM-L6-v2 from `get_collection()`.

## Check script

`scripts/check_retrieval.py` (new `scripts/` folder — not part of `ragdog/core/`):

- Takes a PDF path, ingests it (no-op if already stored), runs a fixed list of questions,
  and prints for each: the question, then the top 5 as `distance · page · first 80 chars`.
- Starter questions for the Acme handbook, each with the page that should win:

| Question | Expected page |
|---|---|
| What does error E2210 mean? | 3 |
| What does error E4012 mean? | 3 |
| How much does the XJ-4417 cost? | 2 |
| How much is the Turbo Blender? | 2 |
| How long do I have to return an opened product? | 1 |
| How long are blender motors covered by warranty? | 4 |
| Who founded Acme? | 1 |
| How do I fix bitter coffee? | 3 |

The near-identical codes (`XJ-4471` / `XJ-4417`, `E2210` / `E4012`) are there on purpose:
meaning-based search often confuses them.

## Testing

`pytest` with the fake embedding fixture (`tests/conftest.py`) for the mechanics:

- Result shape and order; at most `k` results
- `k` larger than the collection; empty collection; blank question
- `doc_hash` filter
- `retrieve` with no collection uses `get_collection()` (the pinned model)

Retrieval **quality** can't be tested with a fake model — that is what the check script and,
later, roadmap 006 are for.
