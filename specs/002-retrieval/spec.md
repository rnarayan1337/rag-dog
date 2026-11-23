# 002 — Retrieval: Spec

**Status:** Approved · **Roadmap:** 002 · **Decisions:** 002, 003, 014 (to add)

## Goal

Given a question, return the stored chunks most likely to answer it, with enough information
to cite them — so 003 (Generation) can hand them to the LLM.

## User story

As a user, I ask a question about my uploaded documents, and rag-dog finds the passages that
answer it, telling me which file and page each came from.

## In scope

- Embed the question with the **same** model as the documents (Rule 4)
- Return the top `k` chunks (default 5) across all documents
- Optional filter to a single document by `doc_hash`
- Each result carries its text, citation fields, and distance score
- A script that runs fixed questions against an ingested document and prints the results
  for checking by eye

## Out of scope (v1)

- Minimum-similarity cutoff / weak-match handling (roadmap 007, parked)
- Re-ranking and hybrid keyword search (roadmap 008, ideas)
- Scoring retrieval automatically (recall@k) — roadmap 006; the check script's questions
  are a seed for its golden set
- Any LLM call — that is 003

## Result model

Each result is one retrieved chunk:

| Field | Value |
|---|---|
| `text` | chunk text |
| `filename` | original filename (from metadata) |
| `page` | page number, 1-based |
| `chunk_index` | position in the document |
| `doc_hash` | which document it came from |
| `distance` | cosine distance from the question: `0` = same direction, higher = less similar |

Results are ordered by `distance`, smallest first.

## Acceptance criteria

1. A question returns at most `k` results, closest first, each with every field above.
2. The question is embedded with the collection's model (`all-MiniLM-L6-v2`) — the same one
   used at ingestion.
3. Asking for more results than are stored returns all stored chunks, not an error.
4. An empty collection returns an empty list, not an error.
5. A blank question is rejected with a clear error.
6. Filtering by `doc_hash` returns only chunks from that document.
7. On the Acme handbook, each check-script question has the chunk that answers it in the
   top 3 (judged by eye; misses are written down, not hidden).

## Constraints

- `ragdog/core/` has no UI or HTTP imports.
- No provider SDK imports in retrieval (Rule 7).
- Retrieval opens the collection through `get_collection()`, so it can never use a different
  embedding model from ingestion.
