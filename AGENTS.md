# AGENTS.md

Instructions for AI coding agents (and humans) working in this repo.

## Project

**rag-dog** — a RAG demo. Users upload documents and ask questions; Claude answers from the
retrieved chunks, with citations.

- What we're building and when: `docs/roadmap.md`
- Why things are the way they are: `docs/decisions.md`
- Current feature: `specs/<NNN-name>/` (`spec.md`, `plan.md`, `tasks.md`)

## How to work with the owner

This is a learning project. The owner designs and writes the code so he can explain every line.

- Explain, review, and suggest. Do **not** write large chunks of implementation unless asked.
- When asked to write code, keep it small and explain the choices.
- Ask before changing anything listed in `docs/decisions.md`.

## Commands

```bash
uv sync                          # install dependencies from uv.lock
uv add <package>                 # add a dependency (never pip install)
uv add --dev <package>           # add a dev dependency (e.g. pytest)
uv run pytest                    # run tests
uv run streamlit run app.py      # run the UI
```

The `Makefile` wraps these. Run `make` to list the targets:

```bash
make install                     # uv sync
make test                        # uv run pytest
make run                         # uv run streamlit run app.py
make clean                       # remove __pycache__ and .pytest_cache (keeps .ragdog_db)
```

## Layout

```
ragdog/core/     # ingestion, retrieval, generation — pure Python, no UI or HTTP
app.py           # Streamlit UI (calls ragdog.core directly)
tests/           # pytest tests
docs/            # roadmap.md, decisions.md
specs/           # one folder per roadmap item
assets/          # logo, banner, favicon
```

## Rules (do not break these)

1. `ragdog/core/` never imports Streamlit, FastAPI, or any UI/HTTP code.
2. Never commit `.env`, API keys, or `.ragdog_db/`.
3. Use `uv`, not `pip`.
4. Documents and queries must be embedded with the **same** model.
   Store `embedding_model` in every chunk's metadata.
5. No LangChain / LlamaIndex in v1 (see decision 001).
6. v1 is the happy path. Parked items (eval, guardrails, re-ranking, API, re-embedding)
   live in `docs/roadmap.md` — don't build them early.

## Keeping docs current

- A change that alters behavior or a decision updates the relevant `spec.md`, `tasks.md`,
  and `docs/decisions.md` **in the same PR**. A PR without its doc updates isn't done.
- Tick tasks in `tasks.md` as they're completed.
- Update status in `docs/roadmap.md` when an item starts or finishes.
- Rules in this file change only deliberately, never as a side effect of a feature.

## Conventions

- Type hints on all functions; short docstrings.
- Small functions that do one thing.
- One branch per spec (e.g. `feature/001-ingestion`), merged via PR.
- Commits are signed.
