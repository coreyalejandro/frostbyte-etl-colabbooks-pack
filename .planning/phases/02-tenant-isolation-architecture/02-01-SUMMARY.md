# Plan 02-01: Tenant Isolation Hetzner — Execution Summary

**Plan:** 02-01-PLAN.md
**Executed:** 2026-02-11
**Status:** Complete

## Deliverable

| Artifact | Path | Purpose |
|----------|------|---------|
| Hetzner provisioning and network boundaries | `docs/TENANT_ISOLATION_HETZNER.md` | Complete specification for ISOL-01 and ISOL-04 |

## What Was Produced

`docs/TENANT_ISOLATION_HETZNER.md` (688 lines) covering:

1. **Provisioning sequence** — PRD Section 3.4 steps 1–11 mapped to concrete Hetzner API calls
2. **Compute** — Server creation (`POST /servers`), polling, label filtering, server type table, hcloud SDK examples
3. **Network** — Private network creation, CIDR allocation (tenant_octet 1–254), CIDR normalization utility, 100-server limit note
4. **Volume** — Volume creation, attachment, mount path convention
5. **DNS** — Record pattern, external DNS integration point, health URL
6. **Tenant registry** — SQL INSERT, audit event, health verification sequence
7. **Deprovisioning** — PRD Section 3.6 steps 6–7: graceful shutdown, server/network/firewall/volume deletion, verification, rollback handling
8. **Firewall rules** — Inbound (HTTPS gateway, SSH bastion, internal), outbound (OpenRouter, internal, DNS), implicit deny behavior (Pitfall 4), cross-tenant denial proof
9. **Docker offline** — `internal: true` network, IPAM, service mapping, verification commands, comparison table
10. **Verification runbook** — Step-by-step for online and offline modes, evidence JSON format

## Verification Results

| Criterion | Required | Actual |
|-----------|----------|--------|
| API call references | ≥ 15 | 40 |
| tenant_id occurrences | ≥ 20 | 29 |
| CIDR/ip_range references | ≥ 10 | 32 |
| PRD cross-references | ≥ 3 | 9 |
| Total lines | ≥ 600 | 688 |
| Mermaid diagram | ≥ 1 | 1 |
| Firewall ALLOW/DENY | ≥ 10 | 12 |
| Direction (in/out) | ≥ 8 | 27 |
| internal: true | ≥ 3 | 7 |
| verification references | ≥ 10 | 21 |
| cross-tenant references | ≥ 3 | 5 |
| Implicit outbound ACCEPT documented | ≥ 1 | 3 |

## Key Links Established

- `docs/TENANT_ISOLATION_HETZNER.md` → `docs/PRD.md` Section 3.4 (provisioning steps)
- `docs/TENANT_ISOLATION_HETZNER.md` → `docs/PRD.md` Section 3.6 (deprovisioning steps)
- `docs/TENANT_ISOLATION_HETZNER.md` → `docs/TECH_DECISIONS.md` (hcloud SDK, cx22, nbg1)

## Next Step

Plan 02-02: Storage isolation (MinIO, PostgreSQL, Qdrant namespaces per tenant).
