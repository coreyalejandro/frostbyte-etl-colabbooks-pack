# Tenant Isolation: Per-Tenant Storage Namespaces and Encryption Key Management

**Document version:** 1.0
**Created:** 2026-02-11
**Requirement traceability:** ISOL-02 (per-tenant storage namespaces), ISOL-03 (encryption key management)
**References:** [PRD.md](PRD.md) Section 3.4 (Provisioning steps 4–7), Section 3.6 (Deprovisioning steps 3–5); [TECH_DECISIONS.md](TECH_DECISIONS.md) Component #11 (PostgreSQL >=16), #15 (Qdrant >=1.13), #16 (MinIO), #19 (Redis >=8.0), #20 (SOPS + age)

---

## Document Conventions

| Notation | Meaning |
|----------|---------|
| `mc {cmd}` | MinIO Client command |
| `{alias}` | MinIO alias (e.g. `minio-prod`) |
| `{tenant_id}` | Tenant identifier (lowercase, alphanumeric) |
| `tenant_{tenant_id}` | SQL identifier (underscores) |

**Storage isolation principle:** Every tenant gets dedicated namespaces in all stateful components. No shared tables, buckets, collections, or key prefixes across tenants. Isolation is structural (by construction), not policy-based (by filter).

---

## 1. Storage Isolation Overview

| Store | Namespace Type | Naming Convention | Credential Scope | Isolation Mechanism |
|-------|----------------|-------------------|------------------|---------------------|
| MinIO | Bucket | `tenant-{tenant_id}-bucket` | IAM user + policy | Per-user IAM policy scoped to bucket ARN |
| PostgreSQL | Database | `tenant_{tenant_id}` | Database user | Dedicated user + REVOKE CONNECT FROM PUBLIC + pg_hba.conf |
| Qdrant | Collection | `tenant_{tenant_id}` | Application-level | Collection-per-tenant + app-level access control |
| Redis | Key prefix | `tenant:{tenant_id}:*` | ACL user (Redis >=6) | Key prefix + ACL rules |

### Data Flow Diagram

```mermaid
flowchart LR
    subgraph INTAKE
        RAW[Raw Documents]
    end

    subgraph MINIO["MinIO (Object Store)"]
        BUCKET[tenant_{tenant_id}_bucket]
    end

    subgraph PG["PostgreSQL"]
        DB[(tenant_{tenant_id} DB)]
    end

    subgraph QDRANT["Qdrant (Vector Store)"]
        COLL[tenant_{tenant_id} collection]
    end

    RAW --> BUCKET
    BUCKET -->|parsed JSON| DB
    DB -->|metadata| COLL
```

---

## 2. MinIO Object Store Isolation (PRD 3.4 Step 4)

### 2.1 Bucket Provisioning

```bash
mc mb {alias}/tenant-{tenant_id}-bucket
```

**Naming:** 3–63 chars, lowercase, hyphens allowed. Example: `tenant-abc-bucket`.

**Server-side encryption:**

```bash
mc encrypt set sse-s3 {alias}/tenant-{tenant_id}-bucket
```

### 2.2 IAM User and Policy Creation

**Research Pitfall 5:** Bucket policies control anonymous access only. Authenticated user access is controlled by IAM policies attached to the user. Use IAM policies for per-tenant isolation.

**Generate credentials:** Use `openssl rand -base64 32` for secret key. Store in SOPS-encrypted secrets file (see Section 6).

```bash
mc admin user add {alias} tenant-{tenant_id}-access {secret_key}
```

**IAM policy (complete):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": ["arn:aws:s3:::tenant-{tenant_id}-bucket"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::tenant-{tenant_id}-bucket/*"]
    }
  ]
}
```

IAM defaults to deny; allow-only policies suffice. User can access only the specified bucket. Create and attach:

```bash
mc admin policy create {alias} tenant-{tenant_id}-policy tenant-{tenant_id}-policy.json
mc admin policy attach {alias} tenant-{tenant_id}-policy --user=tenant-{tenant_id}-access
```

### 2.3 Bucket Structure

```
tenant-{tenant_id}-bucket/
  raw/                    # Original uploaded documents
  parsed/                 # Canonical JSON after parsing
  receipts/               # Intake receipts
  exports/                # Compliance evidence exports
