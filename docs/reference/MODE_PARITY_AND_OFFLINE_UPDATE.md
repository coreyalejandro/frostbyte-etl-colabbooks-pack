# Mode Parity and Offline Update Cycle

**Version:** 1.0  
**Created:** 2026-02-11  
**Requirement traceability:** DEPLOY-03 (mode parity matrix), DEPLOY-04 (offline update cycle)  
**References:** [TECH_DECISIONS.md](TECH_DECISIONS.md) Section 4, [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md), [PRD.md](PRD.md)

---

## 1. Mode Parity Matrix

Every feature is explicitly documented with its online and offline status.

### 1.1 Feature Status Table

| Feature | Online | Offline | Notes |
|---------|--------|---------|-------|
| **Intake** | Full | Full | Same API, auth, manifest, MIME, checksum, malware scan |
| **Parsing** | Full | Full | Docling + Unstructured; identical canonical JSON |
| **Policy (PII)** | Full | Full | Same NER/Presidio rules, REDACT/FLAG/BLOCK |
| **Policy (Classification)** | Full | Full | Rule + ML; offline may use lighter ML model |
| **Policy (Injection)** | Full | Full | DOCUMENT_SAFETY patterns, heuristic scorer |
| **Embedding** | OpenRouter 768d | Nomic v1.5 768d | Dimension parity; semantic divergence (see Divergences) |
| **Indexing** | Full | Full | Three-store write, Qdrant, same schema |
| **Serving (Retrieval)** | Full | Full | RAG retrieval, retrieval proof, cite-only |
| **Serving (Generation)** | Optional | Optional | Same; both can disable via config |
| **Tenant provisioning** | Dynamic (Hetzner) | Static (compose) | Offline: single tenant per deployment |
| **Tenant config** | Registry JSONB | Static JSON file | Same schema (PRD Appendix G) |
| **Audit stream** | Central aggregator | Local PostgreSQL | Same event schema; aggregation differs (see Divergences) |
| **Malware scanning** | ClamAV (live sigs) | ClamAV (bundled) | Offline signatures freeze at bundle build (see Divergences) |
| **Secrets** | SOPS + age | SOPS + age or .env | Same mechanism; offline may pre-decrypt |
| **Monitoring** | Prometheus + Grafana + Loki | Prometheus + Grafana (opt) | No Loki offline; logs via Docker (see Divergences) |
| **API gateway** | Traefik (TLS, routing) | N/A (localhost) | Offline: port mapping only |
| **Network isolation** | Hetzner firewall | Docker internal: true | Both structural; no cross-tenant traffic |
| **Data export** | Audit API, pg_dump, mc | export.sh script | Same export formats |

### 1.2 Parity Summary

| Category | Online | Offline | Parity |
|----------|--------|---------|--------|
| Pipeline (intake → serving) | Full | Full | Yes |
| Tenant lifecycle | Dynamic | Static (1 tenant) | Partial |
| Observability | Full stack | Optional, no Loki | Partial |
| Malware signatures | Live update | Frozen | Partial |
| Embedding model | OpenRouter | Nomic | Partial (dimension match, semantic diff) |

---

## 2. Explicit Divergences

Every divergence has a documented reason and workaround.

### Divergence 1: Embedding Model

**Reason:** Online uses OpenRouter (OpenAI text-embedding-3-small); offline uses Nomic embed-text v1.5. Both produce 768d vectors for storage compatibility, but semantic similarity differs.

**Impact:** Cross-mode search (query in one mode, search vectors from the other) works but may yield suboptimal ranking.

**Workaround:** For optimal quality when migrating data between modes: (1) re-embed all chunks with the target mode's model, (2) re-index into Qdrant. Dimension parity allows storage; re-embedding improves retrieval quality.

### Divergence 2: ClamAV Signature Currency

**Reason:** Online can run `freshclam` for live signature updates. Offline has no outbound network; signatures ship in the bundle and freeze at build time.

**Impact:** Offline may not detect malware whose signatures were released after the bundle was built.

**Workaround:** (1) Signature-only update tarball: deliver main.cvd, daily.cvd, bytecode.cvd via sneakernet; (2) verify tarball signature; (3) extract to ClamAV data volume; (4) restart ClamAV. No full bundle rebuild. (2) Accept risk for air-gapped environments where threat model is document-format malware, not zero-days.

### Divergence 3: Log Aggregation

**Reason:** Online uses Loki for centralized, searchable logs. Offline bundle excludes Loki (reduces size, no outbound); logs are Docker stdout/stderr only.

**Impact:** Offline has no full-text log search or correlation across services.

**Workaround:** (1) Use `docker compose logs -f` for tail; (2) Audit events (compliance-critical) are always in PostgreSQL, not operational logs; (3) For deeper analysis, run `export.sh` and ship audit export to a connected environment.

### Divergence 4: Audit Stream Aggregation

**Reason:** Online aggregates audit events from all tenants into a central audit plane. Offline keeps events local (single-tenant deployment).

**Impact:** No central visibility during offline operation.

**Workaround:** (1) Export audit as JSON Lines via export.sh; (2) Import into central audit plane when offline env later connects; (3) Export format is identical (AUDIT_ARCHITECTURE).

### Divergence 5: Tenant Provisioning

**Reason:** Online provisions via Hetzner API (dynamic). Offline has no cloud API; exactly one tenant per host.

