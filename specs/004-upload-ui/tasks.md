# 004 — Upload UI: Tasks

Tick each task when done. Keep this file current in the same PR as the code.

## Setup

- [x] T1 Create branch `feature/004-upload-ui`
- [x] T2 Review and approve `spec.md` / `plan.md`

## Core

- [x] T3 `file_location` argument on `ingest_file` / `upsert_chunks` + tests
- [x] T4 `DocumentInfo` and `list_documents()` + tests
- [x] T5 Rule 1 test: nothing in `ragdog/core` imports `streamlit` or `fastapi`

## UI

- [x] T6 `app.py` skeleton: `load_dotenv`, page config, cached collection, `main()` guard,
      missing-key warning + first `AppTest` (page loads; warning when no key)
- [x] T7 Upload flow (`ingest_upload`): temp file under the original name, duplicate check,
      "added / already uploaded / no text found / couldn't read", handled uploads remembered
      across reruns + `AppTest` tests
- [x] T8 Document list and "Search in" choice
- [x] T9 `sources()` formatting (collapse whitespace, drop duplicates) + tests
- [x] T10 Chat: history in `st.session_state`, `retrieve` → `generate_answer` with a spinner,
      `GenerationError` shown as an error + `AppTest` tests with a fake `generate_answer`

## Verify

- [x] T11 Manual run in the browser pane (ask the owner first — costs money): upload the
      handbook, upload it again, upload an empty file, ask 3 questions; record what happened

### Browser run (T11)

`uv run streamlit run app.py`, used through the built-in browser pane, 2026-11-24, on a fresh `.ragdog_db` (the old one
moved aside). One upload of three files: `acme-handbook.pdf`, `empty.txt` (0 bytes), and
`renamed-handbook.pdf` (same bytes, other name).

| Step | Expected | Seen |
|---|---|---|
| Empty database | "No documents yet." | ✅ |
| `acme-handbook.pdf` | added 4 chunks | ✅ "added 4 chunks", listed as "acme-handbook.pdf · 4 chunks" |
| `empty.txt` | no text found | ✅ "no text found (is it a scanned PDF?)" |
| `renamed-handbook.pdf` | already uploaded | ✅ "already uploaded", nothing stored |
| Reruns while asking | no re-ingest | ✅ status lines unchanged, still 4 chunks |
| Stored metadata | original name, no temp path | ✅ all 4 chunks: `filename` and `file_location` = `acme-handbook.pdf` |

| Question | Search in | Answer | Sources |
|---|---|---|---|
| What does error E2210 mean? | All documents | ✅ Jar not seated, plus the fix · repeats its first sentence | 2 × p.3 |
| How much does the XJ-4417 cost? | acme-handbook.pdf | ✅ $59, Mini Blender (trap handled); `$` shown as text, not maths | 1 × p.2 |
| What is Acme's annual revenue? | acme-handbook.pdf | ✅ "The documents don't contain…" | none (no Sources list) |

No server errors. 3 questions at about 2,500 input tokens each ≈ $0.001. The UI doesn't show
token counts, so the exact numbers weren't recorded.

- [ ] T12 Walk through the acceptance criteria and record the evidence

## Docs

- [ ] T13 Draft decision 016 (UI: Streamlit page, temp-file uploads, `file_location` holds the
      original filename, no streaming) — approve the text before adding it
- [ ] T14 `docs/challenges.md`: close the "duplicate vs no text" item; add anything new
- [ ] T15 Mark 004 done in `spec.md` and `docs/roadmap.md`