```

### 2.4 Verification

```bash
mc alias set tenant-test http://{minio_host}:9000 tenant-{tenant_id}-access {secret_key}
mc ls tenant-test
# Expect: only tenant-{tenant_id}-bucket

mc ls tenant-test/tenant-{other_id}-bucket
# Expect: Access Denied

mc admin user info {alias} tenant-{tenant_id}-access
# Expect: PolicyName tenant-{tenant_id}-policy
```

### 2.5 Deprovisioning (PRD 3.6 Step 5)

```bash
mc rm --recursive --force {alias}/tenant-{tenant_id}-bucket
mc rb {alias}/tenant-{tenant_id}-bucket
mc admin user remove {alias} tenant-{tenant_id}-access
mc admin policy remove {alias} tenant-{tenant_id}-policy
```

**Verification:** `mc ls {alias}/tenant-{tenant_id}-bucket` → "bucket not found".

### 2.6 Offline Mode

Same MinIO instance in Docker. Same commands. Volume: `minio-data:/data` in docker-compose.yml.

---

## 3. PostgreSQL Relational Database Isolation (PRD 3.4 Step 5)

### 3.1 Database and User Provisioning

```sql
-- 1. Create database
CREATE DATABASE tenant_{tenant_id};

-- 2. Create user with encrypted password
CREATE USER tenant_{tenant_id}_user WITH ENCRYPTED PASSWORD '{password_from_sops}';

-- 3. Grant privileges on database
GRANT ALL PRIVILEGES ON DATABASE tenant_{tenant_id} TO tenant_{tenant_id}_user;

-- 4. Revoke public access (CRITICAL)
REVOKE CONNECT ON DATABASE tenant_{tenant_id} FROM PUBLIC;

-- 5. Connect to tenant database and grant schema privileges
\c tenant_{tenant_id}
GRANT ALL ON SCHEMA public TO tenant_{tenant_id}_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO tenant_{tenant_id}_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO tenant_{tenant_id}_user;
```

**Why REVOKE CONNECT FROM PUBLIC:** Without it, any database user can connect to any database. Revoking limits access to explicitly granted users only.

### 3.2 pg_hba.conf Network Restriction

```
host  tenant_{tenant_id}  tenant_{tenant_id}_user  10.{tenant_octet}.0.0/16  scram-sha-256
```

This restricts the tenant user to connections from the tenant's private network only. Reload: `SELECT pg_reload_conf();` (no restart). Place more specific rules before general rules in pg_hba.conf.

### 3.3 Verification

```bash
psql -l                    # Verify tenant_{tenant_id} exists
psql -c "\du"              # Verify tenant_{tenant_id}_user
psql -h {host} -U tenant_{tenant_id}_user -d tenant_{tenant_id}
# From tenant network: expect success

psql -h {host} -U tenant_{tenant_id}_user -d tenant_{other_id}
# Expect: permission denied

psql -h {host} -U tenant_{tenant_id}_user -d tenant_{tenant_id}
# From non-tenant network: expect "no pg_hba.conf entry"
```

### 3.4 Deprovisioning (PRD 3.6 Step 4)

```sql
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'tenant_{tenant_id}';
DROP DATABASE tenant_{tenant_id};
DROP USER tenant_{tenant_id}_user;
```

Remove pg_hba.conf entry and reload. **Verification:** `\l` should not show `tenant_{tenant_id}`.

### 3.5 Offline Mode

Shared PostgreSQL in Docker. Same SQL. Use Docker network CIDR in pg_hba.conf instead of Hetzner private CIDR.

---

## 4. Qdrant Vector Store Isolation (PRD 3.4 Step 6)

### 4.1 Collection Provisioning

**REST API:**

```http
PUT /collections/tenant_{tenant_id}
Content-Type: application/json

