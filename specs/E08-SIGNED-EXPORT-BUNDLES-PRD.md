# Enhancement #8 – Signed Export Bundles with Verification

## All-In-One Zero-Shot PRD

**Status:** Deterministic, executable  
**Format:** COSTAR System Prompt + Zero-Shot Prompt + PRD + Implementation Plan

---

## COSTAR System Prompt

```
[CONTEXT]
You are implementing signed export bundles for the Frostbyte ETL pipeline. The system must allow a tenant to export a set of documents and their metadata as a cryptographically signed archive. A verification tool must be provided to validate the bundle's integrity and provenance. All design decisions (archive format, signing method, CLI tool) are defined in the PRD. No decisions are left open.

[OBJECTIVE]
Generate the export endpoint, signing logic, and a standalone Python CLI verification tool. Use GPG for signing. The archive format must be TAR.GZ with a manifest JSON containing hashes and signatures.

[STYLE]
Imperative, production-ready. Provide each file content in a code block with its full relative path. No commentary.

[AUDIENCE]
Backend developer. Execute the steps exactly as written.
```

---

## Zero-Shot Prompt

*Concatenated with the PRD and Implementation Plan below – feed this entire document to the implementation LLM.*

---

## Production Requirements Document (PRD) – Signed Export Bundles

### 1. Export Format

- **Container**: `.tar.gz`
- **Internal structure**:

```
export_id/
├── manifest.json
├── documents/
│   ├── doc1.json
│   ├── doc2.json
│   └── ...
└── chunks/
    ├── chunk1.json
    └── ...
```

- **manifest.json** schema:

```json
{
  "export_id": "uuid",
  "tenant_id": "uuid",
  "created_at": "ISO8601",
  "document_count": 3,
  "chunk_count": 12,
  "files": [
    {"path": "documents/doc1.json", "sha256": "hex"},
    ...
  ],
  "signature": "base64-encoded GPG signature"
}
```

### 2. Signing Method

- **Tool**: GPG (GnuPG)
- **Key**: A dedicated signing key per tenant (generated on first export request).
- **Public key** stored in database, private key used only for signing.
- **Signature**: Clearsign the entire `manifest.json` (without the signature field) and store in `signature` field.

### 3. Export API Endpoint

**Endpoint**: `POST /tenants/{tenant_id}/exports`

**Request Body**:

```json
{
  "document_ids": ["uuid1", "uuid2"],
  "include_chunks": true
}
```

**Response**:  
`202 Accepted` with `Location: /tenants/{tenant_id}/exports/{export_id}`

**Polling**:  
`GET /tenants/{tenant_id}/exports/{export_id}` returns status (`pending`, `completed`, `failed`) and when completed, `download_url` (pre-signed S3 URL or local file path).

### 4. Background Export Worker

- Queue: Redis list `export:jobs`.
- Worker assembles files, computes SHA256, creates manifest, signs with GPG, creates tar.gz.
- Stores bundle in configured storage (local filesystem for MVP).
- Updates export record with status and download path.

### 5. Verification CLI Tool

- Name: `frostbyte-verify`
- Command: `frostbyte-verify bundle.tar.gz --public-key key.asc`
- Steps:
  1. Extract manifest.
  2. Verify GPG signature using provided public key.
  3. Recompute SHA256 of each file and compare.
- Exit code 0 on success, 1 on failure.

### 6. GPG Key Management

- On first export request for a tenant, generate a new GPG key pair:
  `gpg --batch --gen-key` with preset parameters.
- Export public key and store in `tenant_keys` table.
- Private key remains on server filesystem; worker has access.

---

## Deterministic Implementation Plan

### Step 1 – Install dependencies

```bash
pip install python-gnupg
```

### Step 2 – Add GPG configuration to settings

**File**: `app/config.py` add:

```python
GPG_HOME_DIR: str = "/var/lib/frostbyte/gpg"
EXPORT_STORAGE_PATH: str = "/var/lib/frostbyte/exports"
```

### Step 3 – Create database migration for export jobs and tenant keys

```bash
alembic revision -m "add_exports_and_tenant_keys"
```

Migration content:

```python
def upgrade():
    op.create_table('tenant_keys',
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('public_key', sa.Text(), nullable=False),
        sa.Column('fingerprint', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('tenant_id')
    )
    op.create_table('export_jobs',
        sa.Column('export_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('document_ids', sa.ARRAY(sa.UUID()), nullable=False),
        sa.Column('include_chunks', sa.Boolean(), nullable=False),
        sa.Column('manifest_path', sa.String(), nullable=True),
        sa.Column('bundle_path', sa.String(), nullable=True),
        sa.Column('download_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('export_id')
    )
```

