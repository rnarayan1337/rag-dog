# 005 — Packaging: Tasks

Tick each task when done. Keep this file current in the same PR as the code.

## Setup

- [x] T1 Create branch `feature/005-packaging`
- [x] T2 Review and approve `spec.md` / `plan.md`

## Usage data off

- [x] T3 Chroma: `get_collection` passes `Settings(anonymized_telemetry=False)` + test
- [x] T4 Streamlit: `.streamlit/config.toml` (`gatherUsageStats = false`,
      `toolbarMode = "viewer"`) + test

## Image

- [ ] T5 `.dockerignore`
- [ ] T6 `Dockerfile`
- [ ] T7 `make docker-build` / `make docker-run`
- [ ] T8 Build it: record the image size; check contents, non-root user, model in the image,
      and that no key is in its files, environment or history

## Verify

- [ ] T9 Run it in the browser pane: upload the handbook, ask one question (ask the owner
      first — costs money), restart on the same volume, start without a key; record results
- [ ] T10 Walk through the acceptance criteria and record the evidence

## Docs

- [ ] T11 `README.md`: "Run with Docker" section
- [ ] T12 Draft decision 017 (Docker image, model baked in, named volume, telemetry off) and a
      dated note on 012 about `-e ANTHROPIC_API_KEY` without a value — approve the text first
- [ ] T13 `docs/challenges.md`: add anything new
- [ ] T14 Mark 005 done in `spec.md` and `docs/roadmap.md` (v1 done)
