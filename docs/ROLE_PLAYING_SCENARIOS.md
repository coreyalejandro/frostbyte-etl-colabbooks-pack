# Role-Playing Scenarios: Frostbyte ETL Pipeline

**Version:** 1.0  
**Created:** 2026-02-11  
**Requirement traceability:** SCENARIO-01, SCENARIO-02  
**References:** [PRD.md](PRD.md), [AUDIT_ARCHITECTURE.md](AUDIT_ARCHITECTURE.md), [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md)

---

## 1. Customer Success Scenarios

### Scenario A: New Vendor Onboarding

**Context:** A new vendor (acme-corp) is preparing their first batch submission. Dana (vendor data ops lead) has received tenant credentials and needs to submit a batch of 50 PDF contracts.

**Situation:**
- Dana has never used the Frostbyte API before
- She has the JWT token, tenant_id (`acme-corp`), and the 50 files
- She is unsure about the manifest format and SHA-256 computation

**Expected Actions:**
1. Provide Dana with the [VENDOR_OPERATIONS_GUIDE](VENDOR_OPERATIONS_GUIDE.md)
2. Walk through: (a) manifest schema, (b) how to compute SHA-256 (sha256sum / Get-FileHash), (c) curl or script example for batch submission
3. Recommend a **small test batch** (e.g., 2–3 files) first to verify connectivity and format
4. Confirm she can reach `https://acme-corp.pipeline.frostbyte.io/health` and gets 200

**Escalation Criteria:**
- Token doesn't work → escalate to platform admin (token scope, expiration)
- Health check fails → escalate to engineering (tenant not provisioned or gateway down)
- All files rejected on first batch → debug manifest together; if schema is correct and still failing → engineering

**Resolution Steps:**
- Dana successfully submits test batch, receives 202 with accepted count
- She runs full batch; any rejected files get clear reasons in the receipt
- She polls batch status until all files show `indexed`

---

### Scenario B: Batch Failure with Rejected Files

**Context:** Dana submitted a batch of 100 files. The receipt shows 95 accepted, 5 rejected with reason `CHECKSUM_MISMATCH`.

**Situation:**
- Dana is confident the files weren't modified after hashing
- She has a deadline; needs to understand quickly whether to resubmit or escalate

**Expected Actions:**
1. Ask Dana to recompute SHA-256 for one rejected file: `sha256sum file_042.pdf`
2. Compare with manifest value—if they match, something is wrong on our side (possible corruption in transfer, multipart parsing bug)
3. If hashes differ: common causes—(a) file was modified after hashing, (b) wrong file in manifest (copy-paste error), (c) line endings in text files
4. For the 5 rejected files: have Dana resubmit only those 5 in a new batch with corrected hashes (if the issue was Dana-side)

**Escalation Criteria:**
- Hash matches manifest but we rejected → engineering (intake bug)
- Consistent CHECKSUM_MISMATCH across many batches → engineering (possible proxy/load balancer altering bodies)
- Dana cannot resolve and deadline is urgent → prioritize engineering ticket

**Resolution Steps:**
- If Dana-side: she fixes manifest, resubmits 5 files; all accepted
- If platform-side: engineering reproduces, fixes, deploys; Dana resubmits

---

### Scenario C: Compliance Inquiry (Audit Export)

**Context:** A customer's legal team requests compliance evidence: "Prove that document X was ingested on date Y and show the full provenance chain from intake to retrieval."

**Situation:**
- CS needs to fulfill the request without deep technical knowledge
- Audit data exists; export format and access must be clear

**Expected Actions:**
1. Identify the document (doc_id or file_id) and tenant_id
2. Use Audit API or export procedure per [AUDIT_ARCHITECTURE](AUDIT_ARCHITECTURE.md) Section 3
3. Export events: by tenant + time range, or by resource_id (document)
4. Provide JSON Lines export + manifest (SHA-256 of export file for integrity)
5. Explain provenance chain: BATCH_RECEIVED → DOCUMENT_INGESTED → DOCUMENT_PARSED → ... → RETRIEVAL_EXECUTED

**Escalation Criteria:**
- Audit API unavailable or access denied → engineering
- Customer needs SIEM integration format → provide export spec; if custom format needed → engineering
- Legal asks for something out of scope (e.g., cross-tenant data) → explain isolation; no cross-tenant audit

**Resolution Steps:**
- CS exports audit events for the document and date range
- Sends JSON Lines file + manifest to customer
- Customer verifies integrity (SHA-256) and reviews event chain

---

## 2. Deployed Engineer Scenarios

