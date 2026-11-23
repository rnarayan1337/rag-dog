# 001 — Ingestion: Tasks

Tick each task when done. Keep this file current in the same PR as the code.

## Setup

- [x] T1 Create branch `feature/001-ingestion`
- [x] T2 Add pytest: `uv add --dev pytest`
- [x] T3 Create `ragdog/core/config.py` with the settings from `plan.md`

## Functions

- [x] T4 `hash_file` + test (same bytes → same hash; streams in blocks)
- [x] T5 `get_collection` (persistent, cosine)
- [x] T6 `already_ingested` + test
- [x] T7 `read_document` for `.txt` / `.md` + test
- [x] T8 `read_document` for `.pdf` (page numbers) + test with a small sample PDF
- [ ] T9 `chunk_pages` (recursive split + overlap) + tests
- [ ] T10 `upsert_chunks` (ids + metadata) + test
- [ ] T11 `ingest_file` orchestrator + dedup tests (same file, renamed copy)

## Verify

- [ ] T12 Ingest a real PDF; print a few stored chunks and their metadata; check by eye
- [ ] T13 Restart and confirm chunks are still there
- [ ] T14 Walk through every acceptance criterion in `spec.md`

## Close out

- [ ] T15 Update `docs/decisions.md` if anything changed
- [ ] T16 Mark 001 ✅ in `docs/roadmap.md`
- [ ] T17 Open PR, review, merge
