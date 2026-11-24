# Challenges

Problems we hit while building rag-dog, what caused them, and how we dealt with them.
Decisions (the choices themselves) live in `decisions.md`; this file is the story of what went
wrong along the way. Newest first within each roadmap item.

Status: ✅ resolved · 🟨 worked around · 🔴 open

## 003 — Generation

### Answers repeat the fact they cite 🔴
*2026-11-23*

- **Symptom:** In 6 of 9 handbook answers, a fact is stated and then repeated almost word for
  word: "Opened products can be returned within 14 days… Opened products can be returned
  within 14 days…".
- **Cause:** The model, not our code. Printing the raw response blocks showed Haiku writes a
  claim in its own words, then outputs the source sentence verbatim as the *cited* text
  block. `to_answer` joins the blocks exactly as the API sends them.
- **Tried:** A prompt line ("State each fact once, in your own words. Don't repeat the source
  text after it; citations are attached automatically."). Still 5/9 repeat. No real change,
  so the line was removed.
- **Next:** Compare models and effort levels (roadmap 012). In the 004 UI, consider showing
  cited blocks as quotes rather than inline text.
- **Lesson:** With citations on, the answer is split into blocks; inspect the raw blocks
  before blaming the code that joins them. Output also varies run to run, so one run can't
  prove a fix.

### Input tokens higher than estimated ✅
*2026-11-23*

- **Symptom:** ~2,500 input tokens per question, not the ~1,500 estimated.
- **Cause:** The Citations feature adds its own system instructions and splits documents into
  sentences.
- **Resolution:** Accepted. It's still about $0.0003 per question on Haiku 5.5. `Answer`
  carries token counts, so the check script shows real usage instead of estimates.

### No server-side refusal fallback on Haiku 5.5 ✅
*2026-11-22*

- **Symptom:** The plan included the `fallbacks="default"` beta, which retries a refused
  request on another model.
- **Cause:** Only some models support it. The docs say not to send it with Haiku 5.5.
- **Resolution:** Dropped. A refusal raises `GenerationError` naming the refusal category.
  Moving to Sonnet or Opus later would mean adding it back.
- **Lesson:** Check a feature against the model you actually chose, not the default one.

### Missing API key fails late and vaguely ✅
*2026-11-22*

- **Symptom:** `anthropic.Anthropic()` with no key doesn't fail. The first request does, with a
  plain `TypeError: Could not resolve authentication method`, which isn't an SDK API error.
- **Resolution:** `generate_answer` checks `ANTHROPIC_API_KEY` itself before creating the
  client and raises `GenerationError("ANTHROPIC_API_KEY is not set")`. Found by testing the
  SDK with no key and no network, before writing the code.

### `load_dotenv()` can't find `.env` from outside the project 🟨
*2026-11-23*

- **Symptom:** A one-off debug script in a temporary folder failed with the vague missing-key
  error above.
- **Cause:** `load_dotenv()` looks for `.env` starting from the calling script's folder and
  walking up. A script outside the project never reaches the project's `.env`.
- **Resolution:** Fine for `scripts/` (inside the project). Scripts elsewhere must pass the
  path explicitly. No request was sent, so it cost nothing.

## 002 — Retrieval

### No similarity cutoff can be chosen yet 🔴
*2026-11-22*

- **Symptom:** We wanted a minimum score below which "the documents don't cover this".
- **Cause:** On the handbook, right pages scored 0.27–0.63 and wrong pages 0.56–1.01. The
  ranges overlap, so any cutoff drops some good matches or keeps some bad ones.
- **Resolution:** No cutoff in v1 (decision 014). The LLM spots weak matches instead, and in 003
  it did correctly answer "the documents don't say". Roadmap 007 revisits this with more data.

### Near-identical codes share a chunk 🟨
*2026-11-22*

- **Symptom:** `XJ-4417` / `XJ-4471` and `E2210` / `E4012` are in the same chunk, so retrieval
  can't tell them apart.
- **Resolution:** Left to the LLM. In 003 Haiku answered all four correctly ($59 vs $129,
  jar vs overheat).

## 001 — Ingestion

### PDF ligatures break search and quotes ✅
*2026-11-22*

- **Symptom:** Extracted text had characters like `ﬁ` instead of `fi`, so "find" didn't match.
- **Resolution:** NFKC-normalise PDF text (decision 013).

### Token counts all came out as 256 ✅
*2026-11-22*

- **Symptom:** When checking that 800-character chunks fit the embedding model's ~256-token
  limit, every chunk measured exactly 256.
- **Cause:** The ONNX tokenizer pads and truncates to 256 by default.
- **Resolution:** Turn off padding and truncation when measuring. Real counts: prose 126–181
  tokens. Code-heavy text reaches ~340, so its tail is cut off (decision 003 notes, decision
  004 revisit trigger).

### Chroma 1.x changed how to set cosine distance ✅
*2026-11-22*

- **Symptom:** Older examples use `metadata={"hnsw:space": "cosine"}`.
- **Resolution:** Chroma 1.5 uses `configuration={"hnsw": {"space": "cosine"}}`. The metric is
  fixed when the collection is created; reopening with a different value is silently ignored
  (decision 002 notes).

### Test setup quirks in Chroma ✅
*2026-11-22*

- Collection names need at least 3 characters (`"t"` errors), so tests use `"test-docs"`.
- A custom embedding function without `get_config` / `build_from_config` triggers a
  `DeprecationWarning`. The fake one in `tests/conftest.py` defines both.

### Duplicate and empty files both return 0 🔴
*2026-11-22*

- **Symptom:** `ingest_file` returns `0` both for a file already stored and for a file with no
  extractable text (e.g. a scanned PDF), so the caller can't tell them apart.
- **Next:** Decide in 004, when the UI needs to show the right message.

## Process

### A commit made on an old copy undid earlier changes ✅
*2026-11-22*

- **Symptom:** A commit reset roadmap statuses and deleted the AGENTS.md Makefile section.
- **Cause:** The files were edited from an older copy, and the review diffed against the wrong
  commit, so it missed the changes.
- **Resolution:** Fixed in follow-up commits. Before pushing, diff the whole branch against
  `main` (`git diff main...HEAD`), not against a recent commit.
