# Vendor Operations Guide (Dana Persona)

**Version:** 1.0  
**Created:** 2026-02-11  
**Requirement traceability:** USERDOC-01, USERDOC-02, USERDOC-03  
**Audience:** Dana — Vendor Data Operations Lead  
**References:** [PRD.md](PRD.md), [INTAKE_GATEWAY_PLAN.md](INTAKE_GATEWAY_PLAN.md)

---

## 1. Batch Submission

### 1.1 Overview

You submit document batches to Frostbyte using a **manifest** (JSON) plus **files**. Each batch gets a unique `batch_id`. The pipeline validates each file, stores accepted files, and returns a **batch receipt** listing what was accepted, rejected, or quarantined.

### 1.2 Manifest Schema

The manifest is a JSON document with this structure:

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
      "sha256": "a1b2c3d4e5f67890abcdef..."
    },
    {
      "file_id": "file_002",
      "filename": "invoice.xlsx",
      "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "size_bytes": 51200,
      "sha256": "b2c3d4e5f67890abcdef..."
    }
  ],
  "submitted_at": "2026-02-08T14:00:00Z",
  "submitter": "dana@vendor.example.com"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `batch_id` | Yes | Unique batch identifier (e.g., `batch_2026-02-08_001`) |
| `tenant_id` | Yes | Your tenant ID (must match your JWT) |
| `file_count` | Yes | Number of files (must equal `files.length`) |
| `files` | Yes | Array of file entries |
| `files[].file_id` | Yes | Unique ID for this file within the batch |
| `files[].filename` | Yes | Original filename |
| `files[].mime_type` | Yes | MIME type (e.g., `application/pdf`) |
| `files[].size_bytes` | Yes | File size in bytes |
| `files[].sha256` | Yes | SHA-256 hash of file content (64 hex chars) |
| `submitted_at` | No | Timestamp (ISO 8601) |
| `submitter` | No | Your email (for audit) |

### 1.3 Computing SHA-256

**Linux / macOS:**
```bash
sha256sum yourfile.pdf
# Output: a1b2c3d4e5f67890...  yourfile.pdf
# Use the first 64 characters (the hash)
```

**Windows (PowerShell):**
```powershell
Get-FileHash yourfile.pdf -Algorithm SHA256 | Select-Object -ExpandProperty Hash
```

### 1.4 Supported MIME Types

| MIME Type | Format |
|-----------|--------|
| `application/pdf` | PDF |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | DOCX |
| `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | XLSX |
| `application/vnd.openxmlformats-officedocument.presentationml.presentation` | PPTX |
| `text/plain` | TXT |
| `text/csv` | CSV |
| `image/png` | PNG |
| `image/tiff` | TIFF |

Unsupported formats are rejected with reason `UNSUPPORTED_FORMAT`.

### 1.5 Authentication

You need a **Bearer JWT** token with `ingest` scope. Obtain the token from your Frostbyte administrator. Include it in the request:

```
Authorization: Bearer <your_jwt_token>
```

### 1.6 Submitting a Batch (curl)

```bash
curl -X POST "https://{tenant_id}.pipeline.frostbyte.io/api/v1/ingest/{tenant_id}/batch" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "manifest=@manifest.json;type=application/json" \
  -F "files=@contract_2024.pdf" \
  -F "files=@invoice.xlsx"
