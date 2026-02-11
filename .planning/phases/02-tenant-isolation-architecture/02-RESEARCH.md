# Phase 2: Tenant Isolation Architecture - Research

**Researched:** 2026-02-09
**Domain:** Multi-tenant infrastructure isolation (compute, storage, network, encryption)
**Confidence:** MEDIUM (web search verified with official sources; some implementation details require hands-on validation)

## Summary

Phase 2 requires specifying per-tenant isolation across four layers: Hetzner Cloud provisioning, storage namespaces, encryption key management, and network boundaries. The research reveals that Hetzner Cloud provides explicit isolation primitives (Projects, private networks, firewalls, labels) but requires manual orchestration since there's no native multi-tenancy construct like AWS Organizations. Storage isolation follows industry-standard patterns: separate MinIO buckets with IAM policies, separate PostgreSQL databases with dedicated users, and Qdrant collection-per-tenant with optional tiered multitenancy. Encryption key management uses SOPS + age for envelope encryption with a three-tier key hierarchy: age recipient keys (KEK) -> SOPS data keys (DEK) -> encrypted secrets. Network isolation in online mode uses Hetzner Cloud firewalls with explicit allow/deny rules and private networks; offline mode uses Docker Compose `internal: true` networks that block all outbound connectivity by preventing gateway configuration.

The research confirms that all chosen technologies support the required isolation patterns, with verification methods available for each layer. The primary implementation challenge is orchestrating the provisioning sequence and maintaining per-tenant key-to-resource mappings across the control plane registry.

**Primary recommendation:** Use Hetzner Cloud labels as the primary tenant identity mechanism (tenant_id label on all resources), implement envelope encryption with per-tenant age keys stored in the control plane secret manager, and define concrete firewall rules early in planning to avoid ambiguity during implementation.

## Standard Stack

The established libraries/tools for multi-tenant infrastructure isolation in this domain:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hcloud SDK (Python) | >=2.10 | Hetzner Cloud API client | Official SDK, supports all Hetzner primitives (servers, networks, firewalls, volumes) |
| SOPS | >=3.8 | Secrets management with envelope encryption | Industry standard for GitOps-friendly encrypted secrets, supports age integration |
| age | >=1.2 | Asymmetric encryption for SOPS | Modern replacement for GPG, simple key format, recommended by SOPS maintainers |
| MinIO Client (mc) | >=2023 | MinIO administration CLI | Official tool for bucket policy, user, and credential management |
| PostgreSQL | >=16 | Relational database | Mature multi-tenant patterns (database-per-tenant, RLS), pg_hba.conf for network isolation |
| Qdrant | >=1.13 | Vector database | Native multitenancy via collections or tiered sharding (v1.16+) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Docker Compose | >=2.29 | Container orchestration for offline mode | Offline deployment bundle, `internal: true` network isolation |
| Traefik | v3 | API gateway / reverse proxy | Online mode control plane routing, TLS termination |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hetzner Cloud | AWS / GCP / Azure | Hyperscalers have native multi-account/project constructs but higher cost; Hetzner requires manual isolation orchestration |
| SOPS + age | HashiCorp Vault | Vault provides dynamic secrets and centralized KMS but adds operational complexity; SOPS is GitOps-native |
| Database-per-tenant | PostgreSQL RLS (Row-Level Security) | RLS is simpler ops but weaker isolation; one query without tenant filter leaks all data |
| Collection-per-tenant (Qdrant) | Payload-based filtering in single collection | Single collection is simpler but payload filtering is fragile; collection-per-tenant provides stronger isolation |

**Installation:**

```bash
# Hetzner Cloud SDK
pip install hcloud>=2.10

# SOPS and age (binary downloads or package manager)
# macOS
brew install sops age

# Linux
wget https://github.com/getsops/sops/releases/download/v3.8.0/sops-v3.8.0.linux.amd64
wget https://github.com/FiloSottile/age/releases/download/v1.2.0/age-v1.2.0-linux-amd64.tar.gz

# MinIO Client
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
```

## Architecture Patterns

### Recommended Provisioning Sequence

The nine-step sequence from ARCHITECTURE.md expanded with Hetzner API specifics:

