"""
Parsing stages per PARSING_PIPELINE_PLAN.
Uses Unstructured for partition + chunk_by_title (handles PDF, DOCX, XLSX, TXT, CSV, images).
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    CanonicalStructuredDocument,
    Chunk,
    ChunkMetadata,
    DroppedContent,
    Lineage,
    Stats,
)


class ParseError(Exception):
    """Raised when parsing fails entirely."""

    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        self.message = message
        super().__init__(f"{reason}: {message}")


def _elem_type_to_canonical(cat: str) -> str:
    m = {
        "Title": "heading",
        "NarrativeText": "paragraph",
        "Text": "paragraph",
        "Table": "table",
        "ListItem": "list_item",
        "Image": "figure_caption",
        "FigureCaption": "figure_caption",
        "Header": "heading",
        "Footer": "paragraph",
        "PageBreak": "paragraph",
        "Address": "paragraph",
        "EmailAddress": "paragraph",
        "UncategorizedText": "paragraph",
    }
    return m.get(cat, "paragraph")


def _chunk_id(doc_id: str, page: int, start: int, end: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{page}|{start}|{end}".encode()).hexdigest()
    return f"chk_{h[:12]}"


def parse_file(
    *,
    input_path: str | Path,
    file_id: str,
    tenant_id: str,
    sha256: str,
    mime_type: str | None = None,
) -> CanonicalStructuredDocument:
    """
    Parse a document file into canonical structured JSON.
    Per PARSING_PIPELINE_PLAN Stages 2–3 (Unstructured partition + chunk, canonical assembly).
    """
    path = Path(input_path)
    if not path.exists():
        raise ParseError("FILE_CORRUPTED", f"File not found: {path}")

    try:
        from unstructured.partition.auto import partition
        from unstructured.chunking.title import chunk_by_title
    except ImportError as e:
        raise ParseError("PARSER_ERROR", f"Unstructured not available: {e}") from e

    # Partition
    try:
        elements = partition(
            filename=str(path),
            strategy="hi_res" if mime_type and "pdf" in (mime_type or "").lower() else "auto",
            infer_table_structure=True,
        )
    except Exception as e:
        raise ParseError("PARSER_ERROR", str(e)) from e

    if not elements:
        raise ParseError("PARSER_ERROR", "No content extracted")

    # Chunk by title (per plan Section 4.1)
    try:
        unstructured_chunks = chunk_by_title(
            elements,
            max_characters=1500,
            new_after_n_chars=1200,
            combine_text_under_n_chars=400,
            multipage_sections=True,
        )
    except Exception as e:
        raise ParseError("PARSER_ERROR", str(e)) from e

    # Doc ID: doc_ + first 12 of sha256(file_id)
    doc_id = f"doc_{hashlib.sha256(file_id.encode()).hexdigest()[:12]}"

    # Map to canonical chunks
    chunks: list[Chunk] = []
    total_chars = 0
    curr_char = 0

    for i, uc in enumerate(unstructured_chunks):
        page = 1
        if hasattr(uc, "metadata") and uc.metadata:
            page = getattr(uc.metadata, "page_number", None) or 1
        text = getattr(uc, "text", "") or str(uc)
        start = curr_char
        end = curr_char + len(text)
        curr_char = end
        total_chars += len(text)

        cat = getattr(uc, "category", None)
        cat_str = getattr(cat, "value", None) or getattr(cat, "name", None) or str(cat) if cat else "UncategorizedText"
        elem_type = _elem_type_to_canonical(cat_str or "UncategorizedText")
        cid = _chunk_id(doc_id, page, start, end)

        meta = ChunkMetadata()
        if hasattr(uc.metadata, "parent_id") and uc.metadata.parent_id:
            meta.section_title = str(uc.metadata.parent_id)[:200]

        chunks.append(
            Chunk(
                chunk_id=cid,
                text=text,
                page=page,
                start_char=start,
                end_char=end,
                element_type=elem_type,
                metadata=meta,
            )
        )

    # Parser versions
    try:
        import unstructured
        unstruct_ver = unstructured.__version__
    except Exception:
        unstruct_ver = "0.16.0"

    lineage = Lineage(
        raw_sha256=sha256,
        stage1_parser_version=unstruct_ver,
        stage2_parser_version=unstruct_ver,
        parse_timestamp=datetime.now(timezone.utc),
    )

    stats = Stats(
        page_count=len(set(c.page for c in chunks)) or 1,
        section_count=0,
        table_count=sum(1 for c in chunks if c.element_type == "table"),
        figure_count=sum(1 for c in chunks if c.element_type == "figure_caption"),
        chunk_count=len(chunks),
        total_characters=total_chars,
    )

    return CanonicalStructuredDocument(
        doc_id=doc_id,
        file_id=file_id,
        tenant_id=tenant_id,
        sections=[],
        tables=[],
        figures=[],
        reading_order=[],
        chunks=chunks,
        lineage=lineage,
        stats=stats,
    )
