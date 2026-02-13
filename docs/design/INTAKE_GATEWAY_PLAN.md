# Intake Gateway Implementation Plan

**Version:** 1.0  
**Created:** 2026-02-11  
**Requirement traceability:** IMPL-03  
**References:** [PRD.md](PRD.md) Section 2.1 (Phase A), Section 5.4 (Intake API), Appendix C; [DOCUMENT_SAFETY.md](DOCUMENT_SAFETY.md) Section 3; [AUDIT_ARCHITECTURE.md](AUDIT_ARCHITECTURE.md) Section 1.2; [TECH_DECISIONS.md](TECH_DECISIONS.md); [FOUNDATION_LAYER_PLAN.md](FOUNDATION_LAYER_PLAN.md); [STORAGE_LAYER_PLAN.md](STORAGE_LAYER_PLAN.md)

---

## Document Conventions

| Notation | Meaning |
|----------|---------|
| `{tenant_id}` | Tenant identifier from JWT |
| `{file_id}` | File identifier from manifest |
| `{sha256}` | SHA-256 hash of file content |

**Trust boundary:** The intake gateway is the first contact point with untrusted documents. All validation must complete before any document content reaches downstream components.

---

## 1. Overview

The intake gateway accepts vendor batch uploads (manifest + files), validates each file (MIME, size, checksum, malware), stores accepted files in the object store, generates immutable receipts, emits audit events, and enqueues parse jobs. Rejected or quarantined files are not processed further.

**Cross-references:** PRD Section 2.1 (flow), Section 5.4 (API); DOCUMENT_SAFETY Section 3 (MIME verification).

---

## 2. Request Flow (Step-by-Step)

### 2.1 Pre-Request

| Step | Action | On Failure |
|------|--------|------------|
| 1 | **TLS termination** — All connections must be HTTPS. Reject unencrypted. | 403 FORBIDDEN |
| 2 | **JWT validation** — Extract `tenant_id` from token claims. Verify token signature, expiration, issuer. Verify `tenant_id` in path matches token. | 401 AUTHENTICATION_REQUIRED or 401 TOKEN_EXPIRED |
| 3 | **Scope check** — Token must have `ingest` scope. | 403 INSUFFICIENT_PERMISSIONS |
| 4 | **Tenant state** — Tenant must be ACTIVE. Reject if SUSPENDED. | 403 TENANT_SUSPENDED |
| 5 | **Rate limit** — 100 requests/minute per tenant. Check Redis key `tenant:{tenant_id}:ratelimit:ingest`. | 429 RATE_LIMIT_EXCEEDED |

### 2.2 Manifest Validation

| Step | Action | On Failure |
|------|--------|------------|
| 6 | **Parse manifest** — Extract `manifest` part from multipart form. Parse as JSON. | 400 MANIFEST_INVALID |
| 7 | **Required fields** — `batch_id`, `tenant_id`, `file_count`, `files[]`. Each file: `file_id`, `filename`, `mime_type`, `size_bytes`, `sha256`. | 400 MANIFEST_INVALID |
| 8 | **File count match** — `len(files[])` must equal `file_count`. Number of uploaded files must equal `file_count`. | 400 MANIFEST_FILE_COUNT_MISMATCH |
| 9 | **No duplicate file_ids** — All `file_id` values in manifest must be unique. | 400 DUPLICATE_FILE_ID |
| 10 | **Tenant match** — Manifest `tenant_id` must equal path `tenant_id` and JWT `tenant_id`. | 400 MANIFEST_INVALID |

**Manifest schema (reference PRD Section 2.1):**

```json
{
  "batch_id": "batch_2026-02-08_001",
  "tenant_id": "tenant_abc",
  "file_count": 3,
  "files": [
    {
      "file_id": "file_001",
      "filename": "contract_2024.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 2457600,
      "sha256": "a1b2c3d4e5f67890..."
    }
  ],
  "submitted_at": "2026-02-08T14:00:00Z",
  "submitter": "dana@vendor.example.com"
}
```