```
1. Create Hetzner Cloud Project (or use tenant-scoped API token)
   └─> No direct API: Projects managed via Hetzner Cloud Console
   └─> Alternative: Use label-based isolation within a single Project

2. Provision compute:
   POST /servers
   {
     "name": "tenant-{tenant_id}-worker-1",
     "server_type": "cx22",  // 2 vCPU, 4GB RAM
     "image": "ubuntu-22.04",
     "location": "nbg1",
     "labels": {
       "tenant_id": "{tenant_id}",
       "environment": "production",
       "role": "worker"
     },
     "networks": [network_id],
     "firewalls": [{"firewall": firewall_id}]
   }

3. Provision private network:
   POST /networks
   {
     "name": "tenant-{tenant_id}-private",
     "ip_range": "10.{tenant_seq}.0.0/16",
     "labels": {"tenant_id": "{tenant_id}"},
     "subnets": [{
       "type": "cloud",
       "ip_range": "10.{tenant_seq}.1.0/24",
       "network_zone": "eu-central"
     }]
   }

4. Provision firewall:
   POST /firewalls
   {
     "name": "tenant-{tenant_id}-fw",
     "labels": {"tenant_id": "{tenant_id}"},
     "rules": [
       // Inbound: HTTPS from API gateway only
       {
         "direction": "in",
         "protocol": "tcp",
         "port": "443",
         "source_ips": ["{api_gateway_ip}/32"]
       },
       // Inbound: Internal traffic within tenant network
       {
         "direction": "in",
         "protocol": "tcp",
         "port": "any",
         "source_ips": ["10.{tenant_seq}.0.0/16"]
       },
       // Outbound: OpenRouter API (online mode only)
       {
         "direction": "out",
         "protocol": "tcp",
         "port": "443",
         "destination_ips": ["{openrouter_cidr}"]
       },
       // Outbound: Internal traffic
       {
         "direction": "out",
         "protocol": "tcp",
         "port": "any",
         "destination_ips": ["10.{tenant_seq}.0.0/16"]
       }
     ],
     "apply_to": [{"label_selector": "tenant_id={tenant_id}"}]
   }

5. Provision volumes:
   POST /volumes
   {
     "name": "tenant-{tenant_id}-data",
     "size": 100,  // GB
     "location": "nbg1",
     "labels": {"tenant_id": "{tenant_id}"},
     "format": "ext4"
   }

6. Provision storage:
   // MinIO: Create bucket + IAM user
   mc mb tenant-{tenant_id}-minio/tenant-{tenant_id}-bucket
   mc admin user add tenant-{tenant_id}-minio {access_key} {secret_key}
   mc admin policy attach tenant-{tenant_id}-minio {policy} --user={access_key}

   // PostgreSQL: Create database + user
   CREATE DATABASE tenant_{tenant_id};
   CREATE USER tenant_{tenant_id}_user WITH PASSWORD '{password}';
   GRANT ALL PRIVILEGES ON DATABASE tenant_{tenant_id} TO tenant_{tenant_id}_user;

   // Qdrant: Create collection
   PUT /collections/tenant_{tenant_id}
   {
     "vectors": {
       "size": 768,
       "distance": "Cosine"
     }
   }

7. Generate secrets:
   // Per-tenant age key
   age-keygen -o tenant-{tenant_id}.age

   // SOPS-encrypted secrets file
   sops --age $(cat tenant-{tenant_id}.age.pub) \
        --encrypt tenant-{tenant_id}-secrets.yaml

8. Configure DNS:
   {tenant_id}.pipeline.frostbyte.io -> {tenant_api_ip}

9. Register in Tenant Registry:
   INSERT INTO tenants (tenant_id, state, endpoints, health_url, created_at)
   VALUES ('{tenant_id}', 'provisioned', '...', '...', NOW());

   // Emit audit event
   INSERT INTO audit_events (event_type, tenant_id, details)
   VALUES ('TENANT_PROVISIONED', '{tenant_id}', '...');
```

### Pattern 1: Hetzner Label-Based Isolation

**What:** Use labels as the primary tenant identity mechanism on all Hetzner Cloud resources (servers, networks, firewalls, volumes). Labels enable dynamic filtering via label selectors.

**When to use:** Always. Every resource provisioned for a tenant must have `tenant_id` label.

**Example:**

```python
# Source: Hetzner Cloud API documentation
from hcloud import Client
from hcloud.servers.domain import Server

client = Client(token="{api_token}")

# Create server with tenant label
server = client.servers.create(
    name=f"tenant-{tenant_id}-worker-1",
    server_type="cx22",
    image="ubuntu-22.04",
    labels={"tenant_id": tenant_id, "role": "worker"}
)

# Filter resources by tenant
tenant_servers = client.servers.get_all(label_selector=f"tenant_id={tenant_id}")
```

**Verification:**

```python
# List all servers for a tenant
servers = client.servers.get_all(label_selector=f"tenant_id={tenant_id}")
assert all(s.labels.get("tenant_id") == tenant_id for s in servers)

# Verify no cross-tenant resources
other_tenant_servers = client.servers.get_all(
    label_selector=f"tenant_id!={tenant_id}"
)
# Should return servers for other tenants only
```