{
  "vectors": {
    "size": 768,
    "distance": "Cosine"
  }
}
```

**Python SDK (qdrant_client):**

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")
client.create_collection(
    collection_name=f"tenant_{tenant_id}",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)
```

Vector size 768 is locked per [TECH_DECISIONS.md](TECH_DECISIONS.md).

### 4.2 Application-Level Access Control

Qdrant does not natively scope API keys to collections. Use application guards:

```python
def get_collection_name(tenant_id: str) -> str:
    return f"tenant_{tenant_id}"

def verify_tenant_access(tenant_id: str, collection_name: str) -> None:
    expected = get_collection_name(tenant_id)
    if collection_name != expected:
        raise PermissionError(f"Tenant {tenant_id} cannot access {collection_name}")
```

All Qdrant operations must pass through these guards. Collections remain structurally separate; no Tenant A vector exists in Tenant B's collection.

### 4.3 Verification

```bash
curl -s http://localhost:6333/collections | jq '.result.collections[].name'
# Verify tenant_{tenant_id} in list
```

Insert test vector and search; results must be tenant-scoped. Call `verify_tenant_access` with wrong collection → PermissionError.

### 4.4 Deprovisioning (PRD 3.6 Step 3)

```http
DELETE /collections/tenant_{tenant_id}
```

**Verification:** `GET /collections/tenant_{tenant_id}` → 404.

### 4.5 Offline Mode

Same Qdrant in Docker. Same REST API. Volume: `qdrant-data:/qdrant/storage`.

---

## 5. Redis Cache/Queue Isolation (PRD 3.4 Step 7)

### 5.1 Key Prefix Convention

All tenant keys: `tenant:{tenant_id}:`

| Use | Example |
|-----|---------|
| Cache | `tenant:{tenant_id}:cache:{key}` |
| Queue | `tenant:{tenant_id}:queue:{queue_name}` |
| Rate limit | `tenant:{tenant_id}:ratelimit:{endpoint}` |
| Session | `tenant:{tenant_id}:session:{session_id}` |

### 5.2 Redis ACL Configuration (Redis >=6, >=8 per TECH_DECISIONS)

```
ACL SETUSER tenant_{tenant_id}_user on >{password} ~tenant:{tenant_id}:* +@all -@dangerous
ACL SAVE
```

Restricts user to keys matching `tenant:{tenant_id}:*`. `-@dangerous` blocks FLUSHALL, FLUSHDB, CONFIG, DEBUG.

### 5.3 Verification

```bash
redis-cli AUTH tenant_{tenant_id}_user {password}
redis-cli SET tenant:{tenant_id}:test value
# Expect: OK

redis-cli SET tenant:{other_id}:test value
# Expect: NOPERM

redis-cli ACL GETUSER tenant_{tenant_id}_user
# Verify key pattern tenant:{tenant_id}:*
```

### 5.4 Deprovisioning

```bash
redis-cli --scan --pattern "tenant:{tenant_id}:*" | xargs -r redis-cli DEL
redis-cli ACL DELUSER tenant_{tenant_id}_user
redis-cli ACL SAVE
```

**Verification:** `redis-cli --scan --pattern "tenant:{tenant_id}:*"` → empty.

### 5.5 Offline Mode

Same Redis in Docker. Same ACL. Volume: `redis-data:/data`.

---

## 6. Encryption Key Management Design (ISOL-03)

### 6.1 Three-Tier Key Hierarchy

```
Tier 1: age recipient key (KEK) — per-tenant asymmetric key pair
  └─> Tier 2: SOPS data key (DEK) — per-file 256-bit AES, encrypted by KEK
      └─> Tier 3: Individual secret values — AES256_GCM using DEK
```