### Step 4 – Create GPG key management module

**File**: `app/export/gpg_keys.py`

```python
import gnupg
import os
from uuid import UUID
from app.config import settings

gpg = gnupg.GPG(gnupghome=settings.GPG_HOME_DIR)

def ensure_tenant_key(tenant_id: UUID, conn):
    # Check if key already exists in DB
    row = await conn.fetchrow("SELECT fingerprint FROM tenant_keys WHERE tenant_id = $1", tenant_id)
    if row:
        return row['fingerprint']
    # Generate new key
    input_data = gpg.gen_key_input(
        name_real=f"Tenant {tenant_id}",
        name_email=f"{tenant_id}@frostbyte.tenant",
        key_type="RSA",
        key_length=2048,
        no_protection=True
    )
    key = gpg.gen_key(input_data)
    fingerprint = key.fingerprint
    public_key = gpg.export_keys(fingerprint)
    # Store in DB
    await conn.execute("""
        INSERT INTO tenant_keys (tenant_id, public_key, fingerprint, created_at)
        VALUES ($1, $2, $3, now())
    """, tenant_id, public_key, fingerprint)
    return fingerprint
```

### Step 5 – Create export API endpoints

**File**: `app/api/endpoints/exports.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID, uuid4
from pydantic import BaseModel
from typing import List
import json
import redis.asyncio as redis
from app.db import get_connection
from app.config import settings

router = APIRouter(prefix="/tenants/{tenant_id}/exports", tags=["exports"])

class ExportRequest(BaseModel):
    document_ids: List[UUID]
    include_chunks: bool = True

@router.post("/")
async def create_export(tenant_id: UUID, payload: ExportRequest, conn = Depends(get_connection)):
    export_id = uuid4()
    # Create job record
    await conn.execute("""
        INSERT INTO export_jobs (export_id, tenant_id, status, document_ids, include_chunks, created_at, updated_at)
        VALUES ($1, $2, 'pending', $3, $4, now(), now())
    """, export_id, tenant_id, payload.document_ids, payload.include_chunks)
    # Push to Redis queue
    r = redis.from_url(settings.REDIS_URL)
    await r.rpush("export:jobs", json.dumps({
        "export_id": str(export_id),
        "tenant_id": str(tenant_id),
        "document_ids": [str(d) for d in payload.document_ids],
        "include_chunks": payload.include_chunks
    }))
    await r.close()
    return {"export_id": export_id, "status": "pending"}

@router.get("/{export_id}")
async def get_export(tenant_id: UUID, export_id: UUID, conn = Depends(get_connection)):
    row = await conn.fetchrow("""
        SELECT export_id, status, manifest_path, bundle_path, download_url, created_at, updated_at
        FROM export_jobs
        WHERE export_id = $1 AND tenant_id = $2
    """, export_id, tenant_id)
    if not row:
        raise HTTPException(404, "Export not found")
    return dict(row)
```

### Step 6 – Create export worker

**File**: `app/worker/export_worker.py`

