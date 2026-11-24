"""Eyeball generation: ingest a document, ask fixed questions, print Claude's cited answers.

Usage:
    uv run python scripts/check_answers.py path/to/acme-handbook.pdf

Every run calls the Claude API and costs money (well under a cent on Haiku 5.5).
The questions and expected answers are written for the Acme handbook (003 spec,
criterion 8). Judge each answer by eye against the expected one.
"""

import argparse

from dotenv import load_dotenv

from ragdog.core.config import LLM_MODEL
from ragdog.core.generate import Answer, GenerationError, generate_answer
from ragdog.core.ingest import hash_file, ingest_file
from ragdog.core.retrieve import retrieve

# (question, expected answer, page that should be cited; None = the handbook doesn't say)
QUESTIONS: list[tuple[str, str, int | None]] = [
    ("What does error E2210 mean?", "Jar not seated correctly", 3),
    ("What does error E4012 mean?", "Motor has overheated", 3),
    ("How much does the XJ-4417 cost?", "$59 (Mini Blender, not the $129 XJ-4471)", 2),
    ("How much is the Turbo Blender?", "$129", 2),
    ("How long do I have to return an opened product?", "14 days, minus 10% restocking fee", 1),
    ("How long are blender motors covered by warranty?", "5 years (Turbo Blender motors)", 4),
    ("Who founded Acme?", "Dana Whitfield (1998, Tulsa)", 1),
    ("How do I fix bitter coffee?", "Descale: vinegar + water cycle, then two plain", 3),
    ("What is Acme's annual revenue?", "Says the handbook doesn't say", None),
]


def show(question: str, expected: str, page: int | None, answer: Answer) -> None:
    """Print one answer with its citations, next to what we expected."""
    where = f"p{page}" if page else "no citation"
    print(f"\nQ: {question}")
    print(f"   expected: {expected} ({where})")
    print(f"   answer:   {' '.join(answer.text.split())}")
    for citation in answer.citations:
        quote = " ".join(citation.cited_text.split())
        print(f'   cites p{citation.chunk.page}: "{quote}"')
    if not answer.citations:
        print("   (no citations)")
    print(f"   tokens:   {answer.input_tokens} in / {answer.output_tokens} out")


def main() -> None:
    load_dotenv()  # ANTHROPIC_API_KEY from .env; only entry points do this, never ragdog/core
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="document to ingest and question")
    args = parser.parse_args()

    stored = ingest_file(args.path)
    print(f"Ingested {stored} new chunks" if stored else "Already ingested")
    doc_hash = hash_file(args.path)
    print(f"Model: {LLM_MODEL}")

    total_in = total_out = 0
    for question, expected, page in QUESTIONS:
        chunks = retrieve(question, doc_hash=doc_hash)
        try:
            answer = generate_answer(question, chunks)
        except GenerationError as e:
            print(f"\nQ: {question}\n   ERROR: {e}")
            continue
        show(question, expected, page, answer)
        total_in += answer.input_tokens
        total_out += answer.output_tokens

    print(f"\nTotal: {total_in} input + {total_out} output tokens")


if __name__ == "__main__":
    main()
