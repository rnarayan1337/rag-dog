# 004 — Upload UI: Plan

## Files

| File | Change |
|---|---|
| `ragdog/core/ingest.py` | `file_location` argument on `ingest_file` / `upsert_chunks`; `DocumentInfo` and `list_documents()` |
| `app.py` (new) | The Streamlit page |
| `tests/test_ingest.py` | Tests for the two `core` additions |
| `tests/test_app.py` (new) | `AppTest` tests with a fake collection and a fake `generate_answer` |
| `tests/test_rules.py` | Add Rule 1: nothing in `ragdog/core` imports `streamlit` (or `fastapi`) |

Streamlit 1.67.0 is already a dependency. Nothing new to install.

## Core additions

### `file_location` on `ingest_file`

```python
def ingest_file(path: str, collection: Collection | None = None,
                file_location: str | None = None) -> int:
```

`upsert_chunks` stores `file_location or path`. Scripts pass nothing and keep today's
behaviour. The UI writes each upload to a temp folder **under its original name** (so
`filename`, taken from `Path(path).name`, is already right) and passes
`file_location=<original filename>`, because the temp path is deleted straight after.

This changes what decision 005's `file_location` holds for uploads (a name, not a path on
disk). Nothing reads it today; decision 005 already says re-embedding doesn't need the
original files. Recorded in decision 016.

### `list_documents`

```python
@dataclass(frozen=True)
class DocumentInfo:
    filename: str
    doc_hash: str
    chunks: int

def list_documents(collection: Collection | None = None) -> list[DocumentInfo]:
```

One `collection.get(include=["metadatas"])`, then count chunks per `doc_hash`, sorted by
filename. Fetching all metadata is fine at demo size (hundreds of chunks). It lives in
`ingest.py` next to `already_ingested`, since both read what ingestion stored.

## `app.py`

```
load_dotenv()
st.set_page_config(page_title="rag-dog", page_icon="assets/favicon.png")

@st.cache_resource
def collection() -> Collection: return get_collection()     # open DB + load ONNX model once

def main():
    if no ANTHROPIC_API_KEY: st.warning(...)
    with st.sidebar:
        uploads = st.file_uploader(type=["pdf","md","txt"], accept_multiple_files=True)
        for upload in new uploads: st.write(ingest_upload(upload))
        documents = list_documents(collection())
        show the list; scope = st.selectbox("Search in", ["All documents", *filenames])
    show st.session_state.messages
    if question := st.chat_input(disabled=no key):
        chunks = retrieve(question, doc_hash=<scope>, collection=collection())
        with st.spinner(): answer = generate_answer(question, chunks)
        (GenerationError → store and show st.error instead)
        append question and answer to st.session_state.messages

if __name__ == "__main__":
    main()
```

Notes:

- **Why `main()` and the `__main__` guard.** `streamlit run` and `AppTest` both run the file as
  `__main__`, so the page still draws. A test can `import app` to unit-test the small helpers
  without drawing anything.
- **Why `st.cache_resource`.** Streamlit reruns the whole script on every click. Without the
  cache, each rerun would reopen Chroma and reload the embedding model. The cached collection
  is passed to `core` with `collection=`, which every function already accepts.
- **Rerun and the uploader.** The uploader keeps its files across reruns, so a file would be
  ingested again on every click. We remember the uploads already handled in
  `st.session_state` (by Streamlit's `file_id`) and only process new ones. Dedup in `core`
  would catch repeats anyway, but would print "already uploaded" every rerun.

### Upload flow (`ingest_upload`)

```
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / Path(upload.name).name        # original name, no folders
    path.write_bytes(upload.getvalue())
    if already_ingested(collection, hash_file(path)) → "already uploaded"
    try: added = ingest_file(path, collection, file_location=upload.name)
    except Exception as e → "couldn't read it: {e}"
    added == 0 → "no text found (is it a scanned PDF?)"
    else → "added {added} chunks"
```

Checking `already_ingested` first is what separates the two zeros: by the time
`ingest_file` returns 0, the document can't be a duplicate, so it had no text. No change to
`ingest_file`'s return value is needed. The temp folder is deleted when the `with` block ends.

Catching `Exception` here is the one broad catch in the app. It's at the boundary, it reports
the message, and it lets the other files in the same upload carry on.

### Sources (`sources`)

```python
def sources(citations: list[Citation]) -> list[str]:
    # "acme-handbook.pdf · p.3 — “Error E2210 means the jar is not seated correctly.”"
```

Whitespace in each quote is collapsed (PDF text has line breaks), and a line that's already
in the list is skipped, so a quote cited twice appears once. Order follows the answer.

### Chat history

`st.session_state.messages` holds dicts: `{"role": "user", "text": ...}` and
`{"role": "assistant", "text": ..., "sources": [...], "error": bool}`. Strings only, so
nothing heavy is kept per session. It's cleared when the browser tab is closed or reloaded.

### Search scope

The selectbox shows filenames; the chosen one maps back to its `doc_hash`, passed to
`retrieve(doc_hash=...)`. "All documents" passes `None`. If two stored documents share a
filename, the label adds the first 8 characters of the hash.

## Testing

**Unit (`tests/test_ingest.py`):**
- `file_location` is stored when given, and defaults to the path when not
- `list_documents`: empty collection → `[]`; two documents → one entry each, right counts,
  sorted by filename

**UI (`tests/test_app.py`, `streamlit.testing.v1.AppTest`):** the test monkeypatches
`ragdog.core.ingest.get_collection` to return the `fake_collection` fixture and
`ragdog.core.generate.generate_answer` to return a canned `Answer`, so no model download, no
network and no cost.
- The page loads with no exceptions
- Missing key → warning shown, chat input disabled
- Upload a `.txt` → "added N chunks" and it's listed; upload it again → "already uploaded"
- Upload an empty `.txt` → "no text found"
- Ask a question → user message, answer, and the deduplicated Sources
- `generate_answer` raises `GenerationError` → an error is shown and the app doesn't crash
- `sources()` directly: format, whitespace collapsed, duplicates dropped

**Rules (`tests/test_rules.py`):** add Rule 1 — no file under `ragdog/core` imports
`streamlit` or `fastapi`. The Rule 7 test already scans `app.py` once it exists.

**Manual, in the browser pane (asks the owner first — costs money):** `make run`, upload the
Acme handbook, upload it again, upload an empty file, ask 3 questions (one per scope setting,
plus the unanswerable one), check sources and pages by eye. About $0.001 in total.
