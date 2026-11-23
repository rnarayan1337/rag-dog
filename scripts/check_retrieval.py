"""Eyeball retrieval: ingest a document, ask fixed questions, print what comes back.

Usage:
    uv run python scripts/check_retrieval.py path/to/acme-handbook.pdf

The questions and expected pages are written for the Acme handbook. A question is a HIT
when its expected page is in the top 3 (002 spec, criterion 7).
"""

import argparse

from ragdog.core.ingest import hash_file, ingest_file
from ragdog.core.retrieve import RetrievedChunk, retrieve

HIT_WITHIN: int = 3

# (question, page that answers it)
QUESTIONS: list[tuple[str, int]] = [
    ("What does error E2210 mean?", 3),
    ("What does error E4012 mean?", 3),
    ("How much does the XJ-4417 cost?", 2),
    ("How much is the Turbo Blender?", 2),
    ("How long do I have to return an opened product?", 1),
    ("How long are blender motors covered by warranty?", 4),
    ("Who founded Acme?", 1),
    ("How do I fix bitter coffee?", 3),
]


def preview(text: str, width: int = 80) -> str:
    """First `width` characters of a chunk on one line."""
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= width else one_line[: width - 1] + "…"


def check(question: str, expected_page: int, results: list[RetrievedChunk]) -> bool:
    """Print one question's results; return True if the expected page is in the top 3."""
    pages = [r.page for r in results[:HIT_WITHIN]]
    hit = expected_page in pages
    print(f"\n{'HIT ' if hit else 'MISS'}  expected p{expected_page}  |  {question}")
    for rank, r in enumerate(results, start=1):
        print(f"  {rank}. {r.distance:.3f} · p{r.page} · {preview(r.text)}")
    return hit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="document to ingest and question")
    args = parser.parse_args()

    stored = ingest_file(args.path)
    print(f"Ingested {stored} new chunks" if stored else "Already ingested")
    doc_hash = hash_file(args.path)

    hits = sum(
        check(question, page, retrieve(question, doc_hash=doc_hash))
        for question, page in QUESTIONS
    )
    print(f"\n{hits}/{len(QUESTIONS)} questions have the expected page in the top {HIT_WITHIN}")


if __name__ == "__main__":
    main()
