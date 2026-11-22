# Roadmap

Each item becomes a folder under `specs/` (spec.md, plan.md, tasks.md) **when work on it starts** —
not before. Update status here as items move.

Status: ⬜ not started · 🟨 in progress · ✅ done · 🅿️ parked

## v1 — happy path

| # | Item | What it delivers | Status |
|---|------|------------------|--------|
| 000 | Setup | Repo, SSH + signed commits, uv project, `.env` | ✅ |
| 001 | Ingestion | Upload → hash/dedup → read pages → chunk → store in ChromaDB | 🟨 |
| 002 | Retrieval | Embed the question, return top-k chunks; check them by eye | ⬜ |
| 003 | Generation | Prompt + chunks → Claude → cited answer | ⬜ |
| 004 | Upload UI | Streamlit page to upload files and chat | ⬜ |
| 005 | Packaging | Docker image, volume mount for the DB, API key at run time | ⬜ |

**v1 is done when:** someone can `docker run` rag-dog, upload a PDF, and get a cited answer.

## After v1

| # | Item | What it delivers | Status |
|---|------|------------------|--------|
| 006 | Evaluation | Golden set; score retrieval (recall@k) and answers (faithfulness) separately | 🅿️ |
| 007 | Guardrails | Weak-match check before the LLM call; citation enforcement | 🅿️ |
| 008 | Re-ranking | Cross-encoder re-ranker; fusion (RRF) — needs a deeper discussion first | 🅿️ |
| 009 | API | FastAPI wrapper around `core/` (`POST /documents`, `POST /ask`) | 🅿️ |
| 010 | Re-embedding | Blue/green migration to a new embedding model | 🅿️ |

## Ideas (not committed)

- Pluggable LLM provider (Claude ↔ Ollama via config)
- Cross-page chunking with a page-offset map
- Replace old chunks when a document with the same filename is re-uploaded
- Hybrid search (keyword + vector)
