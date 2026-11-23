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
- [x] T9 `chunk_pages` (recursive split + overlap) + tests
- [x] T10 `upsert_chunks` (ids + metadata) + test
- [x] T11 `ingest_file` orchestrator + dedup tests (same file, renamed copy)

## Verify

- [x] T12 Ingest a real PDF; print a few stored chunks and their metadata; check by eye
- [x] T13 Restart and confirm chunks are still there
- [x] T14 Walk through every acceptance criterion in `spec.md`

### Acceptance results (T14)

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 1 | ≥ 1 chunk with all metadata fields | `test_upsert_chunks_stores_ids_text_and_metadata`; T12 real PDF: 4 chunks, all 6 fields | ✅ |
| 2 | Same file twice → stored once, second call `0` | `test_ingest_file_twice_stores_once`; T12 second run returned `0` | ✅ |
| 3 | Renamed copy is a duplicate | `test_ingest_file_renamed_copy_is_a_duplicate` | ✅ |
| 4 | Chunks ≤ size; neighbours overlap | `test_chunk_pages_size_limit_and_overlap`, `test_split_text_*` | ✅ |
| 5 | PDF chunks carry the right page | `test_ingest_file_pdf_chunks_carry_page_numbers`, `test_read_document_pdf_keeps_page_numbers`; T12 pages 1–4 | ✅ |
| 6 | Chunks survive a restart | `test_get_collection_persists_across_clients`; T13 read back in a fresh process | ✅ |
| 7 | Unsupported types rejected clearly | `test_read_document_rejects_unsupported_types`, `test_ingest_file_unsupported_type_stores_nothing` | ✅ |
| 8 | ≥ 100 MB file hashes without loading it all | Manual: 120 MB file, peak memory 2 MB with `hash_file` vs 120 MB reading it whole; same hash | ✅ |

Constraints: `ragdog/core/` has no UI/HTTP imports ✅. Chunk size vs ~256-token limit: prose
chunks 126–181 tokens ✅; code-heavy text can reach ~340 tokens at 800 chars and be truncated
(known trade-off, decision 003).

## Close out

- [x] T15 Update `docs/decisions.md` if anything changed
- [ ] T16 Mark 001 ✅ in `docs/roadmap.md`
- [ ] T17 Open PR, review, merge