### Scenario A: Parse Failure (DOCUMENT_PARSE_FAILED)

**Context:** A document fails parsing. The batch status shows `parse_failed` for file_id `file_017`. Dana reports that the same PDF opens fine in Adobe.

**Situation:**
- Parse worker logged DOCUMENT_PARSE_FAILED
- Need to diagnose whether it's: (a) corrupt file, (b) unsupported PDF flavor, (c) Docling/Unstructured bug, (d) resource constraint (OOM, timeout)

**Expected Actions:**
1. Fetch the file from object store: `raw/{tenant_id}/file_017/{sha256}`
2. Run parser locally on the file: `python -c "from docling import ..."` or equivalent
3. Check parse worker logs for stack trace, OOM, or timeout
4. If local parse succeeds: possible worker resource issue (memory, CPU) or environment difference
5. If local parse fails: document may use a PDF feature we don't support; add to known limitations or file parser bug

**Escalation Criteria:**
- Parser crash with no clear cause → upstream Docling/Unstructured issue
- Many documents of same type failing → possible regression or format not supported
- OOM on large PDFs → increase worker memory or add chunked processing

**Resolution Steps:**
- If fixable: patch parser config or upgrade library; redeploy; retry job
- If document unsupported: inform Dana; add to documentation; optionally request format support
- Emit DOCUMENT_PARSE_FAILED with details for audit; include in acceptance report

---

### Scenario B: Tenant Provisioning Stuck

**Context:** A new tenant (`newco`) provisioning has been running for 20 minutes. Normally it completes in 5–10 minutes. Tenant state is `PROVISIONING`.

**Situation:**
- Provisioning orchestrator may have failed mid-way
- Need to determine: (a) which step failed, (b) what resources were created, (c) whether to retry or rollback

**Expected Actions:**
1. Check provisioning orchestrator logs for the last successful step and first failure
2. List Hetzner resources by label: `tenant_id=newco` (servers, networks, firewalls, volumes)
3. Follow [DEPLOYMENT_ARCHITECTURE Section 2.3](DEPLOYMENT_ARCHITECTURE.md) rollback procedure if needed
4. Common failures: firewall apply timeout, volume attach slow, storage provisioning (MinIO/PostgreSQL) failure
5. If storage step failed: check STORAGE_LAYER_PLAN verification; credentials, bucket creation, etc.

**Escalation Criteria:**
- Hetzner API rate limit or outage → wait and retry; or contact Hetzner
- Resource leak (partial create, no rollback) → manual cleanup per runbook; escalate if unclear
- Database migration failure → check migration order; fix migration; re-run

**Resolution Steps:**
- Identify failed step
- If retryable: fix config/transient error; resume from failure point or restart from beginning (with rollback of partial resources)
- If rollback: delete resources in reverse order of creation; set tenant state to FAILED; emit audit event; notify platform owner

---

### Scenario C: Audit Query for SIEM Integration

**Context:** A customer wants to ship Frostbyte audit events to their SIEM (e.g., Splunk). They need the export format, authentication, and any limitations.

**Situation:**
- Engineer needs to explain: (a) export format (JSON Lines), (b) manifest with SHA-256, (c) how to authenticate (Audit API if available), (d) rate limits, (e) event schema

**Expected Actions:**
1. Provide [AUDIT_ARCHITECTURE](AUDIT_ARCHITECTURE.md) Section 3 (query patterns, export format)
2. Export format: JSON Lines, one event per line; manifest with `file_sha256`, `event_count`, `from`, `to`, `tenant_id`
3. Authentication: Audit API uses separate read-only credentials; scope limited to customer's tenant_id
4. Rate limits: document in API spec; typically generous for export (bulk pull)
5. Event schema: event_id, tenant_id, event_type, timestamp, resource_type, resource_id, details, previous_event_id

**Escalation Criteria:**
- Customer needs real-time streaming → not in v1; document as future enhancement
- Cross-tenant export request → deny; explain isolation
- Custom schema (e.g., CEF) → provide mapping doc or script; if complex → engineering

**Resolution Steps:**
- Document export procedure and schema for customer
- Customer configures SIEM connector (or cron + curl) to pull exports periodically
- Customer verifies integrity using manifest SHA-256

---

## 3. Scenario Summary

| Persona | Scenarios | Key Skills |
|---------|-----------|------------|
| **Customer Success** | Onboarding, batch failure, compliance | Vendor guide, manifest, escalation paths |
| **Deployed Engineer** | Parse failure, provisioning, audit/SIEM | Runbooks, logs, DEPLOYMENT_ARCHITECTURE, AUDIT_ARCHITECTURE |
