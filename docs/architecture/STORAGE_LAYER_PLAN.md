# Storage Layer Implementation Plan

**Version:** 1.0  
**Created:** 2026-02-11  
**Requirement traceability:** IMPL-02  
**References:** [PRD.md](PRD.md) Section 3.4 (Provisioning steps 4–7), Section 3.6; [TENANT_ISOLATION_STORAGE_ENCRYPTION.md](TENANT_ISOLATION_STORAGE_ENCRYPTION.md) Sections 2–6, 9–10; [AUDIT_ARCHITECTURE.md](AUDIT_ARCHITECTURE.md) Section 1, 2.3

---

## Document Conventions

| Notation | Meaning |
|----------|---------|
| `mc {cmd}` | MinIO Client command |
| `{alias}` | MinIO alias (e.g., `minio-prod`) |
| `{tenant_id}` | Tenant identifier (lowercase, alphanumeric) |
| `tenant_{tenant_id}` | SQL/collection identifier (underscores) |

**Storage isolation principle:** Every tenant gets dedicated namespaces in all stateful components. No shared tables, buckets, collections, or key prefixes across tenants. Isolation is structural (by construction), not policy-based (by filter).

---

## 1. Overview

The storage layer implements [PRD Section 3.4](PRD.md) steps 4–7:

| PRD Step | Action | Store |
|----------|--------|-------|
| 4 | Provision object storage | MinIO |
| 5 | Provision relational database | PostgreSQL |
| 6 | Provision vector store | Qdrant |
| 7 | Provision cache/queue | Redis |

**Combined sequence:** [TENANT_ISOLATION_STORAGE_ENCRYPTION Section 10](TENANT_ISOLATION_STORAGE_ENCRYPTION.md).

**Per-tenant isolation:** Each store uses dedicated namespaces and credentials. Cross-tenant access is denied by construction (IAM policy, REVOKE CONNECT, collection-per-tenant, ACL key pattern).

---

## 2. MinIO Provisioning

**Isolation spec:** [TENANT_ISOLATION_STORAGE_ENCRYPTION Section 2](TENANT_ISOLATION_STORAGE_ENCRYPTION.md).

### 2.1 Step-by-Step

1. **Create bucket**
   ```bash
   mc mb {alias}/tenant-{tenant_id}-bucket
   mc encrypt set sse-s3 {alias}/tenant-{tenant_id}-bucket
   ```
   Naming: 3–63 chars, lowercase, hyphens. Example: `tenant-abc-bucket`.

2. **Generate credentials**
   ```bash
   secret_key=$(openssl rand -base64 32)
   ```
   Store in SOPS-encrypted secrets file (Section 6).

3. **Create IAM user**
   ```bash
   mc admin user add {alias} tenant-{tenant_id}-access {secret_key}
   ```

4. **Create and attach IAM policy**
   Save policy to `tenant-{tenant_id}-policy.json`:
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
   Then:
   ```bash
   mc admin policy create {alias} tenant-{tenant_id}-policy tenant-{tenant_id}-policy.json
   mc admin policy attach {alias} tenant-{tenant_id}-policy --user=tenant-{tenant_id}-access
   ```

### 2.2 Bucket Structure

```
tenant-{tenant_id}-bucket/
  raw/                    # Original uploaded documents
  parsed/                 # Canonical JSON after parsing
  receipts/               # Intake receipts
  exports/                # Compliance evidence exports
```

### 2.3 Verification

```bash
mc alias set tenant-test http://{minio_host}:9000 tenant-{tenant_id}-access {secret_key}
mc ls tenant-test
# Expect: only tenant-{tenant_id}-bucket

mc ls tenant-test/tenant-{other_id}-bucket
# Expect: Access Denied

mc admin user info {alias} tenant-{tenant_id}-access
# Expect: PolicyName tenant-{tenant_id}-policy
```

### 2.4 Deprovisioning

```bash
mc rm --recursive --force {alias}/tenant-{tenant_id}-bucket
mc rb {alias}/tenant-{tenant_id}-bucket
mc admin user remove {alias} tenant-{tenant_id}-access
mc admin policy remove {alias} tenant-{tenant_id}-policy
```

