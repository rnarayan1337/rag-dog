# 002 — Retrieval: Tasks

Tick each task when done. Keep this file current in the same PR as the code.

## Setup

- [x] T1 Create branch `feature/002-retrieval`
- [x] T2 Review and approve `spec.md` / `plan.md`
- [x] T3 Add `TOP_K = 5` to `ragdog/core/config.py`

## Functions

- [x] T4 `RetrievedChunk` dataclass
- [x] T5 `to_chunks` (unpack Chroma's nested query result) + test
- [ ] T6 `retrieve` + tests (shape, order, `k`, empty collection, blank question)
- [ ] T7 `doc_hash` filter + test

## Verify

- [ ] T8 `scripts/check_retrieval.py` with the starter questions
- [ ] T9 Run it on the Acme handbook; record hits and misses (expected page in top 3?)
- [ ] T10 Walk through every acceptance criterion in `spec.md`

## Close out

- [ ] T11 Add decision 014 (retrieval: top-k = 5, distances returned, no cutoff in v1)
      to `docs/decisions.md`
- [ ] T12 Mark 002 ✅ in `docs/roadmap.md`; add `scripts/` to the AGENTS.md layout
- [ ] T13 Open PR, review, merge
