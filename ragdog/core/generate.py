"""Generation: question + retrieved chunks → Claude → cited answer.

This is the only module that imports a provider SDK (Rule 7).
"""

from dataclasses import dataclass

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
