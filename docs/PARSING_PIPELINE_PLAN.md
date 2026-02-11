# Parsing Pipeline Implementation Plan

**Version:** 1.0  
**Created:** 2026-02-11  
**Requirement traceability:** IMPL-04  
**References:** [PRD.md](PRD.md) Section 2.2 (Phase B), Appendix C; [TECH_DECISIONS.md](TECH_DECISIONS.md) Components 3, 4, 10; [AUDIT_ARCHITECTURE.md](AUDIT_ARCHITECTURE.md) Section 1.2; [STORAGE_LAYER_PLAN.md](STORAGE_LAYER_PLAN.md)

---

## Document Conventions

| Notation | Meaning |
|----------|---------|
| `{tenant_id}` | Tenant identifier |
| `{file_id}` | File identifier from intake receipt |
| `{doc_id}` | Document identifier (UUID v7 or deterministic from file_id) |
| `{sha256}` | SHA-256 of raw file content |

**Input:** Raw files from object store at `raw/{tenant_id}/{file_id}/{sha256}`. Intake receipt provides file_id, sha256, mime_type, storage_path.

**Output:** Canonical structured document JSON at `normalized/{tenant_id}/{doc_id}/structured.json`.

---

## 1. Overview

The parsing pipeline transforms raw documents into a canonical structured representation through three stages: (1) Layout-aware conversion (Docling), (2) Partitioning and chunking (Unstructured), (3) Canonical JSON assembly and storage. Supported formats: PDF, DOCX, XLSX, TXT, CSV, PNG, TIFF (PRD Appendix C).

**Reference:** PRD Section 2.2.

---

## 2. Job Input

Parse jobs are enqueued by the intake gateway. Payload:

```json
{
  "file_id": "file_001",
  "batch_id": "batch_2026-02-08_001",
  "sha256": "a1b2c3d4e5f67890...",
  "storage_path": "raw/tenant_abc/file_001/a1b2c3d4e5f67890",
  "tenant_id": "tenant_abc",
  "mime_type": "application/pdf"
}
```

**Idempotency:** If canonical JSON already exists at `normalized/{tenant_id}/{doc_id}/structured.json` with `lineage.raw_sha256` matching job sha256 and parser versions matching current, skip reprocessing.

---

## 3. Stage 1: Layout-Aware Conversion (Docling)

