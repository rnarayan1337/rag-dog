# Decision Log

Each entry records what we chose, why, what we gave up, and when to revisit it.
Add a new entry whenever a decision is made or changed — in the same PR as the code.

---

## 001 — Build without a framework (no LangChain)
*2026-11-21*

- **Decision:** Plain Anthropic SDK + ChromaDB.
- **Why:** The whole loop is ~100 lines. Writing it by hand means every step can be explained.
- **Trade-off:** More code to write; no ready-made integrations.
- **Revisit when:** v1 works — rebuilding in LangChain/LlamaIndex is a good comparison exercise.

## 002 — Vector store: ChromaDB, persistent mode
*2026-11-21*

- **Decision:** ChromaDB `PersistentClient`, cosine distance.
- **Why:** Open source, runs in-process, no account or server. Persistent mode keeps embeddings across restarts.
- **Trade-off:** Not built for large-scale production (vs. Pinecone, pgvector, etc.).
- **Note:** Distance metric is fixed when the collection is created.
- **Note (2026-11-22):** In Chroma 1.x, cosine is set with
  `configuration={"hnsw": {"space": "cosine"}}`. Reopening an existing collection ignores a
  different value.
- **Revisit when:** Multi-user or millions of chunks.

## 003 — Embedding model: all-MiniLM-L6-v2
*2026-11-21*

- **Decision:** ChromaDB's default local model (384 dimensions).
- **Why:** Free, local, private, fast, no API key.
- **Trade-off:** Moderate quality, English-centric, ~256-token input limit (longer text is silently truncated).
- **Rule:** The same model must embed both documents and queries.
- **Implementation (2026-11-22):** The embedding function is set explicitly
  (`ONNXMiniLM_L6_V2`) instead of relying on Chroma's default, so a Chroma upgrade can't
  silently switch models.
- **Measured (2026-11-22):** Prose chunks of 560–750 chars are 126–181 tokens. Code-heavy text
  (model numbers, error codes, emails) can reach ~340 tokens at 800 chars, so its tail is
  truncated.
- **Revisit when:** The golden set shows retrieval misses. Shortlist from MTEB Retrieval, compare on recall@k.
- **Migration plan:** Blue/green — re-embed into a new collection, evaluate, switch, drop old.

## 004 — Chunking: recursive, per page
*2026-11-21*

- **Decision:** Recursive splitting (paragraph → sentence → word), ~800 chars, ~150 overlap, within each page.
- **Why:** Respects natural boundaries; fits the embedding model's token limit; overlap keeps ideas that straddle a boundary intact; per-page gives page numbers for citations.
- **Trade-off:** Chunks never cross page boundaries.
- **Revisit when:** Answers miss context that spans pages (fix: concatenate with a page-offset
  map), or the golden set shows misses on code-heavy documents (fix: lower `CHUNK_SIZE` to
  ~600).

## 005 — Chunk ID and metadata schema
*2026-11-21*

- **Decision:** `id = f"{doc_hash}:{chunk_index}"`
- **Metadata:** `doc_hash`, `filename`, `file_location`, `chunk_index`, `page`, `embedding_model`
- **Why:** Unique and stable. A pure chunk-text hash was rejected: identical text in two documents (footers, disclaimers) would collide and overwrite citations.
- **Note:** Chunk text is stored alongside its vector, so re-embedding doesn't need the original files.

## 006 — Dedup by content hash
*2026-11-21*

- **Decision:** SHA-256 of file bytes, read in 1 MB blocks.
- **Why:** Same content → same hash regardless of filename. Streaming keeps memory flat for large files.
- **Rejected:** File metadata (size/mtime) — unreliable, and browser uploads don't provide mtime.
- **Open:** Updated document with the same filename → delete old chunks for that filename (not in v1).

## 007 — Architecture: monolith with a UI-free core
*2026-11-21*

- **Decision:** Streamlit calls `ragdog/core/` directly. `core/` never imports UI or HTTP code.
- **Why:** Fastest path to v1, while keeping a clean seam for a FastAPI layer later.
- **Trade-off:** No API for other clients in v1.
- **Revisit when:** A second client (CLI, Slack bot) is needed — see roadmap 009.

## 008 — v1 ingestion: browser upload
*2026-11-21*