### Pattern 2: Envelope Encryption with SOPS + age

**What:** Three-tier key hierarchy: age recipient keys (KEK) -> SOPS data keys (DEK) -> encrypted secrets. Each tenant gets a dedicated age key pair.

**When to use:** For all per-tenant secrets (DB passwords, API keys, object store credentials).

**Example:**

```bash
# Source: SOPS documentation + age specification
# 1. Generate per-tenant age key
age-keygen -o .secrets/tenant-abc.age
# Public key: age1hl5v2xfx8lc8n3z9x4q7r5t6y8u9o0p2a4s6d8f

# 2. Create secrets file for tenant
cat > tenant-abc-secrets.yaml <<EOF
db_password: changeme123
minio_access_key: tenant_abc_key
minio_secret_key: secret456
EOF

# 3. Encrypt with SOPS using tenant's age key
sops --age age1hl5v2xfx8lc8n3z9x4q7r5t6y8u9o0p2a4s6d8f \
     --encrypt tenant-abc-secrets.yaml > tenant-abc-secrets.enc.yaml

# 4. Decrypt (requires private key in $SOPS_AGE_KEY_FILE or stdin)
export SOPS_AGE_KEY_FILE=.secrets/tenant-abc.age
sops --decrypt tenant-abc-secrets.enc.yaml
```

**Key Hierarchy:**

```
age recipient key (KEK, per-tenant)
  └─> SOPS data key (DEK, generated per-file, 256-bit AES)
      └─> Individual secret values (encrypted with AES256_GCM)
```

**Rotation procedure:**

```bash
# Source: SOPS key rotation documentation
# 1. Generate new age key
age-keygen -o .secrets/tenant-abc-new.age

# 2. Rotate: decrypt with old key, encrypt with new key
sops --rotate \
     --add-age $(cat .secrets/tenant-abc-new.age.pub) \
     --rm-age $(cat .secrets/tenant-abc.age.pub) \
     --in-place tenant-abc-secrets.enc.yaml

# 3. Update key reference in control plane registry
UPDATE tenants SET age_public_key = '{new_public_key}'
WHERE tenant_id = 'abc';

# 4. Securely delete old private key
shred -u .secrets/tenant-abc.age
```

### Pattern 3: Storage Namespace Isolation

**What:** Each tenant gets isolated namespaces in all three stores: MinIO bucket, PostgreSQL database, Qdrant collection.

**When to use:** Always. No shared namespaces across tenants.

**Example (MinIO):**

```bash
# Source: MinIO bucket policy documentation
# Create bucket
mc mb minio-prod/tenant-abc-bucket

# Create IAM policy limiting access to tenant bucket only
cat > tenant-abc-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::tenant-abc-bucket"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::tenant-abc-bucket/*"]
    }
  ]
}
EOF

# Create policy and user
mc admin policy create minio-prod tenant-abc-policy tenant-abc-policy.json
mc admin user add minio-prod tenant-abc-access {secret}
mc admin policy attach minio-prod tenant-abc-policy --user=tenant-abc-access

# Verification: List buckets as tenant user
mc alias set tenant-abc-minio http://localhost:9000 tenant-abc-access {secret}
mc ls tenant-abc-minio
# Should only show tenant-abc-bucket
```

**Example (PostgreSQL):**

```sql
-- Source: PostgreSQL documentation + pg_hba.conf patterns
-- Create database and user
CREATE DATABASE tenant_abc;
CREATE USER tenant_abc_user WITH PASSWORD 'encrypted_password';
GRANT ALL PRIVILEGES ON DATABASE tenant_abc TO tenant_abc_user;

-- Revoke public access
REVOKE CONNECT ON DATABASE tenant_abc FROM PUBLIC;

-- Configure pg_hba.conf for network restriction
-- host  tenant_abc  tenant_abc_user  10.1.0.0/16  scram-sha-256
-- This restricts tenant_abc_user to only connect from tenant network

-- Verification queries
\l  -- List databases, verify tenant_abc exists
\du -- List users, verify tenant_abc_user has correct roles

-- Verify isolation: tenant_abc_user cannot access other databases
-- (Connect as tenant_abc_user)
\c tenant_xyz  -- Should fail with permission denied
```

**Example (Qdrant):**

```python
# Source: Qdrant multitenancy documentation
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

# Create per-tenant collection
client.create_collection(
    collection_name=f"tenant_abc",
    vectors_config={
        "size": 768,
        "distance": "Cosine"
    }
)

# Verification: List collections
collections = client.get_collections()
tenant_collections = [c.name for c in collections.collections
                      if c.name.startswith("tenant_abc")]
assert len(tenant_collections) == 1

# Verify tenant cannot access other collections (app-level enforcement)
# Qdrant API key scoping is limited; use application-level checks
```

