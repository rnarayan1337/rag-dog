# 003 — Generation: Tasks

Tick each task when done. Keep this file current in the same PR as the code.

## Setup

- [x] T1 Create branch `feature/003-generation`
- [x] T2 Review and approve `spec.md` / `plan.md`
- [x] T3 Add `LLM_MODEL`, `LLM_EFFORT`, `LLM_MAX_TOKENS` to `ragdog/core/config.py`

## Functions

- [x] T4 `Citation`, `Answer` dataclasses and `GenerationError`
- [x] T5 `document_blocks` + test
- [x] T6 `to_answer` (text blocks, skip thinking, map citations) + tests
- [x] T7 `generate_answer` happy path with a fake client + tests (request shape)
- [x] T8 Guards: blank question, empty chunks, missing API key (no API call) + tests
- [x] T9 Errors: `refusal`, `max_tokens`, `anthropic.APIError` → `GenerationError` + tests
- [x] T10 Rule 7 test: only `generate.py` imports `anthropic`

## Verify

- [x] T11 `scripts/check_answers.py` with the 9 questions
- [x] T12 Run it on the Acme handbook (ask the owner first — costs money); record answers,
      citations and token counts

### Check results (T12)

`acme-handbook.pdf` (4 chunks, so every question gets the whole document), `claude-haiku-5-5`,
effort `low`, run 2026-11-23.

| Question | Expected | Answer | Cited | Tokens in / out |
|---|---|---|---|---|
| What does error E2210 mean? | Jar not seated (p3) | ✅ Jar not seated, plus the fix | p3 | 2,508 / 69 |
| What does error E4012 mean? | Motor overheated (p3) | ✅ Overheated, plus the fix · repeats itself | p3 ×2 | 2,508 / 121 |
| How much does the XJ-4417 cost? | $59, not $129 (p2) | ✅ $59, Mini Blender | p2 | 2,512 / 46 |
| How much is the Turbo Blender? | $129 (p2) | ✅ $129 · repeats itself | p2 | 2,510 / 108 |
| Return an opened product? | 14 days, −10% (p1) | ✅ 14 days, −10% · repeats itself | p1 ×2 | 2,510 / 125 |
| Blender motor warranty? | 5 years, Turbo (p4) | ✅ 5 years, Turbo · repeats itself · adds a guess ("presumably") about other models | p4 ×2 | 2,512 / 174 |
| Who founded Acme? | Dana Whitfield (p1) | ✅ Dana Whitfield, 1998, Tulsa · repeats itself | p1 | 2,506 / 96 |
| How do I fix bitter coffee? | Descale (p3) | ✅ Descale, vinegar then 2 plain · repeats itself | p3 ×2 | 2,510 / 128 |
| What is Acme's annual revenue? | Doesn't say | ✅ "The documents don't contain…" | none | 2,510 / 60 |

**9/9 correct facts, all citations on the expected page.** The XJ-4417 / XJ-4471 trap was
answered correctly. Total 22,586 in + 927 out tokens ≈ $0.003 at $0.10 / $0.50 per million.