### 2.3 Per-File Processing Loop

For each file in the manifest, execute in order:

| Step | Action | On Failure |
|------|--------|------------|
| 11 | **MIME type check** — Use python-magic (libmagic) to sniff actual content type. Compare against tenant `mime_allowlist` (from FOUNDATION_LAYER_PLAN, load_tenant_config). If declared_mime provided and differs from sniffed, reject (possible spoofing). **Reference:** DOCUMENT_SAFETY Section 3.2–3.5 | Reject file; reason UNSUPPORTED_FORMAT |
| 12 | **Size check** — File size must be <= `config.max_file_size_mb` (default 500 MB). | Reject file; reason SIZE_EXCEEDED |
| 13 | **Checksum verification** — Compute SHA-256 of file bytes. Compare with manifest `sha256`. Must match exactly. | Reject file; reason CHECKSUM_MISMATCH |
| 14 | **Malware scan** — Send file to ClamAV via clamd socket. Use `clamd.instream` or equivalent. Quarantine if scan returns infected. **Reference:** TECH_DECISIONS #32 (ClamAV sidecar) | Quarantine file; reason MALWARE_DETECTED |
| 15 | **Write to object store** — Path: `raw/{tenant_id}/{file_id}/{sha256}`. Use tenant MinIO credentials from STORAGE_LAYER_PLAN. | 500 INTERNAL_ERROR |
| 16 | **Generate intake receipt** — Create immutable receipt (schema below). Store in relational DB or receipt store. | 500 INTERNAL_ERROR |
| 17 | **Emit audit event** — DOCUMENT_INGESTED with details (sha256, mime_type, storage_path). **Reference:** AUDIT_ARCHITECTURE Section 1.2 | — |
| 18 | **Enqueue parse job** — Add job to tenant parse queue (Redis/Celery): `tenant:{tenant_id}:queue:parse`. Payload: `{file_id, batch_id, sha256, storage_path}`. | — |

**Reject path:** Emit DOCUMENT_REJECTED with `details.reason` = UNSUPPORTED_FORMAT | SIZE_EXCEEDED | CHECKSUM_MISMATCH. Do not write to object store. Do not enqueue.

**Quarantine path:** Store file in quarantine path `quarantine/{tenant_id}/{file_id}/{sha256}` (optional; or discard). Emit DOCUMENT_QUARANTINED with `details.scan_engine`, `details.threat_name`. Do not enqueue.

### 2.4 Batch Completion

| Step | Action |
|------|--------|
| 19 | **Emit BATCH_RECEIVED** — At start of processing (after manifest valid). Resource: batch. |
| 20 | **Return batch receipt** — 202 Accepted. Aggregate accepted, rejected, quarantined counts. Include receipts array, rejected_files, quarantined_files with reason and message. |

---

## 3. API Endpoint Definitions

### 3.1 POST /api/v1/ingest/{tenant_id}/batch

**Purpose:** Submit a document batch for ingestion.

**Auth:** Bearer JWT. Token must contain `tenant_id` matching path. Token must have `ingest` scope.

**Rate limit:** 100 req/min per tenant.

**Request:** `multipart/form-data`

| Part | Type | Required | Description |
|------|------|----------|-------------|
| `manifest` | application/json | Yes | Batch manifest (schema above) |
| `files` | binary (multiple) | Yes | Document files. Order must match manifest `files[]` order, or each file part must have `file_id` in Content-Disposition. |

**Success response (202 Accepted):**

```json
{
  "success": true,
  "data": {
    "batch_id": "batch_2026-02-08_001",
    "tenant_id": "tenant_abc",
    "file_count": 10,
    "accepted": 8,
    "rejected": 1,
    "quarantined": 1,
    "receipts": [
      {
        "receipt_id": "01957a3c-8b2e-7000-a000-000000000002",
        "file_id": "file_001",
        "status": "accepted"
      }
    ],
    "rejected_files": [
      {
        "file_id": "file_003",
        "reason": "CHECKSUM_MISMATCH",
        "message": "Expected SHA-256 a1b2... but computed c3d4..."
      }
    ],
    "quarantined_files": [
      {
        "file_id": "file_007",
        "reason": "MALWARE_DETECTED",
        "message": "Malware scan flagged: Trojan.PDF-123"
      }
    ],
    "received_at": "2026-02-08T14:30:05Z"
  }
}
```

