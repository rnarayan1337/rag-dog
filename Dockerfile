# rag-dog: Streamlit UI + ragdog.core, with the embedding model baked in.
#
#   docker build -t rag-dog .
#   docker run --rm -p 127.0.0.1:8501:8501 -e ANTHROPIC_API_KEY -v ragdog-data:/app/.ragdog_db rag-dog
#
# The API key is only ever passed at run time (Rule 8). See specs/005-packaging/plan.md.

# Debian-based slim image: onnxruntime has wheels for it (not for Alpine). Matches .python-version.
FROM python:3.12-slim

# uv from its official image, pinned to the version used locally (Rule 3: uv, not pip)
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv

# Compile .pyc at install time (faster start), copy files instead of linking, use the image's
# Python rather than downloading one, and put the project's environment first on PATH.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --create-home ragdog
WORKDIR /app

# 1. Dependencies only, exactly as locked, without dev tools. This layer is rebuilt only when
#    pyproject.toml or uv.lock changes, so editing app code rebuilds in seconds.
#    uv's download cache lives in a build cache mount: reused between builds, never in the image.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 2. The app. README.md is needed because pyproject.toml names it as the readme.
COPY README.md app.py ./
COPY ragdog/ ragdog/
COPY assets/ assets/
COPY .streamlit/ .streamlit/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev \
    && mkdir .ragdog_db \
    && chown ragdog:ragdog .ragdog_db

# Everything from here on, including the running app, is the non-root user. A new named volume
# mounted on /app/.ragdog_db copies this folder's owner, so the app can write to it.
USER ragdog

# 3. Download the embedding model now (into /home/ragdog/.cache/chroma), so a new container
#    never downloads it on its first upload. Chroma only checks the unpacked files, so the
#    downloaded archive is deleted.
RUN python -c "from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2; \
ONNXMiniLM_L6_V2()(['warm up'])" \
    && rm /home/ragdog/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz

EXPOSE 8501

# Listen on all interfaces, or the published port can't reach Streamlit inside the container.
CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