- **Decision:** Users upload files through the UI (not a mounted folder).
- **Why:** Zero setup for someone trying the demo.
- **Note:** Parsing and chunking happen in Python either way.

## 009 — v1 scope: happy path only
*2026-11-21*

- **Decision:** No guardrails, re-ranking, or eval in v1.
- **Why:** Get the full loop working end to end first, then harden.

## 010 — Tooling
*2026-11-21*

- **Decision:** `uv` for environment and dependencies; signed commits required on `main`.
- **Why:** Fast, single tool with a lockfile; signed commits prove authorship.

## 011 — LLM: Claude for v1, behind one function
*2026-11-22*

- **Decision:** Use Claude via the Anthropic SDK for v1. All LLM calls go through a single
  `generate_answer` function in `ragdog/core/`.
- **Why:** The key is ready and the SDK is installed — fastest path to a working v1. One
  function keeps the provider swappable.
- **Trade-off:** Users need an Anthropic API key for now.
- **Considered:** LiteLLM (one interface for many providers, but an extra dependency that can
  lag provider SDKs); OpenAI SDK pointed at OpenAI-compatible endpoints (Ollama, Groq, etc.;
  may miss provider-specific features).
- **Revisit when:** After v1 — see roadmap 011 (pluggable LLM).

## 012 — API key handling
*2026-11-22*

- **Decision:** The key comes from an environment variable: `.env` when running locally,
  `-e ANTHROPIC_API_KEY=...` for Docker.
- **Why:** Simple and keeps keys out of code and the image.
- **Considered:** A key field in the UI — friendlier for a demo, but if hosted for others their
  keys would pass through our server. Listed as an idea in the roadmap.

## 013 — Text extraction cleanup
*2026-11-22*

- **Decision:** PDF text is NFKC-normalised (ligatures like `ﬁ` → `fi`). `.txt` / `.md` are
  read as UTF-8, with undecodable bytes replaced by `�`.
- **Why:** PDF fonts often produce ligature characters that don't match normal spelling in
  search or citations. Replacing bad bytes means one stray byte doesn't fail a whole upload.
- **Trade-off:** NFKC also changes some characters on purpose (e.g. `²` → `2`, full-width
  letters → normal). Files in other encodings lose their non-ASCII characters.
- **Revisit when:** Non-English documents matter (detect the encoding instead of assuming UTF-8).

## 014 — Retrieval: top-k with distances, no cutoff in v1
*2026-11-22*

- **Decision:** `retrieve()` returns the `TOP_K = 5` closest chunks as frozen `RetrievedChunk`
  dataclasses (text, filename, page, chunk_index, doc_hash, cosine distance), closest first,
  optionally filtered to one `doc_hash`. There is no minimum-similarity cutoff: the top k
  always come back.
- **Why:** 5 × ~800-char chunks is about 1,000 tokens of context, which is enough for most
  answers without much noise. Returning the distance keeps the evidence needed for a cutoff
  later. A dataclass gives 003 named, typed fields instead of dict keys.
- **Trade-off:** A question the documents can't answer still gets 5 chunks. Spotting a weak
  match is left to the LLM in 003, until roadmap 007.
- **Measured (2026-11-22):** On the 4-page handbook, the right page scored 0.27–0.63 and wrong
  pages 0.56–1.01. The ranges overlap, so one small document can't set a cutoff.
- **Revisit when:** 006's golden set shows recall@5 misses (try a larger k, or re-ranking in
  008), or 007 adds a weak-match check (use the recorded distances to choose a threshold).

## 015 — Generation: Haiku 5.5, Citations API, one document per chunk
*2026-11-23*

- **Decision:** `generate_answer(question, chunks)` in `ragdog/core/generate.py` calls
  `claude-haiku-5-5` at effort `low` (non-streaming, `max_tokens` 16000). Each chunk is sent as
  its own plain-text `document` block with citations enabled, and the API's citations are
  mapped back to chunks by `document_index`. The answer comes back as a frozen `Answer` (text,
  citations, token counts). Refusals, `max_tokens` cut-offs, a missing key and API errors all
  raise one `GenerationError`. No chunks means a fixed answer without calling the API.