### Pattern 4: Docker Internal Network Isolation (Offline Mode)

**What:** Use Docker Compose `internal: true` network parameter to block all outbound connectivity while allowing inter-container communication.

**When to use:** Offline mode deployments on air-gapped hosts.

**Example:**

```yaml
# Source: Docker Compose networks documentation
version: '3.8'

networks:
  etl-internal:
    driver: bridge
    internal: true  # KEY: No gateway, no outbound connectivity

services:
  intake-gateway:
    image: frostbyte/intake-gateway:latest
    networks:
      - etl-internal
    ports:
      - "127.0.0.1:8080:8080"  # Only localhost mapping

  parse-worker:
    image: frostbyte/parse-worker:latest
    networks:
      - etl-internal
    # No port mappings, internal-only

  postgres:
    image: postgres:16
    networks:
      - etl-internal
    environment:
      POSTGRES_DB: tenant_offline
      POSTGRES_USER: tenant_offline_user
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    volumes:
      - postgres-data:/var/lib/postgresql/data

  minio:
    image: minio/minio:latest
    networks:
      - etl-internal
    command: server /data
    volumes:
      - minio-data:/data

  qdrant:
    image: qdrant/qdrant:v1.13
    networks:
      - etl-internal
    volumes:
      - qdrant-data:/qdrant/storage

volumes:
  postgres-data:
  minio-data:
  qdrant-data:
```

**Behavior:**

- Containers can communicate with each other via service names (e.g., `postgres:5432`)
- Containers CANNOT reach the internet (no default gateway)
- Port mappings only work to localhost (`127.0.0.1:`), not `0.0.0.0:`
- Verification: `docker exec {container} ping 8.8.8.8` should fail

### Anti-Patterns to Avoid

**Anti-Pattern 1: Shared Database with Row-Level Security**

- **What:** Using PostgreSQL RLS instead of separate databases per tenant
- **Why bad:** One query without tenant filter leaks all data; compliance auditors flag as insufficient
- **Instead:** Separate database per tenant; blast radius limited by construction

**Anti-Pattern 2: Payload-Based Filtering Only (Qdrant)**

- **What:** Single Qdrant collection with `tenant_id` in payload, filtering via search parameters
- **Why bad:** Application bug forgetting tenant filter exposes all vectors; no structural isolation
- **Instead:** Collection-per-tenant; tenant filter is collection name, not search parameter

**Anti-Pattern 3: Trusting Host Firewall for Offline Isolation**

- **What:** Relying on iptables or host network rules to block outbound traffic
- **Why bad:** Customer may modify host rules; defense must be structural (Docker `internal: true`)
- **Instead:** Application-level guarantee via Docker network config

**Anti-Pattern 4: Reusing Age Keys Across Tenants**

- **What:** Single age key pair for all tenant secrets
- **Why bad:** Key compromise exposes all tenants; rotation requires re-encrypting all secrets
- **Instead:** Per-tenant age keys; rotation scoped to one tenant

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secrets encryption | Custom AES wrapper | SOPS + age | Envelope encryption, key rotation, audit trail, GitOps integration |
| API gateway / routing | Custom reverse proxy | Traefik v3 | Auto-discovery, TLS management, middleware (rate limiting, auth) |
| Per-tenant credential management | Manual key generation scripts | MinIO mc admin, PostgreSQL roles | Atomic operations, built-in verification, consistent format |
| Firewall rule validation | Custom parser | Hetzner Cloud API response validation | API validates rule syntax, CIDR format, port ranges before applying |
| Network isolation testing | Manual ping/curl tests | Docker network inspection tools | `docker network inspect`, `docker exec {container} ip route` shows gateway absence |

**Key insight:** Infrastructure orchestration has sharp edges (partial failures, state inconsistency, credential leakage). Use battle-tested tools that handle retries, idempotency, and error cases.

## Common Pitfalls

### Pitfall 1: Hetzner Cloud CIDR Host Bits

**What goes wrong:** Creating firewall rules with CIDR blocks that have host bits set (e.g., `10.1.1.5/24`) fails silently or is rejected by API.

**Why it happens:** As of December 2025, Hetzner Cloud API enforces that CIDR blocks must have host bits zeroed (e.g., `10.1.1.0/24`, not `10.1.1.5/24`).

**How to avoid:** Always normalize CIDRs before API calls:

