# Shortcuts for the uv commands in AGENTS.md. Run `make` to list them.

.DEFAULT_GOAL := help
.PHONY: help install test run clean docker-build docker-run

help:  ## List available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-13s %s\n", $$1, $$2}'

install:  ## Install dependencies from uv.lock
	uv sync

test:  ## Run the test suite
	uv run pytest

run:  ## Start the Streamlit UI
	uv run streamlit run app.py

clean:  ## Remove Python and pytest caches (keeps .ragdog_db)
	find . -type d -name __pycache__ -not -path './.venv/*' -prune -exec rm -rf {} +
	rm -rf .pytest_cache

docker-build:  ## Build the Docker image `rag-dog`
	docker build -t rag-dog .

docker-run:  ## Run the image on port 8501 (key from .env, documents in the ragdog-data volume)
	docker run --rm -p 127.0.0.1:8501:8501 --env-file .env -v ragdog-data:/app/.ragdog_db rag-dog
