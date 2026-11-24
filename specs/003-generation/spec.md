# 003 — Generation: Spec

**Status:** Done · **Roadmap:** 003 · **Decisions:** 011, 012, 014, 015

## Goal

Given a question and the chunks from `retrieve()`, ask Claude for an answer that uses only
those chunks and cites them, so 004 (UI) can show an answer with its sources.

## User story

As a user, I ask a question about my uploaded documents and get a short answer. Each claim
names the file and page it came from, and quotes the passage it relied on.

## In scope

- One function, `generate_answer(question, chunks)`, in `ragdog/core/generate.py`. It is the
  only place that imports `anthropic` (Rule 7).
- Claude **Haiku 5.5** (`claude-haiku-5-5`), effort `low`. Model, effort and `max_tokens`
  live in `config.py`.
- Each chunk is sent as its own plain-text `document` block with the API's **Citations**
  feature turned on. Citations come back from the API with the exact quoted text, so we
  don't parse markers out of the answer.
- A system prompt that says to answer only from the documents, and to say so when they don't
  contain the answer.
- Clear errors for a refusal, an answer cut off by `max_tokens`, and API failures.
- A script that runs fixed questions against an ingested document and prints each answer with
  its citations and token use, for checking by eye.

## Out of scope (v1)

- Streaming (comes with the 004 UI)
- Conversation history / follow-up questions (each question stands alone)
- Server-side refusal fallback: Haiku 5.5 doesn't have one
- Enforcing citations or refusing on weak matches (roadmap 007, parked)
- Scoring answers automatically (faithfulness) — roadmap 006
- Other providers (roadmap 011, parked)
- Prompt caching (five ~800-character chunks are too small to benefit)

## Answer model

`Answer` (frozen dataclass):

| Field | Value |
|---|---|
| `text` | the full answer text |
| `citations` | list of `Citation`, in the order they appear in the answer |
| `input_tokens` | tokens sent (from `response.usage`) |
| `output_tokens` | tokens generated, thinking included |

`Citation` (frozen dataclass):

| Field | Value |
|---|---|
| `chunk` | the `RetrievedChunk` it points at (gives filename, page, chunk_index) |
| `cited_text` | the exact passage Claude quoted from that chunk |

## Acceptance criteria

1. A question with chunks returns an `Answer` with non-empty text. Every citation points at
   one of the chunks passed in, and its `cited_text` appears in that chunk's text.
2. `ragdog/core/generate.py` is the only module that imports `anthropic` (Rule 7).
3. The API key is read from `ANTHROPIC_API_KEY` in the environment; nothing in `core` loads
   `.env` or stores the key (Rule 8). A missing key gives a clear error.
4. An empty chunk list returns a fixed "no documents" answer **without** calling the API.
5. A blank question is rejected with a clear error, without calling the API.
6. A refusal, an answer cut off by `max_tokens`, or an API error (auth, rate limit, network)
   raises `GenerationError` with a message saying which one.
7. Model, effort and `max_tokens` come from `config.py`.
8. On the Acme handbook, each check-script question gets the right answer with a citation to
   the expected page, and the question the handbook can't answer says so. Judged by eye;
   misses are written down, not hidden.

## Constraints

- `ragdog/core/` has no UI or HTTP imports, and doesn't call `load_dotenv()`.
- Unit tests make no network calls and cost nothing (fake client).
- Every real API call (the check script) costs money: ask the owner before each run.