```python
import ipaddress

def normalize_cidr(cidr_str):
    network = ipaddress.ip_network(cidr_str, strict=False)
    return str(network)

# Example
normalize_cidr("10.1.1.5/24")  # Returns "10.1.1.0/24"
```

**Warning signs:** API returns 400 Bad Request with "invalid CIDR" error.

### Pitfall 2: Hetzner Private Network 100-Server Limit

**What goes wrong:** Creating more than 100 servers in a single Hetzner private network fails.

**Why it happens:** Hetzner Cloud private networks have a hard limit of 100 nodes per network.

**How to avoid:** Plan network topology early:

- For <100 servers per tenant: Single private network per tenant
- For >100 servers per tenant: Multiple private networks with routing, or use public network with firewall rules

**Warning signs:** API error "network full" when attaching server to network.

### Pitfall 3: SOPS Key Rotation Without Backup

**What goes wrong:** Rotating age keys with `sops --rotate` but losing access to old private key makes old backups undecryptable.

**Why it happens:** SOPS rotation re-encrypts the data key but doesn't decrypt with the old key afterward.

**How to avoid:**

1. Test decryption before deleting old key
2. Keep old keys in secure offline storage for backup recovery period (e.g., 90 days)
3. Document key-to-backup-date mapping in control plane registry

**Warning signs:** `sops --decrypt` fails with "no keys available" on old backups.

### Pitfall 4: Implicit Outbound Allow in Hetzner Firewalls

**What goes wrong:** Creating only inbound firewall rules, expecting outbound to be blocked, but outbound is implicitly allowed.

**Why it happens:** Hetzner Cloud Firewalls default to "outbound ACCEPT" if no outbound rules exist. Defining even one outbound rule changes to "implicit deny" for unmatched traffic.

**How to avoid:** Explicitly define outbound rules for all allowed traffic:

```python
rules = [
    # Inbound rules...

    # Outbound: Explicitly allow only internal traffic
    {
        "direction": "out",
        "protocol": "tcp",
        "port": "any",
        "destination_ips": ["10.1.0.0/16"]
    }
    # Implicit deny: All other outbound traffic blocked
]
```

**Warning signs:** Tenant servers can reach internet unexpectedly; no audit events for outbound blocks.

### Pitfall 5: MinIO Bucket Policy vs IAM Policy Confusion

**What goes wrong:** Trying to use MinIO bucket policies to restrict user access, but bucket policies only control anonymous access.

**Why it happens:** MinIO bucket policies follow S3 semantics but only apply to anonymous (no credentials) access. User access is controlled by IAM policies attached to the user.

**How to avoid:** Use IAM policies for per-tenant user isolation:

```bash
# WRONG: Bucket policy for user access
mc admin policy create minio-prod tenant-policy bucket-policy.json

# CORRECT: IAM policy attached to user
mc admin policy create minio-prod tenant-policy iam-policy.json
mc admin policy attach minio-prod tenant-policy --user=tenant-user
```

**Warning signs:** User can access buckets despite bucket policy restrictions.

## Code Examples

Verified patterns from official sources:

### Hetzner Cloud Firewall Creation (Complete Example)

```python
# Source: Hetzner Cloud API reference
from hcloud import Client
from hcloud.firewalls.domain import FirewallRule

client = Client(token="{api_token}")

# Define firewall rules
inbound_rules = [
    FirewallRule(
        direction="in",
        protocol="tcp",
        port="443",
        source_ips=["203.0.113.5/32"]  # API gateway IP
    ),
    FirewallRule(
        direction="in",
        protocol="tcp",
        port="any",
        source_ips=["10.1.0.0/16"]  # Tenant private network
    )
]

outbound_rules = [
    FirewallRule(
        direction="out",
        protocol="tcp",
        port="443",
        destination_ips=["198.51.100.0/24"]  # OpenRouter API range
    ),
    FirewallRule(
        direction="out",
        protocol="tcp",
        port="any",
        destination_ips=["10.1.0.0/16"]  # Tenant private network
    )
]

# Create firewall
firewall = client.firewalls.create(
    name=f"tenant-{tenant_id}-fw",
    labels={"tenant_id": tenant_id},
    rules=inbound_rules + outbound_rules
)

# Apply to servers with matching label
client.firewalls.apply_to_resources(
    firewall=firewall,
    resources=[{"type": "label_selector", "label_selector": f"tenant_id={tenant_id}"}]
)
```

### SOPS Envelope Encryption Workflow