### 3.2 GET /api/v1/ingest/{tenant_id}/batch/{batch_id}

**Purpose:** Get current status of a batch, including per-file stage progress.

**Auth:** Bearer JWT, `ingest` scope.

**Rate limit:** 100 req/min per tenant.

**Success response (200 OK):**

```json
{
  "success": true,
  "data": {
    "batch_id": "batch_2026-02-08_001",
    "tenant_id": "tenant_abc",
    "status": "processing",
    "submitted_at": "2026-02-08T14:30:00Z",
    "updated_at": "2026-02-08T14:35:00Z",
    "summary": {
      "total_files": 10,
      "completed": 6,
      "processing": 2,
      "queued": 1,
      "failed": 1
    },
    "files": [
      {
        "file_id": "file_001",
        "original_filename": "contract_2024.pdf",
        "stages": {
          "intake": "completed",
          "parse": "completed",
          "policy": "queued",
          "embed": "queued",
          "index": "queued"
        },
        "current_stage": "parse",
        "error": null
      }
    ]
  }
}
```

### 3.3 GET /api/v1/ingest/{tenant_id}/receipt/{receipt_id}

**Purpose:** Get individual intake receipt for a file.

**Auth:** Bearer JWT, `ingest` scope.

**Rate limit:** 100 req/min per tenant.

**Success response (200 OK):**

```json
{
  "success": true,
  "data": {
    "receipt_id": "01957a3c-8b2e-7000-a000-000000000002",
    "tenant_id": "tenant_abc",
    "batch_id": "batch_2026-02-08_001",
    "file_id": "file_001",
    "original_filename": "contract_2024.pdf",
    "mime_type": "application/pdf",
    "size_bytes": 2457600,
    "sha256": "a1b2c3d4e5f67890...",
    "scan_result": "clean",
    "received_at": "2026-02-08T14:30:00Z",
    "storage_path": "raw/tenant_abc/file_001/a1b2c3d4e5f67890",
    "status": "accepted"
  }
}
```

---

## 4. Error Response Format

All error responses use this structure:

```json
{
  "success": false,
  "error": {
    "code": "MANIFEST_INVALID",
    "message": "Manifest JSON is malformed or missing required fields",
    "details": {}
  }
}
```

**Error codes by endpoint:**

| Status | Code | Condition |
|--------|------|-----------|
| 400 | MANIFEST_INVALID | Manifest JSON malformed or missing required fields |
| 400 | MANIFEST_FILE_COUNT_MISMATCH | File count in manifest does not match uploaded files |
| 400 | DUPLICATE_FILE_ID | Manifest contains duplicate file IDs |
| 401 | AUTHENTICATION_REQUIRED | Missing or invalid JWT |
| 401 | TOKEN_EXPIRED | JWT has expired |
| 403 | INSUFFICIENT_PERMISSIONS | Token does not have ingest scope |
| 403 | TENANT_SUSPENDED | Tenant is suspended |
| 404 | RESOURCE_NOT_FOUND | Batch ID or receipt ID does not exist for tenant |
| 429 | RATE_LIMIT_EXCEEDED | Intake rate limit exceeded |
| 500 | INTERNAL_ERROR | Server error during processing |
| 503 | SERVICE_UNAVAILABLE | ClamAV or object store unavailable |

**Per-file reject reasons (in batch receipt):**

| Reason | Description |
|--------|-------------|
| UNSUPPORTED_FORMAT | MIME type not on allowlist (DOCUMENT_SAFETY Section 3) |
| SIZE_EXCEEDED | File exceeds max_file_size_mb |
| CHECKSUM_MISMATCH | Computed SHA-256 does not match manifest |
| MALWARE_DETECTED | ClamAV flagged file (quarantined, not rejected) |

