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

- [x] T5 `.dockerignore`
- [x] T6 `Dockerfile`
- [x] T7 `make docker-build` / `make docker-run`
- [x] T8 Build it: record the image size; check contents, non-root user, model in the image,
      and that no key is in its files, environment or history

### Image checks (T8)

Docker Desktop 29.9.3, arm64, 2026-11-24.

**Size: 2.66 GB → 1.58 GB.** The first build saved uv's download cache (689 MB, in
`/root/.cache/uv`) into the dependency layer, and kept the model's 83 MB download archive next
to the unpacked files. Fixed with a BuildKit cache mount on both `uv sync` steps and by deleting
`onnx.tar.gz` after unpacking (Chroma only checks the unpacked files). Rebuild: 38 s.

| Layer | Size |
|---|---|
| Locked dependencies (`.venv`) | 904 MB (largest: pyarrow 155 MB, kubernetes 119 MB, pandas 84 MB, onnxruntime 63 MB) |
| Debian base | 110 MB |
| Embedding model | 91 MB |
| Python | 45 MB |
| uv binary | 36 MB |

| Check | Result |
|---|---|
| `/app` contents | ✅ `.ragdog_db .streamlit .venv README.md app.py assets pyproject.toml ragdog uv.lock`; no `.env`, `tests`, `.git` |
| `/app/.ragdog_db` | ✅ empty, owned by `ragdog:ragdog` |
| User | ✅ `uid=1000(ragdog)`, not root |
| Model in image | ✅ the six unpacked files; embedding works with `--network none` (384 dimensions) |
| Dev dependencies | ✅ pytest not installed |
| Versions match local | ✅ Python 3.12.16, chromadb 1.5.9, streamlit 1.67.0, anthropic 2.12.0, pypdf 7.1.1 |
| Key in environment | ✅ none; env names are `PATH LANG GPG_KEY PYTHON_VERSION PYTHON_SHA256 UV_*` (`GPG_KEY` is the base image's Python signing key) |
| Key anywhere | ✅ the real key (read from `.env` on the Mac, never printed or sent into a container) matched 0 times in the exported image files (1,126 MB), `docker history --no-trunc` and `docker image inspect` |

### Browser run (T9)

2026-11-25, browser pane, new `ragdog-data` volume. Containers started from `.claude/launch.json`
(`make docker-run`, and `docker run` without `--env-file` for the no-key check).

| Check | Result |
|---|---|
| Page served | ✅ `make docker-run` → `http://localhost:8501`, "No documents yet." |
| Upload | ✅ `acme-handbook.pdf: added 4 chunks`; no model download in the container logs |
| Question (paid, approved) | ✅ "What does error E4012 mean on the blender, and what should I do?" → motor overheated; unplug, cool 20 minutes, less food. Both sources cite `acme-handbook.pdf · p.3`, which is the right page |
| Restart on the same volume | ✅ container removed by `--rm`, volume kept; new container lists `acme-handbook.pdf · 4 chunks` |
| No key | ✅ warning shown, chat box disabled, no crash |

Noticed:

- On start-up Streamlit prints an "External URL" with the machine's public IP, which it looks up
  from an outside service. `gatherUsageStats = false` doesn't cover it. Local runs do the same.
- The no-key warning says "Add it to `.env`". In Docker the fix is `--env-file .env` or
  `-e ANTHROPIC_API_KEY`, which the README section (T11) should say.

### Acceptance criteria (T10)

2026-11-25.

| # | Criterion | Evidence |
|---|---|---|
| 1 | Builds from a clean checkout, locked versions, size recorded | ✅ fresh `git clone` of the branch at `d57668c`, `docker build --no-cache`: 40 s, 1.58 GB; chromadb 1.5.9, streamlit 1.67.0, anthropic 2.12.0, pypdf 7.1.1. (`--no-cache` skips Docker's layer cache; uv's download cache mount is still reused, which only saves downloads) |
| 2 | v1 goal: upload the handbook, cited answer with the right page | ✅ T9: E4012 answer citing `acme-handbook.pdf · p.3` |
| 3 | Documents survive a new container on the same volume | ✅ T9: handbook still listed with 4 chunks |
| 4 | No `.env`, database files, `tests/`, `.git/`; non-root | ✅ T8 (and the clean build): `/app` holds only the app; `.ragdog_db` empty; `uid=1000(ragdog)` |
| 5 | Model in the image; first upload doesn't download it | ✅ T8: embedding works with `--network none`; T9: no download line on first upload |
| 6 | No key: warning, no crash | ✅ T9: warning shown, chat box disabled |
| 7 | Usage data off, checked by tests | ✅ `test_get_collection_turns_chroma_telemetry_off`, `test_streamlit_config_turns_usage_stats_off` |
| 8 | Key not in files, environment or history | ✅ T8: 0 matches in 1,126 MB of image files, `docker image inspect`, `docker history --no-trunc` |
| 9 | Local development unchanged | ✅ `make test`: 102 passed. `make run`: health check `ok`, page served |
| 10 | README says how to build and run | ✅ T11: "Run with Docker" in `README.md` |
| 11 | Only this machine can open the app | ✅ T11a: see below |

Noticed while checking `make run`: without `~/.streamlit/credentials.toml`, Streamlit's first
start asks for an email address in the terminal. It was like this before 005. In a terminal you
press Enter once; without a terminal (this check) it quits, so the check ran with
`STREAMLIT_SERVER_HEADLESS=true` instead of answering, which would have written that file.

### Local only (T11a)

2026-11-25. Health check (`/_stcore/health`) from `localhost` and from the Mac's network
address (192.168.86.130). Connecting to its own network address is enough to show what the port
is bound to.

| Run | `localhost` | Network address |
|---|---|---|
| Before: `docker run -p 8501:8501` | ok | ok (anyone on the network) |
| `make docker-run` (`-p 127.0.0.1:8501:8501`) | ok | refused |
| `make run` (`server.address = "localhost"`) | ok | refused |

With `server.address` set, `make run` prints only `URL: http://localhost:8501`: no Network or
External URL, so it no longer asks an outside service for the public IP (the T9 note). The
container still does, because inside it Streamlit listens on `0.0.0.0`.

## Verify

- [x] T9 Run it in the browser pane: upload the handbook, ask one question (ask the owner
      first — costs money), restart on the same volume, start without a key; record results
- [x] T10 Walk through the acceptance criteria and record the evidence

## Docs

- [x] T11 `README.md`: "Run with Docker" section
- [x] T11a Only this machine can reach the app (found while answering a question about
      the key): `server.address = "localhost"` + test, `-p 127.0.0.1:…` in the Makefile, README
      and Dockerfile comment; check from the network
- [x] T12 Draft decision 017 (Docker image, model baked in, named volume, telemetry off) and a
      dated note on 012 about `-e ANTHROPIC_API_KEY` without a value — approve the text first
- [x] T13 `docs/challenges.md`: add anything new
- [x] T14 Mark 005 done in `spec.md` and `docs/roadmap.md` (v1 done)
