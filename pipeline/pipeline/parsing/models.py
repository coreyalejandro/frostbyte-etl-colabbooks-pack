"""
Canonical structured document schema per PARSING_PIPELINE_PLAN Section 6.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Section(BaseModel):
    section_id: str
    title: str
    level: int
    page: int
    start_char: int
    end_char: int


class Table(BaseModel):
    table_id: str
    page: int
    rows: int
    columns: int
    cells: list[list[str]]
    start_char: int
    end_char: int


class Figure(BaseModel):
    figure_id: str
    page: int
    caption: str | None
    start_char: int
    end_char: int


class ChunkMetadata(BaseModel):
    section_title: str | None = None
    heading_level: int | None = None


class Chunk(BaseModel):
    chunk_id: str
    text: str
    page: int
    start_char: int
    end_char: int
    element_type: Literal["paragraph", "table", "heading", "list_item", "figure_caption"]
    metadata: ChunkMetadata = Field(default_factory=ChunkMetadata)


class Lineage(BaseModel):
    raw_sha256: str
    stage1_parser_version: str
    stage2_parser_version: str
    parse_timestamp: datetime


class DroppedContent(BaseModel):
    element_type: str
    page: int
    reason: str


class Stats(BaseModel):
    page_count: int
    section_count: int
    table_count: int
    figure_count: int
    chunk_count: int
    total_characters: int
    ocr_pages: int = 0
    ocr_avg_confidence: float | None = None
    dropped_content: list[DroppedContent] = Field(default_factory=list)


class CanonicalStructuredDocument(BaseModel):
    doc_id: str
    file_id: str
    tenant_id: str
    sections: list[Section] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list)
    reading_order: list[str] = Field(default_factory=list)
    chunks: list[Chunk]
    lineage: Lineage
    stats: Stats