```python
import asyncio
import json
import tarfile
import hashlib
import os
from pathlib import Path
from uuid import UUID
import asyncpg
import redis.asyncio as redis
from app.config import settings
from app.export.gpg_keys import ensure_tenant_key, gpg
from datetime import datetime

EXPORT_DIR = Path(settings.EXPORT_STORAGE_PATH)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

async def export_worker():
    r = redis.from_url(settings.REDIS_URL)
    while True:
        try:
            _, payload = await r.blpop("export:jobs", timeout=1)
            if not payload:
                continue
            data = json.loads(payload)
            export_id = UUID(data["export_id"])
            tenant_id = UUID(data["tenant_id"])
            document_ids = [UUID(doc) for doc in data["document_ids"]]
            include_chunks = data["include_chunks"]

            conn = await asyncpg.connect(settings.DATABASE_URL)

            # 1. Ensure tenant has GPG key
            fingerprint = await ensure_tenant_key(tenant_id, conn)

            # 2. Create temporary working directory
            work_dir = EXPORT_DIR / str(export_id)
            work_dir.mkdir()
            docs_dir = work_dir / "documents"
            docs_dir.mkdir()
            chunks_dir = work_dir / "chunks"
            if include_chunks:
                chunks_dir.mkdir()

            # 3. Fetch and write document/chunk JSON files
            files_manifest = []
            for doc_id in document_ids:
                doc_row = await conn.fetchrow("SELECT * FROM documents WHERE id = $1", doc_id)
                if doc_row:
                    doc_path = docs_dir / f"{doc_id}.json"
                    with open(doc_path, "w") as f:
                        json.dump(dict(doc_row), f, default=str)
                    sha = hashlib.sha256(doc_path.read_bytes()).hexdigest()
                    files_manifest.append({"path": f"documents/{doc_id}.json", "sha256": sha})

                    if include_chunks:
                        chunk_rows = await conn.fetch("SELECT * FROM chunks WHERE document_id = $1", doc_id)
                        for chunk_row in chunk_rows:
                            chunk_path = chunks_dir / f"{chunk_row['chunk_id']}.json"
                            with open(chunk_path, "w") as f:
                                json.dump(dict(chunk_row), f, default=str)
                            sha = hashlib.sha256(chunk_path.read_bytes()).hexdigest()
                            files_manifest.append({"path": f"chunks/{chunk_row['chunk_id']}.json", "sha256": sha})

            # 4. Create manifest.json (without signature)
            manifest = {
                "export_id": str(export_id),
                "tenant_id": str(tenant_id),
                "created_at": datetime.utcnow().isoformat(),
                "document_count": len(document_ids),
                "chunk_count": len(files_manifest) - len(document_ids),
                "files": files_manifest
            }
            manifest_path = work_dir / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            # 5. Sign the manifest
            with open(manifest_path, "rb") as f:
                signed_data = gpg.sign_file(f, keyid=fingerprint, detach=False, clearsign=True)
            manifest["signature"] = str(signed_data)
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            # 6. Create tar.gz
            bundle_path = EXPORT_DIR / f"{export_id}.tar.gz"
            with tarfile.open(bundle_path, "w:gz") as tar:
                tar.add(work_dir, arcname=str(export_id))

            # 7. Update DB
            await conn.execute("""
                UPDATE export_jobs
                SET status = 'completed', manifest_path = $1, bundle_path = $2, download_url = $3, updated_at = now()
                WHERE export_id = $4
            """, str(manifest_path), str(bundle_path), f"/exports/{export_id}.tar.gz", export_id)

            await conn.close()
            # Cleanup temp dir
            import shutil
            shutil.rmtree(work_dir)

        except Exception as e:
            print(f"Export worker error: {e}")
            await asyncio.sleep(5)
```

### Step 7 – Create CLI verification tool

**File**: `scripts/frostbyte-verify.py`

```python
#!/usr/bin/env python3
import argparse
import tarfile
import json
import hashlib
import sys
import gnupg
import tempfile
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Verify Frostbyte export bundle")
    parser.add_argument("bundle", help="Path to .tar.gz bundle")
    parser.add_argument("--public-key", required=True, help="Public key file for verification")
    args = parser.parse_args()

    gpg = gnupg.GPG()
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract bundle
        with tarfile.open(args.bundle, "r:gz") as tar:
            tar.extractall(tmpdir)
        # Find manifest.json (top-level directory)
        dirs = [d for d in Path(tmpdir).iterdir() if d.is_dir()]
        if len(dirs) != 1:
            print("❌ Bundle should contain exactly one top-level directory")
            sys.exit(1)
        manifest_path = dirs[0] / "manifest.json"
        if not manifest_path.exists():
            print("❌ manifest.json not found")
            sys.exit(1)
        with open(manifest_path) as f:
            manifest = json.load(f)
        # Extract signature and remove from manifest for verification
        signature = manifest.pop("signature", None)
        if not signature:
            print("❌ No signature in manifest")
            sys.exit(1)
        # Import public key
        with open(args.public_key) as f:
            gpg.import_keys(f.read())
        # Verify signature
        verified = gpg.verify(signature)
        if not verified:
            print("❌ GPG signature verification failed")
            sys.exit(1)
        print("✅ GPG signature valid")
        # Verify file hashes
        base_dir = dirs[0]
        for file_entry in manifest["files"]:
            file_path = base_dir / file_entry["path"]
            if not file_path.exists():
                print(f"❌ Missing file: {file_entry['path']}")
                sys.exit(1)
            sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if sha != file_entry["sha256"]:
                print(f"❌ Hash mismatch for {file_entry['path']}")
                sys.exit(1)
        print("✅ All file hashes match")
        print("✅ Export bundle is valid and authentic")
        sys.exit(0)

if __name__ == "__main__":
    main()
```

### Step 8 – Add export worker to startup

In `app/main.py`:

```python
from app.worker.export_worker import export_worker

@app.on_event("startup")
async def start_workers():
    asyncio.create_task(batch_worker())
    asyncio.create_task(export_worker())
```

### Step 9 – Commit

```bash
git add app/export app/api/endpoints/exports.py app/worker/export_worker.py scripts/frostbyte-verify.py
git add alembic/versions/*_add_exports_and_tenant_keys.py
git commit -m "feat(export): add signed export bundles with GPG verification CLI"
```