**Verification:** `mc ls {alias}/tenant-{tenant_id}-bucket` → "bucket not found".

---

## 3. PostgreSQL Provisioning

**Isolation spec:** [TENANT_ISOLATION_STORAGE_ENCRYPTION Section 3](TENANT_ISOLATION_STORAGE_ENCRYPTION.md).

### 3.1 Step-by-Step

1. **Create database**
   ```sql
   CREATE DATABASE tenant_{tenant_id};
   ```

2. **Create user** (use password from SOPS secrets)
   ```sql
   CREATE USER tenant_{tenant_id}_user WITH ENCRYPTED PASSWORD '{password_from_sops}';
   ```

3. **Grant privileges**
   ```sql
   GRANT ALL PRIVILEGES ON DATABASE tenant_{tenant_id} TO tenant_{tenant_id}_user;
   REVOKE CONNECT ON DATABASE tenant_{tenant_id} FROM PUBLIC;
   ```

4. **Grant schema privileges** (connect to tenant DB)
   ```sql
   \c tenant_{tenant_id}
   GRANT ALL ON SCHEMA public TO tenant_{tenant_id}_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO tenant_{tenant_id}_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO tenant_{tenant_id}_user;
   ```

5. **pg_hba.conf** (network restriction)
   ```
   host  tenant_{tenant_id}  tenant_{tenant_id}_user  10.{tenant_octet}.0.0/16  scram-sha-256
   ```
   Reload: `SELECT pg_reload_conf();`

### 3.2 Verification

```bash
psql -l                    # Verify tenant_{tenant_id} exists
psql -c "\du"              # Verify tenant_{tenant_id}_user
psql -h {host} -U tenant_{tenant_id}_user -d tenant_{tenant_id}
# From tenant network: expect success

psql -h {host} -U tenant_{tenant_id}_user -d tenant_{other_id}
# Expect: permission denied
```

### 3.3 Deprovisioning

```sql
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'tenant_{tenant_id}';
DROP DATABASE tenant_{tenant_id};
DROP USER tenant_{tenant_id}_user;
```

Remove pg_hba.conf entry and reload. **Verification:** `\l` should not show `tenant_{tenant_id}`.

---

## 4. Qdrant Provisioning

**Isolation spec:** [TENANT_ISOLATION_STORAGE_ENCRYPTION Section 4](TENANT_ISOLATION_STORAGE_ENCRYPTION.md).

### 4.1 Step-by-Step

1. **Create collection**
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
   Vector size 768 is locked per TECH_DECISIONS.

2. **Application guards** (mandatory for all Qdrant operations)
   ```python
   def get_collection_name(tenant_id: str) -> str:
       return f"tenant_{tenant_id}"

   def verify_tenant_access(tenant_id: str, collection_name: str) -> None:
       expected = get_collection_name(tenant_id)
       if collection_name != expected:
           raise PermissionError(f"Tenant {tenant_id} cannot access {collection_name}")
   ```

### 4.2 Verification

```bash
curl -s http://localhost:6333/collections | jq '.result.collections[].name'
# Verify tenant_{tenant_id} in list
```

Insert test vector and search; results must be tenant-scoped. Call `verify_tenant_access(tenant_id, "tenant_other")` → PermissionError.

### 4.3 Deprovisioning

```http
DELETE /collections/tenant_{tenant_id}
```

**Verification:** `GET /collections/tenant_{tenant_id}` → 404.

---

## 5. Redis Provisioning

**Isolation spec:** [TENANT_ISOLATION_STORAGE_ENCRYPTION Section 5](TENANT_ISOLATION_STORAGE_ENCRYPTION.md).

### 5.1 Key Prefix Convention

All tenant keys: `tenant:{tenant_id}:`

| Use | Example |
|-----|---------|
| Cache | `tenant:{tenant_id}:cache:{key}` |
| Queue | `tenant:{tenant_id}:queue:{queue_name}` |
| Rate limit | `tenant:{tenant_id}:ratelimit:{endpoint}` |
| Session | `tenant:{tenant_id}:session:{session_id}` |

### 5.2 Step-by-Step