```

**Important:** The number of `files` parts must equal `file_count`. File order should match the `files[]` array order, or use `Content-Disposition: form-data; name="files"; filename="contract_2024.pdf"` with a matching `file_id` if the API supports it.

### 1.7 Response (202 Accepted)

You receive a **batch receipt** immediately. Processing continues asynchronously. Use `GET /api/v1/ingest/{tenant_id}/batch/{batch_id}` to poll status.

---

## 2. Acceptance Report Interpretation

### 2.1 Batch Receipt Fields

| Field | Meaning |
|-------|---------|
| `batch_id` | Your batch identifier |
| `file_count` | Total files submitted |
| `accepted` | Files that passed all checks and were ingested |
| `rejected` | Files that failed validation (see `rejected_files`) |
| `quarantined` | Files flagged by malware scan (see `quarantined_files`) |
| `receipts` | Receipt IDs for accepted files |
| `rejected_files` | Per-file rejection reasons |
| `quarantined_files` | Per-file quarantine reasons |
| `received_at` | Server timestamp |

### 2.2 Rejected File Reasons

| Reason | Meaning | What to Do |
|--------|---------|------------|
| `UNSUPPORTED_FORMAT` | MIME type not on allowlist | Use a supported format or request format support |
| `SIZE_EXCEEDED` | File exceeds max size (default 500 MB) | Split or compress the file |
| `CHECKSUM_MISMATCH` | SHA-256 in manifest does not match file | Recompute SHA-256; ensure file wasn't modified after hashing |
| `MANIFEST_INVALID` | Manifest malformed or missing required fields | Fix manifest JSON |
| `MANIFEST_FILE_COUNT_MISMATCH` | `file_count` ≠ number of files | Correct `file_count` or add/remove files |
| `DUPLICATE_FILE_ID` | Two files have same `file_id` | Use unique `file_id` per file |

### 2.3 Quarantined File Reasons

| Reason | Meaning | What to Do |
|--------|---------|------------|
| `MALWARE_DETECTED` | File flagged by ClamAV | Do not resubmit; file may be infected; contact IT/security |

### 2.4 Per-File Stages (Batch Status)

When you poll `GET /api/v1/ingest/{tenant_id}/batch/{batch_id}`, each file has a stage:

| Stage | Meaning |
|-------|---------|
| `intake` | Received, validated, stored |
| `parsing` | Parse job in progress |
| `parsed` | Parsing complete |
| `parse_failed` | Parsing failed (see acceptance report) |
| `policy` | Policy checks in progress |
| `indexed` | Fully processed, searchable |

### 2.5 Common Issues

**"All files rejected"**
- Check manifest schema (required fields, types)
- Verify `file_count` matches number of files
- Ensure JWT is valid and has `ingest` scope

**"Some files CHECKSUM_MISMATCH"**
- Recompute SHA-256 after any copy/transfer
- Ensure you hashed the exact file you're uploading
- Check for line-ending changes (CRLF vs LF) in text files

**"UNSUPPORTED_FORMAT"**
- Verify MIME type is in the allowlist
- Use `file` or similar tool to check actual file type; don't rely on extension alone

---

## 3. Troubleshooting

### 3.1 Error Response Format

Errors return JSON with a standard structure:

```json
{
  "error_code": "CHECKSUM_MISMATCH",
  "message": "Expected SHA-256 a1b2... but computed c3d4...",
  "details": { "file_id": "file_003" }
}
```

### 3.2 Resolution Steps by Error

| Error | Step 1 | Step 2 | Escalate? |
|-------|--------|--------|-----------|
| `401 AUTHENTICATION_REQUIRED` | Check token presence, expiration | Request new token from admin | If token is valid and recent |
| `403 TENANT_SUSPENDED` | Contact Frostbyte support | — | Yes |
| `429 RATE_LIMIT_EXCEEDED` | Wait 1 minute, retry | Reduce batch size or frequency | If limit seems wrong |
| `CHECKSUM_MISMATCH` | Recompute hash, fix manifest | Resubmit | If hash matches and still fails |
| `UNSUPPORTED_FORMAT` | Verify MIME, use allowed format | Request new format support | If format should be supported |
| `MALWARE_DETECTED` | Do not resubmit | Contact IT/security | If false positive suspected |

### 3.3 Escalation Paths

1. **Frostbyte Support** — Tenant suspension, token issues, platform errors
2. **Engineering** — Suspected bugs (e.g., checksum verified correct but rejected), format support requests
3. **Your IT/Security** — Malware-flagged files, internal security review

### 3.4 Getting Help

- **Documentation:** This guide, [INTAKE_GATEWAY_PLAN](INTAKE_GATEWAY_PLAN.md) (technical reference)
- **Support:** Contact your Frostbyte account contact
- **Audit export:** Use Audit API (if available) for compliance evidence; see [AUDIT_ARCHITECTURE](AUDIT_ARCHITECTURE.md)
