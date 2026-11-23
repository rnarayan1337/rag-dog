"""Generation: question + retrieved chunks → Claude → cited answer.

This is the only module that imports a provider SDK (Rule 7).
"""

from dataclasses import dataclass

from anthropic.types import DocumentBlockParam, Message, TextCitation

from ragdog.core.retrieve import RetrievedChunk


class GenerationError(Exception):
    """Generation failed: a refusal, a cut-off answer, a missing key, or an API error."""


@dataclass(frozen=True)
class Citation:
    """One passage Claude quoted to support part of its answer."""

    chunk: RetrievedChunk  # the chunk it came from (filename, page, ...)
    cited_text: str  # the exact sentence(s) quoted from that chunk


@dataclass(frozen=True)
class Answer:
    """Claude's answer, its citations in answer order, and the tokens it used."""

    text: str
    citations: list[Citation]
    input_tokens: int
    output_tokens: int  # thinking included


def document_blocks(chunks: list[RetrievedChunk]) -> list[DocumentBlockParam]:
    """One plain-text document per chunk, in retrieval order, with citations turned on.

    The API numbers documents from 0 in this order, so a citation's document_index is
    the index of its chunk in `chunks`.
    """
    return [
        {
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": chunk.text},
            "title": f"{chunk.filename} p.{chunk.page}",
            "citations": {"enabled": True},
        }
        for chunk in chunks
    ]


def to_citation(citation: TextCitation, chunks: list[RetrievedChunk]) -> Citation:
    """Map one API citation back to the chunk it quotes (document_index = chunk position)."""
    if citation.type != "char_location":  # plain-text documents only produce char_location
        raise GenerationError(f"Unexpected citation type {citation.type!r}")
    if not 0 <= citation.document_index < len(chunks):
        raise GenerationError(
            f"Citation points at document {citation.document_index}, "
            f"but only {len(chunks)} were sent"
        )
    return Citation(chunk=chunks[citation.document_index], cited_text=citation.cited_text)


def to_answer(response: Message, chunks: list[RetrievedChunk]) -> Answer:
    """Join the response's text blocks into one Answer, keeping citations in answer order.

    Thinking blocks (and anything else that isn't text) are skipped.
    """
    parts: list[str] = []
    citations: list[Citation] = []
    for block in response.content:
        if block.type != "text":
            continue
        parts.append(block.text)
        citations.extend(to_citation(c, chunks) for c in block.citations or [])
    return Answer(
        text="".join(parts).strip(),
        citations=citations,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
