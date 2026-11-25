# 005 — Packaging: Plan

## Files

| File | Change |
|---|---|
| `Dockerfile` (new) | The image |
| `.dockerignore` (new) | What never goes into the image |
| `.streamlit/config.toml` (new) | Streamlit usage stats off, minimal toolbar |
| `ragdog/core/ingest.py` | `get_collection` turns Chroma telemetry off |
| `Makefile` | `docker-build`, `docker-run` |
| `README.md` | "Run with Docker" section |
| `tests/test_ingest.py`, `tests/test_app.py` | Tests for the two telemetry settings |

Prerequisite: Docker on the Mac (Docker Desktop, OrbStack or Colima). The owner installs it
before the build tasks.

## `Dockerfile`

```dockerfile
FROM python:3.12-slim

# uv from its official image, pinned to the version used locally
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --create-home ragdog
WORKDIR /app

# 1. Dependencies only: this layer is rebuilt only when uv.lock changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. The app itself
COPY README.md app.py ./
COPY ragdog/ ragdog/
COPY assets/ assets/
COPY .streamlit/ .streamlit/
RUN uv sync --frozen --no-dev \
    && mkdir .ragdog_db && chown ragdog:ragdog .ragdog_db

USER ragdog

# 3. Download the embedding model now, into /home/ragdog/.cache/chroma
RUN python -c "from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2; \
ONNXMiniLM_L6_V2()(['warm up'])"

EXPOSE 8501
CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
```

Why each part:

- **`python:3.12-slim`:** matches `.python-version`. Debian-based, so onnxruntime's wheels
  install. Alpine uses a different C library that onnxruntime has no wheels for.
- **Two `uv sync` steps:** the first installs only the dependencies, so editing `app.py`
  rebuilds in seconds instead of reinstalling chromadb. `--frozen` means exactly what's in
  `uv.lock`, and the build fails if the lock is out of date. `--no-dev` leaves out pytest.
- **`README.md` is copied:** `pyproject.toml` names it as the readme, and the build backend
  needs it to install the project.
- **`PATH` with `.venv/bin`:** `streamlit` runs straight from the environment. `uv run` at
  start-up could try to sync, which needs write access and network.
- **`.ragdog_db` is created and owned by `ragdog`:** Docker copies the folder's owner into a
  new named volume, so the non-root user can write to it.
- **The model step runs as `ragdog`:** Chroma saves the model under the user's home, which is
  where it looks at run time.
- **`--server.address=0.0.0.0`:** Streamlit must listen on all interfaces, or the published
  port can't reach it from outside the container.
- **No `ENV ANTHROPIC_API_KEY`:** an `ENV` line would bake a value into the image and its
  history.

## `.dockerignore`

```
.env
.envrc
.ragdog_db/
.venv/
.git/
.claude/
tests/
scripts/
specs/
docs/
**/__pycache__/
.pytest_cache/
```

Only what the app needs is copied anyway (`COPY` names files), but the ignore file also
keeps these out of the build context sent to Docker, so `.env` never leaves the project
folder during a build.

## Telemetry

**Chroma** (`ragdog/core/ingest.py`):

```python
from chromadb.config import Settings

client = chromadb.PersistentClient(path=db_dir, settings=Settings(anonymized_telemetry=False))
```

Chroma keeps one client per path in a process and raises an error if the same path is opened
again with different settings. Every open goes through `get_collection`, so the settings are
always the same. Tests open their own temp paths, which don't clash.

Test: replace `chromadb.PersistentClient` with a spy that records the `settings` it's given,
call `get_collection(tmp_path)`, and check `anonymized_telemetry is False`.

**Streamlit** (`.streamlit/config.toml`, committed; `.gitignore` only ignores
`.streamlit/secrets.toml`):

```toml
[browser]
gatherUsageStats = false

[client]
toolbarMode = "minimal"
```

Streamlit reads this from the folder it's started in, so `make run` and the container both
get it. Test: load it with `tomllib` and check both values.

## `Makefile`

```make
docker-build:  ## Build the Docker image
	docker build -t rag-dog .

docker-run:  ## Run the image on port 8501 (key from .env, data in the ragdog-data volume)
	docker run --rm -p 8501:8501 --env-file .env -v ragdog-data:/app/.ragdog_db rag-dog
```

`--rm` removes the container when it stops. The data stays in the volume.

## README section

```bash
make docker-build
make docker-run          # needs ANTHROPIC_API_KEY in .env
```

Then open http://localhost:8501. Without `make`:

```bash
docker build -t rag-dog .
docker run --rm -p 8501:8501 -e ANTHROPIC_API_KEY -v ragdog-data:/app/.ragdog_db rag-dog
```

`-e ANTHROPIC_API_KEY` with no `=value` passes the key from your shell, so it isn't typed on
the command line or saved in shell history. Documents live in the `ragdog-data` volume;
`docker volume rm ragdog-data` deletes them.

## Verification

pytest can't check a Dockerfile, so most of this is done by hand and recorded in `tasks.md`:

| Check | How |
|---|---|
| Builds | `make docker-build`; `docker image ls rag-dog` for the size |
| Contents | `docker run --rm rag-dog ls -a /app` (no `.env`, `tests`, `.git`); `.ragdog_db` empty |
| Non-root | `docker run --rm rag-dog whoami` → `ragdog` |
| Model in image | `ls /home/ragdog/.cache/chroma/onnx_models/all-MiniLM-L6-v2`; no download line in the logs on first upload |
| Key not in image | `docker inspect rag-dog` env and `docker history --no-trunc rag-dog` contain no key |
| v1 goal | `make docker-run`, browser pane, upload the handbook, ask one question (ask the owner first) |
| Volume | stop, `make docker-run` again, handbook still listed |
| No key | `docker run` without the key → warning, chat disabled |
| Local unchanged | `make test`, `make run` |