- **Why:** Short answers from ~1,000 tokens of context don't need a large model. Haiku costs
  $0.10 / $0.50 per million tokens, against $2 / $10 for Sonnet 5.5 and $4 / $20 for
  Opus 5.5. The Citations API returns the exact quoted text with each claim, so we don't parse
  "[1]" markers or trust the model to number sources. Plain-text documents give sentence-level
  quotes, which are better evidence than whole 800-character chunks.
- **Trade-off:** No server-side refusal fallback: Haiku 5.5 doesn't support it, so a refusal
  is an error the user sees. Probably weaker than Sonnet or Opus at careful reading and at
  saying "I don't know", not yet measured (roadmap 012). Citations can't be combined with
  structured JSON output.
- **Considered:** Opus 5.5 (the SDK default, ~40× the cost); Sonnet 5.5; asking for "[1]"
  markers in the prompt and parsing them; custom-content documents (whole-chunk citations).
- **Measured (2026-11-23):** Handbook, 9 questions: 9/9 correct, every citation on the
  expected page, the XJ-4417 / XJ-4471 trap handled, and the unanswerable question answered
  "the documents don't say". About 2,500 input tokens per question (the citations feature adds
  its own instructions), so roughly $0.003 per 9-question run. 5–6 of 9 answers repeat their
  cited sentence. A prompt line to stop that didn't help and was removed
  (`docs/challenges.md`).
- **Revisit when:** Roadmap 012 compares models (switch with `LLM_MODEL`, and add the
  fallback if leaving Haiku), the 004 UI needs streaming, or 006's golden set shows wrong
  answers.

## 016 — UI: one Streamlit page, uploads through a temp file
*2026-11-24*

- **Decision:** `app.py` is one Streamlit page that calls `ragdog/core` directly (decision 007).
  - The sidebar has an uploader (PDF, Markdown and text, several files at once) with one
    status line per file, the list of stored documents, and a "Search in" choice.
  - The main area is a chat. Its history lasts for the browser session only, and each question
    is answered on its own.
  - Each upload is written to a temp folder under its original name, ingested with
    `file_location` set to that name, and then deleted.
  - The UI checks `already_ingested` before calling `ingest_file`, so a 0 from `ingest_file`
    can only mean "no text found".
  - Answers aren't streamed.
  - The collection and its embedding model are opened once with `st.cache_resource`.
- **Changes decision 005:** for uploads, `file_location` holds the uploaded file's name, not a
  path on disk. Scripts still store the path. Nothing reads the field today, and chunk text is
  stored, so re-embedding doesn't need the file.
- **Why:**
  - **Temp file:** `ingest_file` takes a path, and naming the temp file after the original
    keeps `filename` correct without changing `core`.
  - **Duplicate check in the UI:** "already uploaded" and "no text found" are told apart
    without changing `ingest_file`'s return value.
  - **No streaming:** answers are 50–180 tokens and arrive in a second or two. Streaming would
    need a second function that calls the LLM (against Rule 7), and citations would arrive in
    pieces.
  - **Cache:** Streamlit reruns the whole script on every click, and without the cache each
    rerun would reload the model.
- **Trade-off:**
  - No copy of an uploaded file is kept, so re-parsing it (with a better PDF reader, say)
    means uploading it again.
  - The answer appears all at once.
  - Chat history is lost on reload, and there are no follow-up questions.
  - The upload flow has one broad `except`, so one bad file doesn't stop the rest.
- **Considered:**
  - Keeping copies under `.ragdog_db/uploads/`: re-parsing would be possible, but it takes
    more disk and keeps more copies of user documents.
  - Making `ingest_file` return a status instead of 0: a change to the core API for one
    caller.
  - Streaming the answer.
- **Measured (2026-11-24):** In the browser, on a fresh database:
  - The handbook gave "added 4 chunks", a renamed copy "already uploaded", and an empty file
    "no text found".
  - The stored chunks have `acme-handbook.pdf` in both `filename` and `file_location`.
  - 3 questions were answered correctly with the expected pages, for about $0.001.
- **Revisit when:**
  - Answers get long enough that waiting feels slow (streaming).
  - Follow-up questions are wanted (send history to `generate_answer`).
  - Roadmap 009's API also takes uploads: move the duplicate / no-text check into `core` so
    the two clients don't each have a copy.
  - Roadmap 010 needs the original files.
