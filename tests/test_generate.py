"""Tests for ragdog.core.generate (no network: the API client is faked)."""

from typing import Any

import pytest
from anthropic.types import Message

from ragdog.core.config import LLM_EFFORT, LLM_MAX_TOKENS, LLM_MODEL
from ragdog.core.generate import (
    SYSTEM_PROMPT,
    GenerationError,
    document_blocks,
    generate_answer,
    to_answer,
)
from ragdog.core.retrieve import RetrievedChunk


def make_chunk(
    text: str = "Error E2210 means the jar is not seated.", page: int = 3
) -> RetrievedChunk:
    """A RetrievedChunk with defaults for the fields a test doesn't care about."""
    return RetrievedChunk(
        text=text,
        filename="acme-handbook.pdf",
        page=page,
        chunk_index=0,
        doc_hash="h",
        distance=0.2,
    )


def cite(document_index: int, cited_text: str) -> dict[str, Any]:
    """A char_location citation as the API returns it for plain-text documents."""
    return {
        "type": "char_location",
        "cited_text": cited_text,
        "document_index": document_index,
        "document_title": "acme-handbook.pdf p.3",
        "start_char_index": 0,
        "end_char_index": len(cited_text),
    }


def make_response(
    content: list[dict[str, Any]],
    stop_reason: str = "end_turn",
    input_tokens: int = 100,
    output_tokens: int = 20,
) -> Message:
    """A real SDK Message built from plain dicts, the same shape the API sends back."""
    return Message.model_validate(
        {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": "claude-haiku-5-5",
            "content": content,
            "stop_reason": stop_reason,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
        }
    )


class FakeMessages:
    """Stands in for client.messages: records each create() call, returns a canned reply."""

    def __init__(self, response: Message) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Message:
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    """Stands in for anthropic.Anthropic: no network, no key, no cost."""

    def __init__(self, response: Message) -> None:
        self.messages = FakeMessages(response)


# --- document_blocks ---


def test_document_blocks_builds_one_cited_text_document_per_chunk() -> None:
    chunk = make_chunk()
    assert document_blocks([chunk]) == [
        {
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": chunk.text},
            "title": "acme-handbook.pdf p.3",
            "citations": {"enabled": True},
        }
    ]


def test_document_blocks_keeps_retrieval_order() -> None:
    chunks = [make_chunk("first", page=2), make_chunk("second", page=1)]
    blocks = document_blocks(chunks)
    assert [b["source"]["data"] for b in blocks] == ["first", "second"]
    assert [b["title"] for b in blocks] == ["acme-handbook.pdf p.2", "acme-handbook.pdf p.1"]


def test_document_blocks_empty_list_gives_no_blocks() -> None:
    assert document_blocks([]) == []


# --- to_answer ---


def test_to_answer_joins_text_and_maps_citations_to_chunks() -> None:
    source = "Error E4012 means the motor overheated."
    chunks = [make_chunk(source, page=3), make_chunk("Price list.", page=2)]
    response = make_response(
        [
            {"type": "text", "text": "Error E4012 means "},
            {"type": "text", "text": "the motor has overheated", "citations": [cite(0, source)]},
            {"type": "text", "text": "."},
        ],
        input_tokens=120,
        output_tokens=35,
    )
    answer = to_answer(response, chunks)
    assert answer.text == "Error E4012 means the motor has overheated."
    assert len(answer.citations) == 1
    assert answer.citations[0].chunk is chunks[0]
    assert answer.citations[0].cited_text == source
    assert (answer.input_tokens, answer.output_tokens) == (120, 35)


def test_to_answer_skips_thinking_blocks() -> None:
    response = make_response(
        [
            {"type": "thinking", "thinking": "The jar code is on page 3.", "signature": "sig"},
            {"type": "text", "text": "The jar is not seated."},
        ]
    )
    assert to_answer(response, [make_chunk()]).text == "The jar is not seated."


def test_to_answer_keeps_citations_in_answer_order() -> None:
    chunks = [make_chunk("A.", page=1), make_chunk("B.", page=2)]
    response = make_response(
        [
            {"type": "text", "text": "From B", "citations": [cite(1, "B.")]},
            {"type": "text", "text": " and from A", "citations": [cite(0, "A.")]},
        ]
    )
    assert [c.chunk.page for c in to_answer(response, chunks).citations] == [2, 1]


def test_to_answer_with_no_citations_gives_empty_list() -> None:
    response = make_response([{"type": "text", "text": "The documents don't say."}])
    assert to_answer(response, [make_chunk()]).citations == []


def test_to_answer_rejects_citation_outside_the_chunks_sent() -> None:
    response = make_response([{"type": "text", "text": "Hm", "citations": [cite(5, "x")]}])
    with pytest.raises(GenerationError, match="document 5"):
        to_answer(response, [make_chunk()])


# --- generate_answer ---


def test_generate_answer_sends_settings_from_config() -> None:
    client = FakeClient(make_response([{"type": "text", "text": "Ok."}]))
    generate_answer("What does E2210 mean?", [make_chunk()], client=client)
    [call] = client.messages.calls
    assert call["model"] == LLM_MODEL
    assert call["max_tokens"] == LLM_MAX_TOKENS
    assert call["output_config"] == {"effort": LLM_EFFORT}
    assert call["system"] == SYSTEM_PROMPT


def test_generate_answer_sends_documents_then_question_in_one_user_turn() -> None:
    chunks = [make_chunk("A.", page=1), make_chunk("B.", page=2)]
    client = FakeClient(make_response([{"type": "text", "text": "Ok."}]))
    generate_answer("What does E2210 mean?", chunks, client=client)
    [message] = client.messages.calls[0]["messages"]
    assert message["role"] == "user"
    assert message["content"] == [
        *document_blocks(chunks),
        {"type": "text", "text": "What does E2210 mean?"},
    ]


def test_generate_answer_returns_the_parsed_answer() -> None:
    chunk = make_chunk()
    reply = {"type": "text", "text": "The jar is loose.", "citations": [cite(0, chunk.text)]}
    client = FakeClient(make_response([reply]))
    answer = generate_answer("What does E2210 mean?", [chunk], client=client)
    assert answer.text == "The jar is loose."
    assert answer.citations[0].chunk is chunk