---

## 5. MIME Verification (DOCUMENT_SAFETY Section 3)

**Library:** python-magic >=0.4.27 (libmagic)

**Order:** After manifest validation, before checksum and malware scan.

**Flow:**

1. Sniff MIME: `magic.from_file(file_path, mime=True)` or `magic.from_buffer(bytes, mime=True)`
2. Check sniffed MIME against tenant `mime_allowlist` (from tenants.config, PRD Appendix G)
3. If manifest declares `mime_type` and it differs from sniffed, reject (possible extension spoofing)
4. Allowlist default (PRD Appendix C): application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, text/plain, text/csv, image/png, image/tiff

**Reject response (UNSUPPORTED_FORMAT):**

```json
{
  "success": false,
  "error": {
    "code": "UNSUPPORTED_FORMAT",
    "message": "MIME type application/octet-stream is not on the allowlist.",
    "details": {
      "field": "files[0]",
      "declared_mime": "application/pdf",
      "sniffed_mime": "application/octet-stream"
    }
  }
}
```

---

## 6. Audit Events

**Reference:** AUDIT_ARCHITECTURE Section 1, Section 1.2.

| Event Type | Trigger | resource_type | resource_id | Key details |
|------------|---------|---------------|-------------|-------------|
| BATCH_RECEIVED | Batch submission begins (after manifest valid) | batch | batch_id | file_count, submitter |
| DOCUMENT_INGESTED | File passes all checks, stored | document | file_id | sha256, mime_type, storage_path |
| DOCUMENT_REJECTED | File fails MIME/size/checksum | document | file_id | reason, failed_check |
| DOCUMENT_QUARANTINED | Malware scan flags file | document | file_id | scan_engine, threat_name |

**Emission pattern:** Use `emit_audit_event()` from FOUNDATION_LAYER_PLAN. Set `component: "intake-gateway"`.

---

## 7. Integration Points

| Service | Purpose |
|---------|---------|
| **MinIO** | Store raw files at `raw/{tenant_id}/{file_id}/{sha256}`. Tenant bucket per STORAGE_LAYER_PLAN. |
| **ClamAV** | clamd socket. Scan file before storage. TECH_DECISIONS #32. |
| **Redis** | Rate limit key `tenant:{tenant_id}:ratelimit:ingest`. Parse queue `tenant:{tenant_id}:queue:parse`. |
| **Celery** | Parse job payload: `{file_id, batch_id, sha256, storage_path, tenant_id}`. |
| **PostgreSQL** | Store intake receipts. Batch status. |
| **Audit store** | emit_audit_event() writes to audit_events. |

---

## 8. Receipt Schema (Pydantic-Ready)

```python
class IntakeReceipt(BaseModel):
    receipt_id: str  # UUID v7
    tenant_id: str
    batch_id: str
    file_id: str
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    scan_result: Literal["clean", "quarantined", "skipped"]
    received_at: datetime
    storage_path: str
    status: Literal["accepted", "rejected", "quarantined"]
```

---

## 9. Implementation Checklist

- [ ] JWT validation (python-jose, extract tenant_id, scope check)
- [ ] Rate limiting (Redis, 100/min per tenant)
- [ ] Manifest validation (JSON parse, file count, duplicate file_ids)
- [ ] MIME verification (python-magic, tenant mime_allowlist)
- [ ] Checksum (hashlib.sha256)
- [ ] ClamAV integration (clamd socket or pyclamd)
- [ ] MinIO write (raw/{tenant_id}/{file_id}/{sha256})
- [ ] Receipt generation and storage
- [ ] Audit event emission (BATCH_RECEIVED, DOCUMENT_INGESTED, DOCUMENT_REJECTED, DOCUMENT_QUARANTINED)
- [ ] Celery/Redis parse job enqueue
- [ ] Batch status and receipt GET endpoints