- **KEK (age):** Protects DEK. One per tenant. Public in registry; private in control plane storage.
- **DEK (SOPS):** Protects secrets in a SOPS file. Auto-generated per file. Never stored plain.
- **Secrets:** DB passwords, API keys, MinIO credentials. Encrypted with AES256_GCM.

**Envelope encryption:** Compromising DEK exposes one file; compromising KEK exposes one tenant's secrets, not others.

### 6.2 Key Generation Procedure

```bash
mkdir -p .secrets/tenants/{tenant_id}
age-keygen -o .secrets/tenants/{tenant_id}/key.age
grep "public key:" .secrets/tenants/{tenant_id}/key.age | awk '{print $NF}' > .secrets/tenants/{tenant_id}/key.pub
chmod 600 .secrets/tenants/{tenant_id}/key.age
```

Store public key in registry: `UPDATE tenants SET age_public_key = '{public_key}' WHERE tenant_id = '{tenant_id}';`

**Private key storage:** Online: control plane server, encrypted filesystem. Offline: bundled in encrypted config.

### 6.3 Secrets File Structure

**Before encryption:**

```yaml
# tenant-{tenant_id}-secrets.yaml
minio_access_key: "tenant-{tenant_id}-access"
minio_secret_key: "{generated_secret}"
postgres_password: "{generated_password}"
qdrant_api_key: "{generated_key}"
redis_password: "{generated_password}"
tenant_api_key: "{generated_api_key}"
```

**After SOPS encryption:** Values become `ENC[AES256_GCM,data:...,iv:...,tag:...,type:str]` with sops metadata block.

**.sops.yaml:**

```yaml
creation_rules:
  - path_regex: \.secrets/tenants/([^/]+)/secrets\.enc\.yaml$
    age: "age1..."  # Set per tenant at encrypt time
```

### 6.4 Encryption Workflow

```bash
sops --age $(cat .secrets/tenants/{tenant_id}/key.pub) \
     --encrypt .secrets/tenants/{tenant_id}/secrets.yaml \
     > .secrets/tenants/{tenant_id}/secrets.enc.yaml
shred -u .secrets/tenants/{tenant_id}/secrets.yaml
```

### 6.5 Decryption Workflow

**CLI:**

```bash
export SOPS_AGE_KEY_FILE=.secrets/tenants/{tenant_id}/key.age
sops --decrypt .secrets/tenants/{tenant_id}/secrets.enc.yaml
```

**Python:**

```python
import subprocess
import yaml
import os

def decrypt_tenant_secrets(tenant_id: str) -> dict:
    result = subprocess.run(
        ["sops", "--decrypt", f".secrets/tenants/{tenant_id}/secrets.enc.yaml"],
        capture_output=True, text=True,
        env={**os.environ, "SOPS_AGE_KEY_FILE": f".secrets/tenants/{tenant_id}/key.age"}
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to decrypt secrets for {tenant_id}: {result.stderr}")
    return yaml.safe_load(result.stdout)
```

---

## 7. Key Rotation Procedure

### 7.1 Rotation Triggers

- Scheduled: every 90 days (configurable)
- Emergency: suspected compromise
- Personnel: operator with key access leaves

### 7.2 Step-by-Step Rotation

