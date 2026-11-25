# 004 — Upload UI: Tasks

Tick each task when done. Keep this file current in the same PR as the code.

## Setup

- [x] T1 Create branch `feature/004-upload-ui`
- [x] T2 Review and approve `spec.md` / `plan.md`

## Core

- [x] T3 `file_location` argument on `ingest_file` / `upsert_chunks` + tests
- [ ] T4 `DocumentInfo` and `list_documents()` + tests
- [ ] T5 Rule 1 test: nothing in `ragdog/core` imports `streamlit` or `fastapi`

## UI

- [ ] T6 `app.py` skeleton: `load_dotenv`, page config, cached collection, `main()` guard,
      missing-key warning + first `AppTest` (page loads; warning when no key)
- [ ] T7 Upload flow (`ingest_upload`): temp file under the original name, duplicate check,
      "added / already uploaded / no text found / couldn't read", handled uploads remembered
      across reruns + `AppTest` tests
- [ ] T8 Document list and "Search in" choice
- [ ] T9 `sources()` formatting (collapse whitespace, drop duplicates) + tests
- [ ] T10 Chat: history in `st.session_state`, `retrieve` → `generate_answer` with a spinner,
      `GenerationError` shown as an error + `AppTest` tests with a fake `generate_answer`

## Verify

- [ ] T11 Manual run in the browser pane (ask the owner first — costs money): upload the
      handbook, upload it again, upload an empty file, ask 3 questions; record what happened
- [ ] T12 Walk through the acceptance criteria and record the evidence

## Docs

- [ ] T13 Draft decision 016 (UI: Streamlit page, temp-file uploads, `file_location` holds the
      original filename, no streaming) — approve the text before adding it
- [ ] T14 `docs/challenges.md`: close the "duplicate vs no text" item; add anything new
- [ ] T15 Mark 004 done in `spec.md` and `docs/roadmap.md`