```bash
# Source: SOPS documentation + age specification
# 1. Setup: Generate age key for tenant
mkdir -p .secrets/tenants
age-keygen -o .secrets/tenants/tenant-abc.age
# Output:
# Public key: age1hl5v2xfx8lc8n3z9x4q7r5t6y8u9o0p2a4s6d8f
# (Store public key in control plane registry)

# 2. Create secrets file
cat > tenant-abc-secrets.yaml <<EOF
db_password: super_secret_123
minio_access_key: AKIAIOSFODNN7EXAMPLE
minio_secret_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
qdrant_api_key: qdr_abc_xyz_789
EOF

# 3. Encrypt with SOPS using tenant's age key
sops --age age1hl5v2xfx8lc8n3z9x4q7r5t6y8u9o0p2a4s6d8f \
     --encrypt tenant-abc-secrets.yaml > tenant-abc-secrets.enc.yaml

# Encrypted file structure:
# db_password: ENC[AES256_GCM,data:...,iv:...,tag:...,type:str]
# minio_access_key: ENC[AES256_GCM,data:...,iv:...,tag:...,type:str]
# sops:
#   age:
#     - recipient: age1hl5v2xfx8lc8n3z9x4q7r5t6y8u9o0p2a4s6d8f
#       enc: |
#         -----BEGIN AGE ENCRYPTED FILE-----
#         [encrypted data key]
#         -----END AGE ENCRYPTED FILE-----

# 4. Decrypt (in application)
export SOPS_AGE_KEY_FILE=.secrets/tenants/tenant-abc.age
sops --decrypt tenant-abc-secrets.enc.yaml | yq '.db_password'
# Output: super_secret_123

# 5. Key rotation
age-keygen -o .secrets/tenants/tenant-abc-new.age
sops --rotate \
     --add-age $(cat .secrets/tenants/tenant-abc-new.age.pub) \
     --rm-age age1hl5v2xfx8lc8n3z9x4q7r5t6y8u9o0p2a4s6d8f \
     --in-place tenant-abc-secrets.enc.yaml
```

### MinIO Per-Tenant Isolation Setup

```bash
# Source: MinIO IAM documentation
# Assume MinIO server running at localhost:9000, admin credentials set

# 1. Create tenant bucket
mc mb local-minio/tenant-abc-bucket

# 2. Create IAM policy scoped to tenant bucket
cat > tenant-abc-iam-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::tenant-abc-bucket"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::tenant-abc-bucket/*"
      ]
    },
    {
      "Effect": "Deny",
      "Action": ["s3:*"],
      "Resource": [
        "arn:aws:s3:::tenant-xyz-bucket",
        "arn:aws:s3:::tenant-xyz-bucket/*"
      ]
    }
  ]
}
EOF

# 3. Create policy in MinIO
mc admin policy create local-minio tenant-abc-policy tenant-abc-iam-policy.json

# 4. Create user and attach policy
mc admin user add local-minio tenant-abc-user $(sops -d tenant-abc-secrets.enc.yaml | yq '.minio_secret_key')
mc admin policy attach local-minio tenant-abc-policy --user=tenant-abc-user

# 5. Verification
# Set alias for tenant user
mc alias set tenant-abc-minio http://localhost:9000 \
   tenant-abc-user $(sops -d tenant-abc-secrets.enc.yaml | yq '.minio_secret_key')

# List buckets (should only show tenant-abc-bucket)
mc ls tenant-abc-minio

# Try to access other tenant bucket (should fail)
mc ls tenant-abc-minio/tenant-xyz-bucket
# Error: Access Denied

# Verify policy attachment
mc admin user info local-minio tenant-abc-user
# Output should include PolicyName: tenant-abc-policy
```

### PostgreSQL Database-Per-Tenant Setup

```sql
-- Source: PostgreSQL documentation + multi-tenancy patterns
-- 1. Create database and user
CREATE DATABASE tenant_abc;
CREATE USER tenant_abc_user WITH ENCRYPTED PASSWORD 'password_from_sops';

-- 2. Grant privileges
GRANT ALL PRIVILEGES ON DATABASE tenant_abc TO tenant_abc_user;
GRANT ALL ON SCHEMA public TO tenant_abc_user;

-- 3. Revoke public access
REVOKE CONNECT ON DATABASE tenant_abc FROM PUBLIC;

-- 4. Configure pg_hba.conf for network restriction
-- Add line (requires PostgreSQL restart):
-- host  tenant_abc  tenant_abc_user  10.1.0.0/16  scram-sha-256
-- This restricts tenant_abc_user to connect only from tenant's private network

-- 5. Verification queries
-- List databases
\l
-- Output should include tenant_abc owned by tenant_abc_user

-- List users and roles
\du
-- Output should show tenant_abc_user with privileges

-- Connect as tenant user (from allowed network)
\c tenant_abc tenant_abc_user

-- Verify isolation: try to connect to other database
\c tenant_xyz
-- Error: FATAL:  database "tenant_xyz" does not exist or no privilege

-- Verify table creation
CREATE TABLE test (id SERIAL PRIMARY KEY, data TEXT);
INSERT INTO test (data) VALUES ('tenant abc data');
SELECT * FROM test;

-- Verify pg_hba.conf enforcement (from disallowed network)
-- psql -h {postgres_host} -U tenant_abc_user -d tenant_abc
-- Error: no pg_hba.conf entry for host
```