**Library:** Docling >=2.70 (TECH_DECISIONS #3)

**Purpose:** Extract document structure—sections, tables, figures, reading order, page-level offsets—without partitioning into chunks.

### 3.1 Supported Formats

| Format | MIME | Docling/Unstructured Handling |
|--------|------|------------------------------|
| PDF | application/pdf | Native text extraction or OCR for scanned |
| DOCX | application/vnd.openxmlformats-officedocument.wordprocessingml.document | XML parsing, heading hierarchy |
| XLSX | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet | Sheet as section |
| TXT | text/plain | Line-based structure |
| CSV | text/csv | Single table |
| PNG | image/png | OCR (single page) |
| TIFF | image/tiff | OCR (multi-page) |

### 3.2 Output (Stage 1 Intermediate)

| Field | Type | Description |
|-------|------|-------------|
| sections | list | section_id, title, level, page, start_char, end_char |
| tables | list | table_id, page, rows, columns, cells[][], start_char, end_char |
| figures | list | figure_id, page, caption, start_char, end_char |
| reading_order | list | Ordered IDs (sec_001, tbl_001, sec_002, fig_001) |

### 3.3 OCR Fallback

For scanned documents (PNG, TIFF, image-heavy PDF): Apply OCR. Record per-page confidence. If `ocr_avg_confidence < 0.7`, flag in stats. Low-confidence pages included in acceptance report.

### 3.4 Docling Usage Pattern

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert(input_path)
# Extract layout elements from result
```

Exact API depends on Docling 2.70+; consult library docs. Output must provide sections, tables, figures with page and character offsets.

---

## 4. Stage 2: Partitioning and Chunking (Unstructured)

**Library:** Unstructured >=0.16 (TECH_DECISIONS #4)

**Purpose:** Partition Stage 1 output into discrete elements (paragraphs, table rows, list items, headings), apply structure-aware chunking, generate deterministic chunk IDs.

### 4.1 Chunking Strategy

**Strategy:** `by_title` — Chunk boundaries respect document structure. Section breaks and heading changes create new chunks. Tables are never split across chunks. List items are kept together.

### 4.2 Deterministic Chunk ID

```
chunk_id = sha256(f"{doc_id}|{page}|{start_char}|{end_char}")[:16]  # or full hex
```

Alternative: `chk_` + first 12 chars of hash. Same document processed multiple times must produce identical chunk_ids.

### 4.3 Element Types

| element_type | Description |
|--------------|-------------|
| paragraph | Text paragraph |
| table | Table (entire table as one chunk or per-row based on size) |
| heading | Section heading |
| list_item | List item |
| figure_caption | Figure caption text |

### 4.4 Chunk Metadata

Per chunk:
- `section_title` — Parent section title
- `heading_level` — If applicable
- `element_type` — One of above

### 4.5 Unstructured Usage Pattern

```python
from unstructured.partition.auto import partition

elements = partition(filename=path, strategy="hi_res")
# Apply chunking strategy, assign chunk_ids
```

Unstructured produces elements; apply `by_title` grouping. Merge with Stage 1 layout for reading_order and structure.

---

## 5. Stage 3: Canonical JSON Assembly

### 5.1 Merge and Write

1. Merge Stage 1 layout (sections, tables, figures, reading_order) with Stage 2 chunks
2. Assign doc_id (UUID v7 or deterministic: `doc_` + first 12 of sha256(file_id))
3. Populate lineage object
4. Populate stats object
5. Write to `normalized/{tenant_id}/{doc_id}/structured.json`

### 5.2 Lineage Object

```json
{
  "raw_sha256": "a1b2c3d4e5f67890...",
  "stage1_parser_version": "2.70.0",
  "stage2_parser_version": "0.16.0",
  "parse_timestamp": "2026-02-08T14:35:00Z"
}
```

**Purpose:** Reproducibility. Same raw file + same parser versions = identical output.

### 5.3 Stats Object

```json
{
  "page_count": 42,
  "section_count": 15,
  "table_count": 8,
  "figure_count": 3,
  "chunk_count": 127,
  "total_characters": 98500,
  "ocr_pages": 0,
  "ocr_avg_confidence": null,
  "dropped_content": []
}
```

**dropped_content:** List of `{element_type, page, reason}` for CONTENT_DROPPED audit events.

---

## 6. Canonical JSON Schema (Pydantic-Ready)

### 6.1 Root Model

```python
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

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
```

### 6.2 Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| doc_id | string | Yes | Unique document identifier |
| file_id | string | Yes | Reference to intake receipt file_id |
| tenant_id | string | Yes | Tenant that owns this document |
| sections | array | No | Document sections with titles, levels, offsets |
| tables | array | No | Extracted tables with row/column structure |
| figures | array | No | Detected figures with captions |
| reading_order | array | No | Ordered IDs reflecting document flow |
| chunks | array | Yes | Chunked content with text, offsets, metadata |
| chunks[].chunk_id | string | Yes | Deterministic ID |
| chunks[].element_type | string | Yes | paragraph, table, heading, list_item, figure_caption |
| lineage | object | Yes | raw_sha256, parser versions, timestamp |
| stats | object | Yes | Extraction statistics |

---

## 7. Parse Failure Reporting

### 7.1 DOCUMENT_PARSE_FAILED

**Trigger:** Entire file cannot be parsed.

| Reason | Description |
|--------|-------------|
| FILE_CORRUPTED | File cannot be opened or read |
| UNSUPPORTED_FORMAT | Parser does not support this format (should not occur if intake MIME passed) |
| OCR_FAILED | OCR could not extract text from scanned pages |
| PARSER_ERROR | Docling or Unstructured raised exception |

**Action:** Emit DOCUMENT_PARSE_FAILED audit event. Mark document as parse_failed in batch status. Do not write canonical JSON. Do not enqueue policy job. Include in acceptance report.

### 7.2 CONTENT_DROPPED

**Trigger:** Some elements could not be extracted (e.g., complex table, damaged region).

**Action:** Record in stats.dropped_content. Emit CONTENT_DROPPED per dropped element (or one aggregate event). Continue with extractable content. Acceptance report includes dropped content details.

### 7.3 Acceptance Report Integration

Batch status API (`GET /api/v1/ingest/{tenant_id}/batch/{batch_id}`) includes per-file stages. Parse stage shows:
- `completed` — Canonical JSON written
- `failed` — DOCUMENT_PARSE_FAILED, error message in file detail
- `processing` / `queued` — In progress

---

## 8. Audit Events

**Reference:** AUDIT_ARCHITECTURE Section 1.2.

| Event Type | Trigger | resource_type | resource_id | Key details |
|------------|---------|---------------|-------------|-------------|
| DOCUMENT_PARSED | Canonical JSON successfully written | document | doc_id | chunk_count, page_count, parser_versions |
| DOCUMENT_PARSE_FAILED | Parsing failed for entire document | document | file_id | failure_reason, parser_versions |
| CONTENT_DROPPED | Extractable content was dropped | document | doc_id | dropped_element_type, page, reason |

---

## 9. Job Enqueue (Downstream)

After successful parse, enqueue policy check job:

```json
{
  "doc_id": "doc_01957a3c",
  "file_id": "file_001",
  "tenant_id": "tenant_abc",
  "storage_path": "normalized/tenant_abc/doc_01957a3c/structured.json"
}
```

Queue: `tenant:{tenant_id}:queue:policy`

---

## 10. Storage Paths

| Path | Contents |
|------|----------|
| `raw/{tenant_id}/{file_id}/{sha256}` | Raw uploaded file (from intake) |
| `normalized/{tenant_id}/{doc_id}/structured.json` | Canonical structured document JSON |

**Reference:** STORAGE_LAYER_PLAN (MinIO bucket per tenant).

---

## 11. Offline vs Online Mode

Parsing pipeline is identical in both modes. Docling and Unstructured run in-process or in same worker container. No external API calls during parsing. OCR uses local models if needed (Tesseract or equivalent bundled in offline image).

---

## 12. Implementation Checklist

- [ ] Parse job handler (receive from Celery/Redis)
- [ ] Idempotency check (skip if canonical exists with same lineage)
- [ ] Stage 1: Docling integration (layout extraction)
- [ ] Stage 2: Unstructured integration (partition + chunk)
- [ ] Deterministic chunk_id generation
- [ ] Stage 3: Canonical JSON assembly (Pydantic model)
- [ ] Object store write (normalized path)
- [ ] Audit events (DOCUMENT_PARSED, DOCUMENT_PARSE_FAILED, CONTENT_DROPPED)
- [ ] Policy job enqueue
- [ ] Batch status update (parse stage completion/failure)
- [ ] OCR path for scanned documents
- [ ] Parse failure handling and error reporting
