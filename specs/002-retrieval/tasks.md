# 002 — Retrieval: Tasks

Tick each task when done. Keep this file current in the same PR as the code.

## Setup

- [x] T1 Create branch `feature/002-retrieval`
- [x] T2 Review and approve `spec.md` / `plan.md`
- [x] T3 Add `TOP_K = 5` to `ragdog/core/config.py`

## Functions

- [x] T4 `RetrievedChunk` dataclass
- [x] T5 `to_chunks` (unpack Chroma's nested query result) + test
- [x] T6 `retrieve` + tests (shape, order, `k`, empty collection, blank question)
- [x] T7 `doc_hash` filter + test

## Verify

- [x] T8 `scripts/check_retrieval.py` with the starter questions
- [x] T9 Run it on the Acme handbook; record hits and misses (expected page in top 3?)
- [x] T10 Walk through every acceptance criterion in `spec.md`

### Check results (T9)

`acme-handbook.pdf` (4 pages → 4 chunks), all-MiniLM-L6-v2, cosine distance, run 2026-11-22.

| Question | Expected | Rank | Distance (expected) | Next best |
|---|---|---|---|---|
| What does error E2210 mean? | p3 | 1 | 0.621 | 0.825 (p4) |
| What does error E4012 mean? | p3 | 1 | 0.626 | 0.816 (p4) |
| How much does the XJ-4417 cost? | p2 | 1 | 0.616 | 0.871 (p1) |
| How much is the Turbo Blender? | p2 | 1 | 0.400 | 0.621 (p4) |
| How long do I have to return an opened product? | p1 | 1 | 0.564 | 0.672 (p4) |
| How long are blender motors covered by warranty? | p4 | 1 | 0.271 | 0.558 (p1) |
| Who founded Acme? | p1 | 1 | 0.478 | 0.665 (p4) |
| How do I fix bitter coffee? | p3 | 1 | 0.615 | 0.753 (p2) |

**8/8 hits, all at rank 1. No misses.**

Notes:
- Weak test: with only 4 chunks, "top 3" is nearly guaranteed. The useful signal is the gap —
  the right page won by 0.11–0.29 every time.
- Near-identical codes (`E2210`/`E4012`, `XJ-4417`/`XJ-4471`) share a page, so retrieval only
  had to find the page. Telling them apart is the LLM's job in 003.
- Right pages scored 0.27–0.63; wrong pages 0.56–1.01. The ranges overlap, so one small
  document isn't enough to pick a weak-match cutoff (roadmap 007).
- A larger document with similar-sounding sections is needed for a real test (roadmap 006).

### Acceptance results (T10)

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 1 | ≤ `k` results, closest first, every field | `test_retrieve_returns_closest_first_with_all_fields`, `test_retrieve_defaults_to_top_k`, `test_to_chunks_maps_fields_in_order` | ✅ |
| 2 | Question embedded with the ingestion model | `retrieve` opens the collection via `get_collection()` (`test_retrieve_without_collection_uses_get_collection`; model pinned per `test_get_collection_uses_cosine_and_configured_model`). Manual: embedding the question directly with `ONNXMiniLM_L6_V2` and querying by vector gave identical pages and distances to `retrieve` | ✅ |
| 3 | `k` > stored returns all, no error | `test_retrieve_k_larger_than_collection_returns_all` | ✅ |
| 4 | Empty collection returns `[]` | `test_retrieve_empty_collection_returns_nothing`, `test_to_chunks_no_hits_is_empty` | ✅ |
| 5 | Blank question rejected clearly | `test_retrieve_rejects_blank_question` (`""`, spaces, newline) | ✅ |
| 6 | `doc_hash` filter returns only that document | `test_retrieve_doc_hash_filter_searches_one_document`, `test_retrieve_unknown_doc_hash_returns_nothing` | ✅ |
| 7 | Handbook: expected page in top 3 | Check results above: 8/8, all at rank 1 (weak test — 4 chunks) | ✅ |

Constraints: `ragdog/core/` has no UI/HTTP imports ✅; no provider SDK imports (Rule 7) ✅;
retrieval opens the collection only through `get_collection()` ✅.

## Close out

- [x] T11 Add decision 014 (retrieval: top-k = 5, distances returned, no cutoff in v1)
      to `docs/decisions.md`
- [ ] T12 Mark 002 ✅ in `docs/roadmap.md`; add `scripts/` to the AGENTS.md layout
- [ ] T13 Open PR, review, merge
