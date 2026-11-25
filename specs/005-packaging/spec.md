# 005 — Packaging: Spec

**Status:** Draft · **Roadmap:** 005 · **Decisions:** 002, 003, 010, 012, 016

## Goal

A Docker image of rag-dog, so someone can build it, `docker run` it with their own API key,
upload a PDF and get a cited answer. This is the last v1 item: when it's done, the roadmap's
"v1 is done when" line is true.

## User story

As someone trying rag-dog, I clone the repo, build the image, and start it with my Anthropic
key. I open `http://localhost:8501`, upload a document and ask a question. When I stop and
start the container again, my documents are still there.

## In scope

- A `Dockerfile`: `python:3.12-slim`, dependencies installed with `uv` from `uv.lock`
  (no dev dependencies), the embedding model downloaded during the build, the app running as a
  non-root user on port 8501.
- A `.dockerignore`, so `.env`, `.ragdog_db/`, `.venv/`, `.git/`, `.claude/`, `tests/` and
  caches never reach the image.
- The database on a named volume mounted at `/app/.ragdog_db`.
- The API key passed at run time, with `--env-file .env` or `-e ANTHROPIC_API_KEY` (no value
  on the command line). Never in the image.
- Usage data switched off:
  - Streamlit: a committed `.streamlit/config.toml` with `gatherUsageStats = false`. It also
    sets `toolbarMode = "viewer"` to hide the "Deploy" button. Applies to `make run` too.
  - Chroma: `get_collection` passes `Settings(anonymized_telemetry=False)`.
- `make docker-build` and `make docker-run`.
- A short **Run with Docker** section in `README.md`.

## Out of scope (v1)

- Publishing the image to a registry (e.g. GHCR)
- Multi-platform images (the build is for the machine it runs on; arm64 here)
- A container health check, docker compose, or a reverse proxy / HTTPS
- Hosting rag-dog for other people (decision 012: their keys would pass through our server)
- A full README rewrite

## Behaviour

| Situation | What happens |
|---|---|
| `make docker-build` | Builds the image `rag-dog` from `uv.lock`; the embedding model is inside it |
| `make docker-run` with `.env` present | App at `http://localhost:8501`, database on the `ragdog-data` volume |
| Container removed and started again with the same volume | Same documents listed |
| Started without a key | The 004 warning; chat box disabled; no crash |
| First upload in a new container | No model download; embedding runs offline |

## Acceptance criteria

1. `make docker-build` builds the image from a clean checkout, using the locked versions. The
   image size is recorded.
2. The v1 goal: with a key and a volume, `make docker-run` serves the page; uploading the Acme
   handbook and asking a question gives a cited answer with the right page.
3. Documents survive removing the container and starting a new one on the same volume.
4. The image holds no `.env`, no database files, no `tests/` and no `.git/`, and the app runs
   as a non-root user.
5. The embedding model is in the image: the first upload in a new container doesn't download
   it.
6. Started without a key, the page shows the warning and doesn't crash.
7. Usage data is off: the Chroma setting is checked by a test, and the Streamlit setting is
   checked by a test reading `.streamlit/config.toml`.
8. The key never appears in the image: not in its files, its environment (`docker inspect`) or
   its build history (`docker history`).
9. Local development is unchanged: `make test` and `make run` still work.
10. `README.md` says how to build and run the image in a few commands.

## Constraints

- `uv`, not `pip`, inside the image too (Rule 3).
- The key comes from the environment only (Rule 8, decision 012).
- `ragdog/core/` stays free of UI and HTTP code (Rule 1). The telemetry setting is Chroma
  configuration, not UI.
- Building needs Docker on the Mac, which the owner installs. Nothing is pushed or published.
- The one real question in the container costs about $0.0003: ask the owner first.