Notes:
- **Repetition (6/9):** answers often state a fact, then repeat it almost word for word,
  e.g. "Opened products can be returned within 14 days… Opened products can be returned
  within 14 days…". The repeated sentence is usually the cited one.
  **Cause: the model, not our joining.** One more call (2,510 / 98 tokens) printed the raw
  blocks: Haiku writes a claim, then emits the source sentence verbatim as the *cited* block
  (`' Returns are started from the Orders page of your account, per '` +
  `'Start a return from the Orders page of your account.'` ← cited). `to_answer` joins the
  blocks exactly as sent. The output also varies run to run: the same question repeated
  itself word for word in the first run, and "per <quote>" in the second.
  **Tried: a prompt line** ("State each fact once, in your own words. Don't repeat the source
  text after it; citations are attached automatically."). Re-run 2026-11-23: still 9/9
  correct with the right pages, but **5/9 still repeat** (E4012, Turbo Blender, returns,
  warranty, founder) — no real change from 6/9, and within run-to-run variation. 22,883 in /
  905 out tokens (the line adds ~33 input tokens per question). Not run a second time: the
  result was clear enough. **Line removed** (a rule that doesn't change the output only adds
  tokens). Open; see `docs/challenges.md`.
- **One small guess:** the warranty answer says the two-year warranty "would presumably
  apply" to other models — a reasonable reading, but the prompt says not to guess.
- **Headings in quotes:** some `cited_text` starts with a page heading ("Troubleshooting If
  your blender…"), because PDF extraction joins the heading line to the first sentence.
  Cosmetic; an ingestion detail, not a generation bug.
- **Input tokens were ~2,500, not the ~1,500 estimated.** Citations add their own system
  instructions; the handbook's 4 chunks are ~1,000 tokens of that.
- Output was 46–174 tokens, so at `low` effort Haiku did little or no thinking.
- Weak test, as in 002: 4 chunks means retrieval always sent the right page.

- [x] T13 Walk through every acceptance criterion in `spec.md`

### Acceptance results (T13)

Checked 2026-11-23. No extra API calls: criteria 1 and 8 use the T12 runs.

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 1 | Non-empty text; every citation points at a chunk sent, and its `cited_text` is in that chunk | `test_to_answer_joins_text_and_maps_citations_to_chunks`, `test_generate_answer_returns_the_parsed_answer`, `test_to_answer_rejects_citation_outside_the_chunks_sent`. Real data: all 13 quotes from the T12 runs appear in their chunk (whitespace-normalised), and both raw `cited_text`s from the debug call appear verbatim | ✅ |
| 2 | Only `generate.py` imports `anthropic` | `test_only_generate_imports_a_provider_sdk`, `test_generate_is_scanned_and_does_import_anthropic` (also catches `openai`, `litellm`; proved by a temporary violating file) | ✅ |
| 3 | Key from `ANTHROPIC_API_KEY`; `core` never loads `.env` or stores the key; missing key is a clear error | `test_generate_answer_without_api_key_raises_clear_error`, `test_generate_answer_without_client_builds_one_from_env`. `grep load_dotenv ragdog/` finds nothing; only `scripts/check_answers.py` calls it | ✅ |
| 4 | No chunks → fixed answer, no API call | `test_generate_answer_with_no_chunks_returns_fixed_answer_without_calling_api` | ✅ |
| 5 | Blank question rejected, no API call | `test_generate_answer_rejects_blank_question` (`""`, spaces, newline) | ✅ |
| 6 | Refusal, `max_tokens`, API errors → `GenerationError` saying which | `test_generate_answer_refusal_raises_with_category`, `..._refusal_without_details_says_unknown`, `..._cut_off_at_max_tokens_raises`, `..._bad_key_raises_clear_error`, `..._api_errors_become_generation_error` (rate limit, server, network; cause chained) | ✅ |
| 7 | Model, effort, `max_tokens` from `config.py` | `test_generate_answer_sends_settings_from_config` | ✅ |
| 8 | Handbook: right answer citing the expected page; unanswerable question says so | T12: 9/9 correct, every citation on the expected page, revenue question "The documents don't say…" with no citation | ✅ with notes |

Notes on 8: answers often repeat their cited sentence (open, `docs/challenges.md`), and
the warranty answer adds a mild guess about other models. Neither makes an answer wrong.

Constraints: `ragdog/core/` has no UI/HTTP imports and no `load_dotenv()` ✅; unit tests use
a fake client, no network ✅; every real run was approved first ✅.

Gap: nothing in the code checks that `cited_text` really is in the chunk; the API guarantees
it, and the check above confirmed it on real data. Enforcing citations is roadmap 007.

## Close out

- [x] T14 Add decision 015 (generation: Haiku 5.5 at effort `low`, Citations API with one
      plain-text document per chunk, no server-side fallback) to `docs/decisions.md`
- [x] T15 Mark 003 ✅ in `docs/roadmap.md`
- [ ] T16 Open PR, review, merge
