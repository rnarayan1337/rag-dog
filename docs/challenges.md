# Challenges

Problems we hit while building rag-dog, what caused them, and how we dealt with them.
Decisions (the choices themselves) live in `decisions.md`; this file is the story of what went
wrong along the way. Newest first within each roadmap item.

Status: ✅ resolved · 🟨 worked around · 🔴 open

## 004 — Upload UI

### Every click would ingest the uploads again ✅
*2026-11-24*

- **Symptom (found in planning):** Streamlit reruns the whole script on every click, and the
  file uploader keeps its files across reruns. Ingesting whatever is in the uploader would
  run again on each click, and dedup would then print "already uploaded" for a file that was
  just added.
- **Resolution:** Each file's status is kept in `st.session_state`, keyed by Streamlit's
  `file_id`, and a file is only ingested the first time it's seen. A test reruns the page
  with the file still in the uploader and checks nothing changes. Confirmed in the browser in
  T11.
- **Lesson:** In Streamlit, anything with a side effect must remember that it already ran.

### `$` in answers would be drawn as maths ✅
*2026-11-24*

- **Symptom (found in planning):** Streamlit's markdown treats text between two `$` signs as a
  formula, so "$59 and $129" would be drawn as maths. `*` and `_` in a quote or filename
  would turn into italics.
- **Resolution:** Source lines and the user's question are fully escaped. Claude's answer
  only has `$` escaped, so its own bold and lists still render. Tested, and seen correctly in
  the browser ("sells for $59").

### Tests would have loaded the real `.env` ✅
*2026-11-24*

- **Symptom:** `app.py` calls `load_dotenv()`, and `.env` holds the real key. In tests, that
  would put the key into the test process and make the missing-key test fail.
- **Resolution:** `load_dotenv()` runs inside `main()`, not at import, so `import app` has no
  side effects. An autouse fixture replaces `dotenv.load_dotenv` with a no-op, so each test
  sets the environment itself.

### Test setup quirks in Streamlit ✅
*2026-11-24*

- `AppTest` doesn't expose a `disabled` property on the chat input; the tests read
  `chat_input[0].proto.disabled`.
- `st.cache_resource` is shared by every `AppTest` in the process, so one test's collection
  would leak into the next. A fixture clears it before each test.
- `AppTest` runs `app.py` fresh each time, so monkeypatching `ragdog.core.generate.generate_answer`
  or `ragdog.core.ingest.get_collection` before `run()` is enough; the script's
  `from … import` picks up the fake.

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
- **Next:** Compare models and effort levels (roadmap 012).
- **004 (2026-11-24):** The UI lists the quotes separately under "Sources", so the evidence
  is clear, but the answer text still repeats itself (seen again in T11 for E2210).
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

### Duplicate and empty files both return 0 ✅
*2026-11-22 · resolved 2026-11-24*

- **Symptom:** `ingest_file` returns `0` both for a file already stored and for a file with no
  extractable text (e.g. a scanned PDF), so the caller can't tell them apart.
- **Resolution (004):** The UI calls `already_ingested` first and says "already uploaded". By
  the time `ingest_file` returns 0, the file can't be a duplicate, so it says "no text found".
  `ingest_file` is unchanged (decision 016). Seen in the browser in T11.

## Process

### `awk` counted bytes, so the wrong line was edited ✅
*2026-11-24*

- **Symptom:** A line-length check flagged a test line as over 100 characters, and a `sed`
  edit replaced it with a function signature, breaking the test file.
- **Cause:** `awk length` counts bytes. The line had `·` and curly quotes, which take several
  bytes each, so it was really under 100 characters. The long line was a different one.
- **Resolution:** Restored the line, fixed the real one, and now check lengths in Python
  (characters, not bytes). The tests caught the break straight away.

### Test files in a hidden folder ✅
*2026-11-24*

- **Symptom:** For the T11 browser run, the upload files were in a hidden temporary folder
  that's awkward to reach from a file dialog.
- **Resolution:** Copied them to `~/Downloads/rag-dog-t11/`. Files a person has to pick go
  somewhere they can find.

### A commit made on an old copy undid earlier changes ✅
*2026-11-22*

- **Symptom:** A commit reset roadmap statuses and deleted the AGENTS.md Makefile section.
- **Cause:** The files were edited from an older copy, and the review diffed against the wrong
  commit, so it missed the changes.
- **Resolution:** Fixed in follow-up commits. Before pushing, diff the whole branch against
  `main` (`git diff main...HEAD`), not against a recent commit.
