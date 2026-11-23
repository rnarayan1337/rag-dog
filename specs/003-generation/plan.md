# 003 — Generation: Plan

## Module

`ragdog/core/generate.py` — the only module that imports `anthropic` (Rule 7).

## Flow

```
generate_answer(question, chunks, client=None)
  ├─ reject a blank question (ValueError)
  ├─ no chunks → return NO_DOCUMENTS answer (no API call)
  ├─ if client is None:
  │      no ANTHROPIC_API_KEY in os.environ → GenerationError
  │      client = anthropic.Anthropic()                       # reads ANTHROPIC_API_KEY
  ├─ response = client.messages.create(
  │      model=LLM_MODEL, max_tokens=LLM_MAX_TOKENS,
  │      output_config={"effort": LLM_EFFORT},
  │      system=SYSTEM_PROMPT,
  │      messages=[{"role": "user", "content": [*document_blocks(chunks), question_block]}])
  │    (anthropic.APIError → GenerationError)
  ├─ check stop_reason: "refusal" / "max_tokens" → GenerationError
  └─ return to_answer(response, chunks)
```

## Request shape

One `document` block per chunk, in retrieval order, then the question:

```python
{
    "type": "document",
    "source": {"type": "text", "media_type": "text/plain", "data": chunk.text},
    "title": f"{chunk.filename} p.{chunk.page}",
    "citations": {"enabled": True},
}
```

- Plain-text documents are split into sentences by the API, so `cited_text` is the sentence(s)
  Claude relied on, not the whole 800-character chunk.
- `document_index` in each citation is 0-based across all document blocks in the request,
  so `chunks[document_index]` is the chunk it points at.
- Citations must be enabled on every document in the request, or none.
- Citations can't be combined with `output_config.format` (structured output) — a 400. We
  don't use it.

## Response shape

`response.content` is a list of blocks. With thinking on, it may start with `thinking`
blocks; we skip anything that isn't `type == "text"`. The answer is split across text blocks,
and a block that makes a claim carries a `citations` list (otherwise `None`):

```json
{"type": "text", "text": "Error E2210 means the jar is not seated correctly",
 "citations": [{"type": "char_location", "cited_text": "Error E2210 means the jar is not
   seated correctly. ", "document_index": 0, "document_title": "acme-handbook.pdf p.3",
   "start_char_index": 0, "end_char_index": 52}]}
```

`cited_text` doesn't count toward output tokens.

## Types and functions

| Name | Signature | Notes |
|---|---|---|
| `Citation` | frozen `@dataclass` | `chunk: RetrievedChunk`, `cited_text: str` |
| `Answer` | frozen `@dataclass` | `text`, `citations`, `input_tokens`, `output_tokens` |
| `GenerationError` | `Exception` subclass | One error type for callers (UI, script) to catch |
| `document_blocks` | `(chunks: list[RetrievedChunk]) -> list[dict]` | Builds the request's document blocks |
| `to_answer` | `(response, chunks: list[RetrievedChunk]) -> Answer` | Joins text blocks, maps citations to chunks; bad `document_index` → `GenerationError` |
| `generate_answer` | `(question: str, chunks: list[RetrievedChunk], client: anthropic.Anthropic \| None = None) -> Answer` | Entry point (Rule 7) |

`client=None` mirrors `retrieve(collection=None)`: real code passes nothing, tests pass a fake.

## Settings (`ragdog/core/config.py`)

| Setting | Value | Why |
|---|---|---|
| `LLM_MODEL` | `"claude-haiku-5-5"` | Short answers from ~1,000 tokens of context; cheapest tier |
| `LLM_EFFORT` | `"low"` | Haiku 5.5 always thinks adaptively, default `medium`; `low` is enough for simple Q&A |
| `LLM_MAX_TOKENS` | `16000` | Room for thinking plus the answer (thinking counts toward the limit) |

## System prompt

```
Answer the user's question using only the documents provided.
If the documents don't contain the answer, say that they don't, and don't guess.
Keep the answer short.
```

## Errors

| Case | What we raise |
|---|---|
| Blank question | `ValueError` (same as `retrieve`) |
| `stop_reason == "refusal"` | `GenerationError("Claude declined to answer (category: …)")` |
| `stop_reason == "max_tokens"` | `GenerationError("Answer was cut off at max_tokens")` |
| `anthropic.AuthenticationError` | `GenerationError("ANTHROPIC_API_KEY is missing or invalid")` |
| other `anthropic.APIError` (rate limit, network, server) | `GenerationError(...)` with the cause chained (`raise ... from e`) |
| `ANTHROPIC_API_KEY` not set | `GenerationError("ANTHROPIC_API_KEY is not set")`, checked before creating the client |

Why check the key ourselves: with SDK 2.12.0, `anthropic.Anthropic()` with no key doesn't
fail. The first request does, with a plain `TypeError` ("Could not resolve authentication
method"), which isn't an `APIError`. Checking up front gives a clear message. (Tested
2026-11-22, no network call.)

The SDK already retries rate-limit and server errors twice before raising; we don't add our own.

## Check script

`scripts/check_answers.py` — calls `load_dotenv()` (allowed here, not in `core`):

- Takes a document path, ingests it (no-op if stored), and for each question runs
  `retrieve` then `generate_answer`, printing the answer, each citation as
  `p<page> · "<cited_text>"`, and the token counts. Ends with total tokens.
- Questions — the 8 from 002 plus one the handbook can't answer:

| Question | Expected answer | Expected page |
|---|---|---|
| What does error E2210 mean? | Jar not seated correctly | 3 |
| What does error E4012 mean? | Motor has overheated | 3 |
| How much does the XJ-4417 cost? | $59 (the Mini Blender, not the $129 XJ-4471) | 2 |
| How much is the Turbo Blender? | $129 | 2 |
| How long do I have to return an opened product? | 14 days, minus a 10% restocking fee | 1 |
| How long are blender motors covered by warranty? | 5 years (Turbo Blender motors) | 4 |
| Who founded Acme? | Dana Whitfield, 1998, Tulsa | 1 |
| How do I fix bitter coffee? | Descale: vinegar/water cycle, then two plain water | 3 |
| What is Acme's annual revenue? | Says the handbook doesn't say | — |

Cost: at Haiku 5.5 prices ($0.10 / $0.50 per million tokens) a full run should be well under
one cent. The script prints the real token counts so we can confirm.

## Testing

`pytest` with a fake client (an object with `messages.create` returning a canned response),
so no network and no cost:

- Request shape: model, effort, max_tokens from config; one document block per chunk with
  title and citations enabled; question last
- `to_answer`: joins text blocks, skips thinking blocks, maps `document_index` to the right
  chunk, keeps citation order; bad index raises
- Empty chunks: fixed answer, `create` never called
- Blank question rejected, `create` never called
- `refusal` and `max_tokens` stop reasons raise `GenerationError`
- An `anthropic.APIError` from `create` becomes `GenerationError`
- Rule 7: only `generate.py` imports `anthropic` (scan the source files)

Answer **quality** can't be tested with a fake — that's what the check script and, later,
roadmap 006 are for.