1. **Generate password** (store in SOPS)
   ```bash
   redis_password=$(openssl rand -base64 32)
   ```

2. **Create ACL user** (Redis >=6)
   ```
   ACL SETUSER tenant_{tenant_id}_user on >{password} ~tenant:{tenant_id}:* +@all -@dangerous
   ACL SAVE
   ```

### 5.3 Verification

```bash
redis-cli AUTH tenant_{tenant_id}_user {password}
redis-cli SET tenant:{tenant_id}:test value
# Expect: OK

redis-cli SET tenant:{other_id}:test value
# Expect: NOPERM
```

### 5.4 Deprovisioning

```bash
redis-cli --scan --pattern "tenant:{tenant_id}:*" | xargs -r redis-cli DEL
redis-cli ACL DELUSER tenant_{tenant_id}_user
redis-cli ACL SAVE
```

**Verification:** `redis-cli --scan --pattern "tenant:{tenant_id}:*"` → empty.

---

## 6. Credential Generation and SOPS

**Isolation spec:** [TENANT_ISOLATION_STORAGE_ENCRYPTION Section 6](TENANT_ISOLATION_STORAGE_ENCRYPTION.md).

### 6.1 Age Key Pair

```bash
mkdir -p .secrets/tenants/{tenant_id}
age-keygen -o .secrets/tenants/{tenant_id}/key.age
grep "public key:" .secrets/tenants/{tenant_id}/key.age | awk '{print $NF}' > .secrets/tenants/{tenant_id}/key.pub
chmod 600 .secrets/tenants/{tenant_id}/key.age
```

Store public key in registry: `UPDATE tenants SET age_public_key = '{public_key}' WHERE tenant_id = '{tenant_id}';`

### 6.2 Credential Generation

```bash
minio_secret=$(openssl rand -base64 32)
postgres_password=$(openssl rand -base64 32)
qdrant_api_key=$(openssl rand -base64 32)
redis_password=$(openssl rand -base64 32)
tenant_api_key=$(openssl rand -base64 32)
```

### 6.3 Secrets File Structure (Before Encryption)

```yaml
# .secrets/tenants/{tenant_id}/secrets.yaml
minio_access_key: "tenant-{tenant_id}-access"
minio_secret_key: "{minio_secret}"
postgres_password: "{postgres_password}"
qdrant_api_key: "{qdrant_api_key}"
redis_password: "{redis_password}"
tenant_api_key: "{tenant_api_key}"
```

### 6.4 SOPS Encryption

```bash
sops --age $(cat .secrets/tenants/{tenant_id}/key.pub) \
     --encrypt .secrets/tenants/{tenant_id}/secrets.yaml \
     > .secrets/tenants/{tenant_id}/secrets.enc.yaml
shred -u .secrets/tenants/{tenant_id}/secrets.yaml
```

### 6.5 Decryption (Application)

```bash
export SOPS_AGE_KEY_FILE=.secrets/tenants/{tenant_id}/key.age
sops --decrypt .secrets/tenants/{tenant_id}/secrets.enc.yaml
```

**Python helper:** See TENANT_ISOLATION_STORAGE_ENCRYPTION Section 6.5.

---

## 7. Combined Provisioning Sequence

**Reference:** [TENANT_ISOLATION_STORAGE_ENCRYPTION Section 10](TENANT_ISOLATION_STORAGE_ENCRYPTION.md).

### 7.1 Ordered Steps

| Step | Action | Rollback on Failure |
|------|--------|---------------------|
| 1 | Generate age key pair (Section 6.1) | Delete key files |
| 2 | Generate credentials (Section 6.2) | N/A (not persisted yet) |
| 3 | Create SOPS-encrypted secrets file (Section 6.4) | Delete secrets.enc.yaml, key files |
| 4 | Provision MinIO (Section 2) | mc rb, mc admin user remove, mc admin policy remove |
| 5 | Provision PostgreSQL (Section 3) | DROP DATABASE, DROP USER |
| 6 | Provision Qdrant (Section 4) | DELETE /collections/tenant_{id} |
| 7 | Provision Redis (Section 5) | ACL DELUSER, delete keys |
| 8 | Run cross-store verification (Section 9) | Roll back steps 4–7 in reverse |
| 9 | Register in tenant registry (endpoints, credentials ref) | Remove registry row |

