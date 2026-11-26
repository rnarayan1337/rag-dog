# rag-dog
Fetches answers from your documents.

## Run with Docker

You need Docker and an [Anthropic API key](https://console.anthropic.com/).
Put the key in a `.env` file in the project folder:

```
ANTHROPIC_API_KEY=your-key
```

Then build the image and start it:

```bash
make docker-build
make docker-run
```

Open http://localhost:8501, upload a PDF, Markdown or text file, and ask a question.

Without `make`, pass the key from your shell instead of from `.env`:

```bash
docker build -t rag-dog .
read -s ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY    # paste the key, press Enter
docker run --rm -p 127.0.0.1:8501:8501 -e ANTHROPIC_API_KEY -v ragdog-data:/app/.ragdog_db rag-dog
```

`read -s` takes the key without showing it or saving it in your shell history, and
`-e ANTHROPIC_API_KEY` with no `=value` copies it from your shell into the container. The key is
only passed when the container starts; it's never stored in the image. If the app says the key
is not set, check `.env` (with `make`) or your shell.

`-p 127.0.0.1:8501:8501` means only this computer can open the app. With `-p 8501:8501`, anyone
on your network could use it, and every question they asked would be charged to your key.

Your documents are kept in the Docker volume `ragdog-data`, so they're still there after the
container stops. To delete them:

```bash
docker volume rm ragdog-data
```
