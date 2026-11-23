# 003 — Generation: Tasks

Tick each task when done. Keep this file current in the same PR as the code.

## Setup

- [x] T1 Create branch `feature/003-generation`
- [x] T2 Review and approve `spec.md` / `plan.md`
- [x] T3 Add `LLM_MODEL`, `LLM_EFFORT`, `LLM_MAX_TOKENS` to `ragdog/core/config.py`

## Functions

- [x] T4 `Citation`, `Answer` dataclasses and `GenerationError`
- [ ] T5 `document_blocks` + test
- [ ] T6 `to_answer` (text blocks, skip thinking, map citations) + tests
- [ ] T7 `generate_answer` happy path with a fake client + tests (request shape)
- [ ] T8 Guards: blank question, empty chunks, missing API key (no API call) + tests
- [ ] T9 Errors: `refusal`, `max_tokens`, `anthropic.APIError` → `GenerationError` + tests
- [ ] T10 Rule 7 test: only `generate.py` imports `anthropic`

## Verify

- [ ] T11 `scripts/check_answers.py` with the 9 questions
- [ ] T12 Run it on the Acme handbook (ask the owner first — costs money); record answers,
      citations and token counts
- [ ] T13 Walk through every acceptance criterion in `spec.md`

## Close out

- [ ] T14 Add decision 015 (generation: Haiku 5.5 at effort `low`, Citations API with one
      plain-text document per chunk, no server-side fallback) to `docs/decisions.md`
- [ ] T15 Mark 003 ✅ in `docs/roadmap.md`
- [ ] T16 Open PR, review, merge