### Qdrant Collection-Per-Tenant Setup

```python
# Source: Qdrant multitenancy documentation
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")

# 1. Create collection for tenant
collection_name = f"tenant_abc"

client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(
        size=768,  # Locked dimension from Phase 1
        distance=Distance.COSINE
    )
)

# 2. Verify collection creation
collections = client.get_collections()
tenant_collections = [c.name for c in collections.collections
                      if c.name == collection_name]
assert len(tenant_collections) == 1, f"Collection {collection_name} not found"

# 3. Insert test vector
from qdrant_client.models import PointStruct

client.upsert(
    collection_name=collection_name,
    points=[
        PointStruct(
            id=1,
            vector=[0.1] * 768,
            payload={"doc_id": "abc-001", "chunk_id": "chunk-001"}
        )
    ]
)

# 4. Verify isolation: search only returns tenant data
results = client.search(
    collection_name=collection_name,
    query_vector=[0.1] * 768,
    limit=10
)
assert all(r.payload.get("doc_id", "").startswith("abc-") for r in results)

# 5. Application-level access control (Qdrant has limited API key scoping)
def get_collection_name(tenant_id: str) -> str:
    """Enforce collection-per-tenant naming"""
    return f"tenant_{tenant_id}"

def verify_tenant_access(tenant_id: str, collection_name: str):
    """Verify tenant can only access their collection"""
    expected_collection = get_collection_name(tenant_id)
    if collection_name != expected_collection:
        raise PermissionError(f"Tenant {tenant_id} cannot access {collection_name}")

# Usage in API
tenant_id = "abc"
requested_collection = request.args.get("collection")
verify_tenant_access(tenant_id, requested_collection)
# Proceeds only if requested_collection == "tenant_abc"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PGP for SOPS | age for SOPS | ~2020 | Simpler key format, no keyring management, better CLI UX |
| Qdrant payload filtering | Qdrant tiered multitenancy (v1.16) | Dec 2024 | Automatic tenant promotion from shared to dedicated shards |
| Manual Hetzner firewall rules | Label selectors for automatic application | 2022 | Dynamic firewall application, no need to update rules when servers added |
| PostgreSQL shared DB + RLS | Database-per-tenant | Ongoing (industry shift) | Stronger isolation for regulated industries, simpler compliance audits |
| Docker `--link` for networking | Docker Compose networks with `internal: true` | 2016 | Explicit network isolation control, no deprecated flags |

**Deprecated/outdated:**

- **Hetzner Cloud API v1.0**: Replaced by current REST API with OpenAPI spec
- **SOPS with PGP**: Still supported but age is recommended for new deployments
- **Qdrant single collection + payload filtering**: Still works but v1.16 tiered multitenancy is recommended for scale
- **Docker `--net=none` pattern**: Replaced by `internal: true` networks for cleaner compose syntax

## Open Questions

Things that couldn't be fully resolved:

1. **Hetzner Cloud Projects API**
   - What we know: Projects exist in Hetzner Cloud Console for billing/organizational separation
   - What's unclear: No direct API for creating/managing Projects programmatically; must use Console
   - Recommendation: Use label-based isolation within a single Project, or manually create Projects via Console and use per-Project API tokens

2. **Qdrant API Key Collection Scoping**
   - What we know: Qdrant v1.16 supports tiered multitenancy with sharding
   - What's unclear: API key scoping to specific collections is not documented; may require application-level enforcement
   - Recommendation: Implement tenant-to-collection mapping in application layer; verify with Qdrant team if native API key scoping exists

3. **MinIO Bucket Policy for Authenticated Users**
   - What we know: MinIO bucket policies control anonymous access only; IAM policies control user access
   - What's unclear: Some documentation conflates the two; bucket policies don't directly restrict authenticated users
   - Recommendation: Always use IAM policies for per-tenant user isolation; verify with `mc admin user info`

4. **SOPS Key Group Shamir Secret Sharing for Multi-Tenant**
   - What we know: SOPS supports key groups requiring multiple keys to decrypt (Shamir's Secret Sharing)
   - What's unclear: Whether this adds value for per-tenant keys (vs. single age key per tenant)
   - Recommendation: Start with single age key per tenant for simplicity; evaluate key groups if compliance requires multi-party control

5. **Hetzner Cloud Network Zone Restrictions**
   - What we know: Networks must specify a network zone (eu-central, us-east, us-west, ap-southeast)
   - What's unclear: Cross-zone routing capabilities and latency implications
   - Recommendation: Provision all tenant resources in a single zone for Phase 2; defer multi-zone to Phase 7 (deployment architecture)

## Sources

### Primary (HIGH confidence)

- [Hetzner Cloud API Overview](https://docs.hetzner.cloud/) - API structure, service coverage
- [Hetzner Cloud API Reference](https://docs.hetzner.cloud/reference/cloud) - Server, network, firewall, volume endpoints
- [Hetzner Cloud Firewalls FAQ](https://docs.hetzner.com/cloud/firewalls/faq/) - CIDR limits (100 max), firewall rule behavior
- [Hetzner Cloud Firewalls Overview](https://docs.hetzner.com/cloud/firewalls/overview/) - Inbound/outbound rules, implicit deny/allow
- [SOPS Documentation](https://getsops.io/docs/) - Envelope encryption, age integration, key rotation
- [age Specification](https://github.com/C2SP/C2SP/blob/main/age.md) - File format, symmetric encryption, recipient types
- [Docker Compose Networks Reference](https://docs.docker.com/reference/compose-file/networks/) - `internal` parameter behavior
- [MinIO IAM Documentation](https://min.io/docs/minio/linux/administration/identity-access-management/policy-based-access-control.html) - Bucket policy vs IAM policy
- [PostgreSQL Documentation](https://www.postgresql.org/docs/current/) - Database creation, user roles, pg_hba.conf
- [Qdrant Multitenancy Guide](https://qdrant.tech/documentation/guides/multitenancy/) - Collection-per-tenant, payload-based partitioning
- [Qdrant 1.16 Tiered Multitenancy](https://qdrant.tech/blog/qdrant-1.16.x/) - Shard promotion, fallback shards

### Secondary (MEDIUM confidence)

- [Rotating SOPS Encryption Keys (Techno Tim)](https://technotim.com/posts/rotate-sops-encryption-keys/) - Practical key rotation workflow
- [MinIO Multi-Tenancy Configuration (OneUpTime)](https://oneuptime.com/blog/post/2026-01-28-minio-multi-tenancy/view) - Shared cluster with IAM policies
- [MinIO Bucket Policies (OneUpTime)](https://oneuptime.com/blog/post/2026-01-27-minio-bucket-policies/view) - Bucket policy vs IAM policy clarification
- [Docker Internal Networks (SequentialRead)](https://sequentialread.com/creating-a-simple-but-effective-firewall-using-vanilla-docker-compose/) - Gateway container pattern for outbound control
- [AWS KMS Multi-Tenant Strategy (AWS Architecture Blog)](https://aws.amazon.com/blogs/architecture/simplify-multi-tenant-encryption-with-a-cost-conscious-aws-kms-key-strategy/) - Envelope encryption patterns, key rotation
- [Envelope Encryption Guide (Google Cloud KMS)](https://cloud.google.com/kms/docs/envelope-encryption) - KEK/DEK hierarchy, rotation transparency
- [PostgreSQL Row-Level Security (AWS Database Blog)](https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/) - Alternative to database-per-tenant

### Tertiary (LOW confidence)

- Hetzner Cloud 100-server private network limit - sourced from community forums (LowEndTalk), needs official verification
- Qdrant API key collection scoping - not found in official docs, may not exist or be undocumented
- MinIO bucket policy behavior with authenticated users - conflicting information in community sources vs official docs

## Metadata

**Confidence breakdown:**

- Hetzner Cloud API: MEDIUM - Official API reference consulted but some constraints (Projects, CIDR normalization) from secondary sources
- SOPS + age envelope encryption: HIGH - Official documentation for both tools, clear key hierarchy and rotation procedures
- Storage isolation (MinIO, PostgreSQL, Qdrant): MEDIUM - Official docs consulted but verification commands not tested hands-on
- Docker network isolation: MEDIUM - Official Docker Compose docs confirm `internal: true` behavior but gateway specifics need validation
- Network boundaries (firewall rules): MEDIUM - Hetzner firewall docs clear on inbound/outbound semantics but edge cases (stateful tracking) need testing

**Research date:** 2026-02-09
**Valid until:** 2026-04-09 (60 days - infrastructure APIs are relatively stable but Qdrant/SOPS release frequently)