**Impact:** Multi-tenant offline requires multiple hosts (one tenant per host).

**Workaround:** Deploy one offline bundle per tenant; each bundle has its own docker-compose with isolated resources.

### Divergence 6: API Gateway / TLS

**Reason:** Online uses Traefik for TLS termination and routing. Offline is single-host, localhost-only; TLS not required for local access.

**Impact:** Offline access is HTTP on 127.0.0.1; no TLS in default config.

**Workaround:** If TLS needed (e.g., reverse proxy in front), add Traefik or Caddy to the offline bundle and configure certificates manually.

---

## 3. Offline Update Cycle

### 3.1 Signing Mechanism

**Tool:** age (asymmetric encryption) + SHA-256 checksums.

**Key layout:**
- Frostbyte release key pair: `frostbyte-release.pub` (distributed to operators), `frostbyte-release.key` (held by release manager)
- Bundle tarball: `frostbyte-offline-bundle-v1.1.tar.gz`
- Signature file: `frostbyte-offline-bundle-v1.1.tar.gz.sig` (age signature)
- Manifest: `MANIFEST.json` inside tarball, also signed; contains SHA-256 of tarball and all nested files

**Signing procedure (release manager):**
```bash
# Create bundle tarball
tar -czvf frostbyte-offline-bundle-v1.1.tar.gz frostbyte-offline-bundle-v1.1/

# Compute checksum
sha256sum frostbyte-offline-bundle-v1.1.tar.gz > frostbyte-offline-bundle-v1.1.tar.gz.sha256

# Sign with age (produces .age encrypted checksum or use minisign/openssl for detached sig)
age -e -R frostbyte-release.pub -o frostbyte-offline-bundle-v1.1.tar.gz.sig frostbyte-offline-bundle-v1.1.tar.gz.sha256
# Alternatively: minisign -S -s release.key -m frostbyte-offline-bundle-v1.1.tar.gz
```

### 3.2 Verification Procedure

**Operator steps:**
```bash
# 1. Obtain frostbyte-release.pub (from trusted channel)
# 2. Download bundle and signature
# 3. Verify checksum (if using separate .sha256)
sha256sum -c frostbyte-offline-bundle-v1.1.tar.gz.sha256

# 4. Verify age signature (or minisign -V)
age -d -i frostbyte-release.key frostbyte-offline-bundle-v1.1.tar.gz.sig

# 5. Extract and verify MANIFEST.json internal checksums
tar -xzf frostbyte-offline-bundle-v1.1.tar.gz
cd frostbyte-offline-bundle-v1.1
# Verify each file in MANIFEST against listed sha256
```

**Verification script (verify_bundle.sh):**
```bash
#!/bin/bash
# Input: bundle tarball path, frostbyte-release.pub path
# 1. Verify tarball sha256 if .sha256 provided
# 2. Verify signature
# 3. Extract, validate MANIFEST.json
# 4. Exit 0 if all pass, 1 otherwise
```

### 3.3 Migration Steps

**Schema migrations (Alembic):**
1. Bundle includes `migrations/` with SQL or Alembic versions
2. During update: `docker compose run --rm api alembic upgrade head` (or equivalent)
3. Migrations are backward-compatible where possible; breaking changes require documented procedure

**Data migrations:**
- If schema change requires data backfill: include migration script in bundle
- Script must be idempotent and safe to re-run
- Document rollback: previous bundle version + backup restore

**Migration order:**
1. Stop application containers (keep postgres, minio, qdrant, redis running)
2. Backup: `export.sh` or `pg_dump`
3. Run Alembic upgrade
4. Run data migration scripts (if any)
5. Pull/load new images
6. Start application containers with new images
7. Verify: `verify.sh`
8. If failure: restore backup, revert to previous images

### 3.4 Zero-Downtime Cutover

**Strategy:** Rolling restart (offline single-host).

**Steps:**
1. **Prepare:** Load new images, run migrations (Alembic), ensure new containers can start
2. **Cutover:** `docker compose up -d` (recreate changed services)
3. **Drain:** Celery workers drain in-flight tasks (stop accepting new; wait for current to finish, or timeout)
4. **Restart workers:** `docker compose up -d celery-worker` with new image
5. **Restart gateway/serving:** `docker compose up -d intake-gateway serving`
6. **Verify:** `curl http://127.0.0.1:8080/health` and smoke test

**Downtime:** Typically 10–30 seconds for gateway/serving restart. Workers: ~0 if drain completes before restart; else task re-queue and retry.

**Blue-green alternative:** Not typical for single-host offline; would require two compose stacks and a proxy switch. Rolling restart is the default.

### 3.5 Signature-Only Updates (ClamAV)

For ClamAV signature updates without full bundle:

1. Frostbyte publishes `clamav-signatures-YYYYMMDD.tar.gz` + `.sig`
2. Operator verifies signature, extracts .cvd files to `./clamav-data/`
3. Update docker-compose volume mount or copy into existing ClamAV volume
4. `docker compose restart clamav`
5. No application restart required

---

## 4. Cross-References

| Topic | Document | Section |
|-------|----------|---------|
| Component compatibility | TECH_DECISIONS | 4 |
| Offline bundle structure | DEPLOYMENT_ARCHITECTURE | 3 |
| Audit export format | AUDIT_ARCHITECTURE | 3 |
| Tenant config schema | PRD | Appendix G |
