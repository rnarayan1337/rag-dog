# 004 — Upload UI: Spec

**Status:** Done · **Roadmap:** 004 · **Decisions:** 005, 006, 007, 008, 012, 015, 016

## Goal

A Streamlit page where someone uploads documents and asks questions about them, and gets a
short answer with its sources (file, page and the quoted passage). This is the first time the
whole loop (001 → 002 → 003) runs from a browser.

## User story

As a user, I open rag-dog in my browser, drop in one or more PDF, Markdown or text files, and
see them listed. I type a question and get a short answer, with a list of the passages it was
taken from, each with the file name and page.

## In scope

- `app.py` at the repo root: one page, which calls `ragdog/core` directly (decision 007).
- **Sidebar:**
  - A file uploader for `.pdf`, `.md` and `.txt`, several files at once.
  - One status line per uploaded file: chunks added, "already uploaded", or "no text found".
  - The list of stored documents (filename and chunk count).
  - A "Search in" choice: all documents (the default) or one document.
- **Main area:** a chat. Each answer is followed by its **Sources**: `filename · p.N` and the
  quoted text, with identical quotes shown once.
- Chat history is kept for the browser session only, for display. Each question is still
  answered on its own (no follow-ups, as in 003).
- Two small additions to `core`:
  - `list_documents()`: one entry per stored document, read from chunk metadata.
  - An optional `file_location` argument on `ingest_file`, so an upload records its original
    filename instead of the deleted temp path.
- `app.py` calls `load_dotenv()`. It's an entry point, like the check scripts (Rule 8).
- `make run` (`uv run streamlit run app.py`) starts it.

## Out of scope (v1)

- Deleting or replacing documents (roadmap idea; decision 006 "open")
- Follow-up questions that use earlier answers
- Streaming answers (they're short; see decision 015, and Rule 7's single `generate_answer`)
- An API key field in the UI (roadmap idea; decision 012)
- Keeping copies of uploaded files
- Docker (005)
- Fixing the repeated cited sentence in answers (open in `docs/challenges.md`)

## Behaviour

| Situation | What the user sees |
|---|---|
| New file with text | "acme-handbook.pdf: added 4 chunks", and it appears in the document list |
| Same content uploaded again (any filename) | "acme-handbook.pdf: already uploaded" — nothing stored |
| File with no extractable text (e.g. a scanned PDF) | "scan.pdf: no text found (is it a scanned PDF?)" — nothing stored |
| File that can't be read (e.g. a broken PDF) | "broken.pdf: couldn't read it" plus the error, and the other files still upload |
| Question, documents stored | The answer, then its Sources |
| Question, no documents stored | 003's fixed "no documents" answer, with no API call |
| `ANTHROPIC_API_KEY` not set | A warning at the top of the page; the chat box is disabled |
| `GenerationError` (refusal, cut-off, API error) | A red error in the chat in place of the answer; the app keeps running |

Unsupported file types never reach `core`: the uploader only accepts `.pdf`, `.md` and `.txt`.

## Acceptance criteria

1. `make run` opens the page with the uploader, the document list and the chat box.
2. Uploading the Acme handbook shows the chunks added and lists it with its chunk count. The
   list is still there after a restart (it's read from the database).
3. Uploading the same file again, even renamed, says "already uploaded" and stores nothing.
4. A file with no text says "no text found" and stores nothing. "Already uploaded" and "no
   text found" are told apart (this closes the 🔴 item in `docs/challenges.md`).
5. Stored chunks from an upload have the original filename in `filename` and
   `file_location`, never a temp path.
6. A question gets an answer and a Sources list. Each source names a stored file and page,
   and identical quotes appear once.
7. "Search in" limited to one document only returns sources from that document.
8. A missing key gives a warning instead of a crash, and a `GenerationError` is shown as an
   error message while the app keeps working.
9. `ragdog/core/` still has no Streamlit import (Rule 1), and only `generate.py` imports
   `anthropic` (Rule 7). Both are checked by tests.
10. Automated tests make no API calls and cost nothing. The real run in the browser (a few
    questions on the handbook) is done once, with the owner's OK.

## Constraints

- `ragdog/core/` never imports Streamlit (Rule 1).
- `app.py` never imports `anthropic`; it only calls `generate_answer` (Rule 7).
- The API key is never typed into, shown by, or saved from the UI (Rule 8, decision 012).
- Every real question asked through the UI costs money (about $0.0003 each): ask the owner
  before each run.
