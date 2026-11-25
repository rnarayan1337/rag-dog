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

- [x] T12 Walk through the acceptance criteria and record the evidence

### Acceptance criteria (T12)

Checked 2026-11-24. 100 tests pass (`make test`).

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 1 | `make run` opens the page | `make run` is `uv run streamlit run app.py`; the browser pane ran the same command (plus `--server.headless`, `--server.port`) and showed the uploader, document list and chat box | ✅ |
| 2 | Handbook upload shows chunks added and is listed; survives a restart | T11: "added 4 chunks", "acme-handbook.pdf · 4 chunks". A second server process (the no-key check below) listed it on its first page load. `test_stored_documents_listed_on_first_visit` | ✅ |
| 3 | Same file again, even renamed → "already uploaded", nothing stored | T11: `renamed-handbook.pdf` → "already uploaded", still 4 chunks. `test_ingest_upload_tells_duplicate_from_no_text`, `test_upload_shows_one_status_per_file` | ✅ |
| 4 | No text → "no text found"; told apart from a duplicate | T11: `empty.txt` → "no text found". Same two tests as #3 | ✅ |
| 5 | `filename` and `file_location` are the original name, never a temp path | T11: read all 4 stored chunks; both fields `acme-handbook.pdf`. `test_ingest_upload_stores_original_name_not_temp_path`, `test_ingest_file_records_file_location_not_temp_path` | ✅ |
| 6 | Answer plus Sources naming a stored file and page; identical quotes once | T11: E2210 (2 × p.3), XJ-4417 (p.2). `test_question_gets_answer_and_sources` (cites one chunk twice, shows one line), `test_sources_drops_repeats_keeps_order` | ✅ |
| 7 | "Search in" one document → sources only from it | `test_search_in_one_document` (two documents stored, only `hash-b` chunks reach `generate_answer`), `test_search_all_documents_by_default`. T11 had one document, so the browser run couldn't show the filtering | ✅ (tests) |
| 8 | Missing key → warning, no crash; `GenerationError` shown, app keeps working | Started a second server with `ANTHROPIC_API_KEY=` (empty, so `.env` doesn't fill it): warning shown, chat box `disabled`, no server errors. `test_missing_key_warns_and_disables_chat`, `test_generation_error_shown_and_app_keeps_working` | ✅ |
| 9 | No Streamlit in `ragdog/core` (Rule 1); only `generate.py` imports `anthropic` (Rule 7) | `test_core_imports_no_ui_or_http_framework` (shown to catch a planted import in T5), `test_only_generate_imports_a_provider_sdk` (now also scans `app.py`) | ✅ |
| 10 | Automated tests are free; the real run done once with the owner's OK | Every chat test patches `generate_answer` with `FakeGenerate`; the others never ask a question. T11 was approved and cost about $0.001 | ✅ |

## Docs

- [x] T13 Draft decision 016 (UI: Streamlit page, temp-file uploads, `file_location` holds the
      original filename, no streaming) — approve the text before adding it
- [x] T14 `docs/challenges.md`: close the "duplicate vs no text" item; add anything new
- [ ] T15 Mark 004 done in `spec.md` and `docs/roadmap.md`