**Error handling:** On failure at any step, execute rollback for all completed steps in reverse order. Emit `TENANT_PROVISION_FAILED` audit event with details of which step failed.

### 7.2 Audit Event After Step 8

After Step 8 (verification) passes, emit `TENANT_PROVISIONED` audit event before Step 9. **Reference:** [AUDIT_ARCHITECTURE Section 1.2](AUDIT_ARCHITECTURE.md).

```python
emit_audit_event(
    event_id=uuid.uuid7(),
    tenant_id=tenant_id,
    event_type="TENANT_PROVISIONED",
    resource_type="tenant",
    resource_id=tenant_id,
    details={
        "component": "provisioning-orchestrator",
        "status": "success",
        "stores_verified": ["minio", "postgresql", "qdrant", "redis"],
    },
    previous_event_id=None,
)
```

Then proceed to Step 9 (register in tenant registry).

---

## 8. Cross-Store Verification (Section 9)

**Reference:** [TENANT_ISOLATION_STORAGE_ENCRYPTION Section 9](TENANT_ISOLATION_STORAGE_ENCRYPTION.md).

### 8.1 Checklist

- [ ] MinIO: tenant user only accesses tenant bucket; cross-tenant access denied
- [ ] PostgreSQL: tenant user only connects to tenant database; cross-db denied
- [ ] Qdrant: `verify_tenant_access` blocks wrong collection; collection exists
- [ ] Redis: ACL user only accesses `tenant:{id}:*`; cross-tenant denied
- [ ] Encryption: tenant secrets decrypt only with tenant age key

### 8.2 Verification Report Format

```json
{
  "tenant_id": "{tenant_id}",
  "checks": [
    {"store": "minio", "test": "cross_tenant_access", "result": "DENIED", "timestamp": "2026-02-11T12:00:00Z"},
    {"store": "postgresql", "test": "cross_db_connect", "result": "DENIED", "timestamp": "2026-02-11T12:00:01Z"},
    {"store": "qdrant", "test": "collection_exists", "result": "OK", "timestamp": "2026-02-11T12:00:02Z"},
    {"store": "redis", "test": "cross_tenant_prefix", "result": "DENIED", "timestamp": "2026-02-11T12:00:03Z"}
  ],
  "overall_pass": true
}
```

Store verification results for audit (AUDIT_ARCHITECTURE).

---

## 9. Cross-References Table

| Store | Isolation Spec | Section |
|-------|----------------|---------|
| MinIO | TENANT_ISOLATION_STORAGE_ENCRYPTION | Section 2 |
| PostgreSQL | TENANT_ISOLATION_STORAGE_ENCRYPTION | Section 3 |
| Qdrant | TENANT_ISOLATION_STORAGE_ENCRYPTION | Section 4 |
| Redis | TENANT_ISOLATION_STORAGE_ENCRYPTION | Section 5 |
| Credentials/SOPS | TENANT_ISOLATION_STORAGE_ENCRYPTION | Section 6 |
| Verification | TENANT_ISOLATION_STORAGE_ENCRYPTION | Section 9 |
| Combined sequence | TENANT_ISOLATION_STORAGE_ENCRYPTION | Section 10 |
| Audit event schema | AUDIT_ARCHITECTURE | Section 1 |
| Provisioning PRD | PRD | Section 3.4 |
| Deprovisioning PRD | PRD | Section 3.6 |

---

## 10. Implementation Checklist

- [ ] Implement MinIO provisioning (create bucket, IAM user, policy, attach)
- [ ] Implement PostgreSQL provisioning (CREATE DATABASE, CREATE USER, GRANT, REVOKE)
- [ ] Implement Qdrant provisioning (PUT /collections)
- [ ] Implement Redis provisioning (ACL SETUSER)
- [ ] Implement credential generation + SOPS encrypt
- [ ] Implement combined sequence with rollback
- [ ] Implement cross-store verification
- [ ] Emit TENANT_PROVISIONED after verification
- [ ] Implement deprovisioning for each store (reverse order)
