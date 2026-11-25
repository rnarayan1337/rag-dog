"""Tests for ragdog.core.ingest."""

import hashlib
from pathlib import Path

import pytest
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

from ragdog.core.config import CHUNK_OVERLAP, CHUNK_SIZE, COLLECTION, EMBEDDING_MODEL
from ragdog.core.ingest import (
    HASH_BLOCK_SIZE,
    DocumentInfo,
    already_ingested,
    chunk_pages,
    get_collection,
    hash_file,
    ingest_file,
    list_documents,
    read_document,
    split_text,
    upsert_chunks,
)


def test_hash_file_same_bytes_same_hash(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "renamed.txt"
    a.write_bytes(b"hello rag-dog")
    b.write_bytes(b"hello rag-dog")
    assert hash_file(str(a)) == hash_file(str(b))


def test_hash_file_different_bytes_different_hash(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_bytes(b"hello rag-dog")
    b.write_bytes(b"hello rag-cat")
    assert hash_file(str(a)) != hash_file(str(b))


def test_hash_file_spanning_blocks_matches_whole_file_hash(tmp_path: Path) -> None:
    data = b"x" * (HASH_BLOCK_SIZE * 2 + 123)  # forces 3 reads, last one partial
    path = tmp_path / "big.bin"
    path.write_bytes(data)
    assert hash_file(str(path)) == hashlib.sha256(data).hexdigest()


def test_get_collection_uses_cosine_and_configured_model(tmp_path: Path) -> None:
    col = get_collection(str(tmp_path))
    assert col.name == COLLECTION
    assert col.configuration["hnsw"]["space"] == "cosine"
    assert ONNXMiniLM_L6_V2.MODEL_NAME == EMBEDDING_MODEL  # rule 4: one model


def test_get_collection_persists_across_clients(tmp_path: Path) -> None:
    get_collection(str(tmp_path)).add(ids=["x"], documents=["hi"], embeddings=[[0.0] * 384])
    assert get_collection(str(tmp_path)).count() == 1


def test_already_ingested_true_only_for_stored_hash(tmp_path: Path) -> None:
    col = get_collection(str(tmp_path))
    assert not already_ingested(col, "abc")
    col.add(
        ids=["abc:0"],
        documents=["chunk"],
        embeddings=[[0.0] * 384],
        metadatas=[{"doc_hash": "abc"}],
    )
    assert already_ingested(col, "abc")
    assert not already_ingested(col, "def")


@pytest.mark.parametrize("name", ["notes.txt", "README.md", "SHOUTY.TXT"])
def test_read_document_text_files_are_one_page(tmp_path: Path, name: str) -> None:
    path = tmp_path / name
    path.write_text("# Title\n\nFirst paragraph.\n\nSecond — with a dash.", encoding="utf-8")
    assert read_document(str(path)) == [(1, "# Title\n\nFirst paragraph.\n\nSecond — with a dash.")]


@pytest.mark.parametrize("name", ["report.docx", "no_extension"])
def test_read_document_rejects_unsupported_types(tmp_path: Path, name: str) -> None:
    path = tmp_path / name
    path.write_bytes(b"whatever")
    with pytest.raises(ValueError, match="Unsupported file type"):
        read_document(str(path))


SAMPLE_PDF = Path(__file__).parent / "fixtures" / "sample-3-pages.pdf"


def test_read_document_pdf_keeps_page_numbers() -> None:
    pages = read_document(str(SAMPLE_PDF))
    assert [number for number, _ in pages] == [1, 2, 3]
    assert "Bulldogs were bred in England." in pages[0][1]
    assert "Retrieval finds the chunks." in pages[1][1]  # "ﬁ" ligature normalised
    assert "Generation writes the answer." in pages[1][1]
    assert "Citations name the page." in pages[2][1]


def make_text(paragraphs: int, sentences: int) -> str:
    """Numbered sentences grouped into paragraphs, so every word is traceable."""
    return "\n\n".join(
        " ".join(f"Paragraph {p} sentence {s} is about bulldogs." for s in range(sentences))
        for p in range(paragraphs)
    )


def test_split_text_loses_nothing() -> None:
    text = make_text(paragraphs=5, sentences=30)  # paragraphs longer than CHUNK_SIZE
    pieces = split_text(text, CHUNK_SIZE)
    assert "".join(pieces) == text
    assert all(len(piece) <= CHUNK_SIZE for piece in pieces)


def test_split_text_hard_cuts_text_with_no_spaces() -> None:
    pieces = split_text("a" * 2000, 800)
    assert [len(piece) for piece in pieces] == [800, 800, 400]


def test_chunk_pages_short_page_is_one_chunk() -> None:
    assert chunk_pages([(1, "Just one line.")]) == [(1, 0, "Just one line.")]


def test_chunk_pages_skips_empty_pages() -> None:
    assert chunk_pages([(1, ""), (2, "   \n\n "), (3, "Hi.")]) == [(3, 0, "Hi.")]


def test_chunk_pages_size_limit_and_overlap() -> None:
    text = make_text(paragraphs=8, sentences=12)
    chunks = [chunk for _, _, chunk in chunk_pages([(1, text)])]
    assert len(chunks) > 3
    assert all(len(chunk) <= CHUNK_SIZE for chunk in chunks)
    for previous, current in zip(chunks, chunks[1:]):
        shared = current[:50]
        assert shared in previous[-CHUNK_OVERLAP:]  # next chunk starts with prev's tail


def test_chunk_pages_keeps_every_sentence() -> None:
    text = make_text(paragraphs=8, sentences=12)
    joined = " ".join(chunk for _, _, chunk in chunk_pages([(1, text)]))
    for p in range(8):
        for s in range(12):
            assert f"Paragraph {p} sentence {s} is about bulldogs." in joined


def test_chunk_pages_page_numbers_and_global_index() -> None:
    long_page = make_text(paragraphs=4, sentences=12)
    chunks = chunk_pages([(1, long_page), (2, "Short page two."), (3, long_page)])
    assert [index for _, index, _ in chunks] == list(range(len(chunks)))
    assert [text for page, _, text in chunks if page == 2] == ["Short page two."]
    pages = [page for page, _, _ in chunks]
    assert pages == sorted(pages) and set(pages) == {1, 2, 3}


CHUNKS = [(1, 0, "First chunk."), (1, 1, "Second chunk."), (2, 2, "Third, on page two.")]


def test_upsert_chunks_stores_ids_text_and_metadata(fake_collection: Collection) -> None:
    stored = upsert_chunks(fake_collection, CHUNKS, "abc", "uploads/report.pdf")
    assert stored == 3
    record = fake_collection.get(ids=["abc:2"], include=["documents", "metadatas"])
    assert record["documents"] == ["Third, on page two."]
    assert record["metadatas"] == [
        {
            "doc_hash": "abc",
            "filename": "report.pdf",
            "file_location": "uploads/report.pdf",
            "chunk_index": 2,
            "page": 2,
            "embedding_model": EMBEDDING_MODEL,
        }
    ]


def test_upsert_chunks_file_location_overrides_path(fake_collection: Collection) -> None:
    upsert_chunks(fake_collection, CHUNKS, "abc", "/tmp/xyz/report.pdf", file_location="report.pdf")
    stored = fake_collection.get(include=["metadatas"])
    assert {meta["file_location"] for meta in stored["metadatas"]} == {"report.pdf"}
    assert {meta["filename"] for meta in stored["metadatas"]} == {"report.pdf"}


def test_upsert_chunks_twice_does_not_duplicate(fake_collection: Collection) -> None:
    upsert_chunks(fake_collection, CHUNKS, "abc", "report.pdf")
    upsert_chunks(fake_collection, CHUNKS, "abc", "report.pdf")
    assert fake_collection.count() == 3


def test_upsert_chunks_in_batches(fake_collection: Collection) -> None:
    many = [(1, i, f"Chunk {i}.") for i in range(7)]
    assert upsert_chunks(fake_collection, many, "abc", "a.txt", batch_size=3) == 7
    assert fake_collection.count() == 7


def test_upsert_chunks_with_nothing_stores_nothing(fake_collection: Collection) -> None:
    assert upsert_chunks(fake_collection, [], "abc", "empty.txt") == 0
    assert fake_collection.count() == 0


def test_ingest_file_twice_stores_once(fake_collection: Collection, tmp_path: Path) -> None:
    path = tmp_path / "notes.md"
    path.write_text(make_text(paragraphs=6, sentences=12), encoding="utf-8")
    first = ingest_file(str(path), fake_collection)
    assert first > 1
    assert ingest_file(str(path), fake_collection) == 0
    assert fake_collection.count() == first


def test_ingest_file_renamed_copy_is_a_duplicate(fake_collection: Collection, tmp_path: Path) -> None:
    original = tmp_path / "notes.txt"
    original.write_text("Same bytes, different name.", encoding="utf-8")
    copy = tmp_path / "copy of notes.txt"
    copy.write_bytes(original.read_bytes())
    assert ingest_file(str(original), fake_collection) == 1
    assert ingest_file(str(copy), fake_collection) == 0
    assert fake_collection.count() == 1


def test_ingest_file_pdf_chunks_carry_page_numbers(fake_collection: Collection) -> None:
    assert ingest_file(str(SAMPLE_PDF), fake_collection) == 3
    stored = fake_collection.get(include=["documents", "metadatas"])
    page_of = {doc: meta["page"] for doc, meta in zip(stored["documents"], stored["metadatas"])}
    assert [page for doc, page in page_of.items() if "Bulldogs" in doc] == [1]
    assert [page for doc, page in page_of.items() if "Retrieval finds" in doc] == [2]
    assert [page for doc, page in page_of.items() if "Citations" in doc] == [3]


def test_ingest_file_unsupported_type_stores_nothing(fake_collection: Collection, tmp_path: Path) -> None:
    path = tmp_path / "slides.pptx"
    path.write_bytes(b"not really slides")
    with pytest.raises(ValueError, match="Unsupported file type"):
        ingest_file(str(path), fake_collection)
    assert fake_collection.count() == 0


def test_ingest_file_records_file_location_not_temp_path(
    fake_collection: Collection, tmp_path: Path
) -> None:
    """What the UI does: ingest a temp copy, record the uploaded file's name."""
    temp_copy = tmp_path / "notes.md"
    temp_copy.write_text(make_text(paragraphs=4, sentences=12), encoding="utf-8")
    assert ingest_file(str(temp_copy), fake_collection, file_location="notes.md") > 1
    stored = fake_collection.get(include=["metadatas"])
    assert {meta["file_location"] for meta in stored["metadatas"]} == {"notes.md"}
    assert {meta["filename"] for meta in stored["metadatas"]} == {"notes.md"}


def test_list_documents_empty_collection(fake_collection: Collection) -> None:
    assert list_documents(fake_collection) == []


def test_list_documents_one_entry_per_document_sorted(fake_collection: Collection) -> None:
    upsert_chunks(fake_collection, CHUNKS, "h1", "zebra.pdf")
    upsert_chunks(fake_collection, CHUNKS[:1], "h2", "apple.txt")
    assert list_documents(fake_collection) == [
        DocumentInfo(filename="apple.txt", doc_hash="h2", chunks=1),
        DocumentInfo(filename="zebra.pdf", doc_hash="h1", chunks=3),
    ]


def test_list_documents_same_filename_different_content(fake_collection: Collection) -> None:
    """Two versions of one file are two documents (decision 006); hash breaks the tie."""
    upsert_chunks(fake_collection, CHUNKS, "bbb", "report.pdf")
    upsert_chunks(fake_collection, CHUNKS[:2], "aaa", "report.pdf")
    assert [(d.doc_hash, d.chunks) for d in list_documents(fake_collection)] == [
        ("aaa", 2),
        ("bbb", 3),
    ]