```bash
age-keygen -o .secrets/tenants/{tenant_id}/key-new.age
NEW_PUB=$(grep "public key:" .secrets/tenants/{tenant_id}/key-new.age | awk '{print $NF}')
OLD_PUB=$(cat .secrets/tenants/{tenant_id}/key.pub)

SOPS_AGE_KEY_FILE=.secrets/tenants/{tenant_id}/key.age \
  sops --decrypt .secrets/tenants/{tenant_id}/secrets.enc.yaml > /dev/null
echo "Old key decryption: OK"

sops --rotate --add-age $NEW_PUB --rm-age $OLD_PUB \
  --in-place .secrets/tenants/{tenant_id}/secrets.enc.yaml

SOPS_AGE_KEY_FILE=.secrets/tenants/{tenant_id}/key-new.age \
  sops --decrypt .secrets/tenants/{tenant_id}/secrets.enc.yaml > /dev/null
echo "New key decryption: OK"

mv .secrets/tenants/{tenant_id}/key.age .secrets/tenants/{tenant_id}/key-$(date +%Y%m%d)-archived.age
mv .secrets/tenants/{tenant_id}/key-new.age .secrets/tenants/{tenant_id}/key.age
echo $NEW_PUB > .secrets/tenants/{tenant_id}/key.pub

# Update registry
# UPDATE tenants SET age_public_key = '$NEW_PUB', key_rotated_at = NOW() WHERE tenant_id = '{tenant_id}';
# INSERT INTO audit_events (event_type, tenant_id, details) VALUES ('KEY_ROTATED', '{tenant_id}', '{}');
```

### 7.3 Backup Recovery (Research Pitfall 3)

Archive old private keys for 90 days. Restore from pre-rotation backups with archived key. Key-to-backup-date mapping should be tracked in the control plane registry for recovery. After retention: `shred -u .secrets/tenants/{tenant_id}/key-*-archived.age`.

### 7.4 Emergency Rotation

Same steps; revoke old key immediately. Terminate sessions; regenerate MinIO, PostgreSQL, Qdrant, Redis credentials and re-encrypt.

---

## 8. Key-to-Tenant Mapping Registry

### 8.1 Control Plane Schema

```sql
ALTER TABLE tenants ADD COLUMN age_public_key TEXT NOT NULL;
ALTER TABLE tenants ADD COLUMN key_rotated_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE tenants ADD COLUMN key_rotation_due_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE tenants ADD COLUMN key_version INTEGER DEFAULT 1;
```

### 8.2 Key History Table

```sql
CREATE TABLE tenant_key_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id),
  key_version INTEGER NOT NULL,
  public_key_hash TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  archived_at TIMESTAMP WITH TIME ZONE,
  purged_at TIMESTAMP WITH TIME ZONE,
  rotation_reason TEXT
);
```

### 8.3 Key Status Lifecycle

- ACTIVE: current key
- ARCHIVED: retained for backup recovery
- PURGED: deleted after retention

---

## 9. Storage Isolation Verification Runbook

### 9.1 Cross-Store Checklist

- [ ] MinIO: tenant user only accesses tenant bucket
- [ ] PostgreSQL: tenant user only connects to tenant database
- [ ] Qdrant: guard blocks cross-collection access
- [ ] Redis: ACL user only accesses tenant prefix
- [ ] Encryption: tenant secrets decrypt only with tenant age key

### 9.2 Verification Report Format

```json
{
  "tenant_id": "{tenant_id}",
  "checks": [
    {"store": "minio", "test": "cross_tenant_access", "result": "DENIED", "timestamp": "2026-02-11T12:00:00Z"},
    {"store": "postgresql", "test": "cross_db_connect", "result": "DENIED", "timestamp": "2026-02-11T12:00:01Z"}
  ],
  "overall_pass": true
}
```

### 9.3 Compliance Evidence

Store verification results for audit. Reference Phase 3 audit design.

---

## 10. Storage Provisioning Sequence (Combined)

Order for [PRD Section 3.4](PRD.md) steps 4–7:

1. Generate age key pair (Section 6.2)
2. Generate credentials (random passwords/keys)
3. Create SOPS-encrypted secrets file (Section 6.4)
4. Provision MinIO bucket and user (Section 2)
5. Provision PostgreSQL database and user (Section 3)
6. Provision Qdrant collection (Section 4)
7. Provision Redis ACL user (Section 5)
8. Run cross-store verification (Section 9)
9. Register tenant with key metadata (Section 8)

**Error handling:** On failure, roll back all completed steps in reverse order.
