# Frostbyte Secrets Management

This directory contains encrypted secrets managed by [SOPS](https://github.com/getsops/sops) and [age](https://github.com/FiloSottile/age).

## Structure

```
.secrets/
├── age.key              # Master encryption key (NEVER commit)
├── age.pub              # Master public key (can commit)
├── .gitkeep             # Keeps directory in git
└── tenants/
    └── {tenant_id}/
        ├── key.age      # Tenant private key
        ├── key.pub      # Tenant public key
        ├── secrets.enc.yaml   # Encrypted secrets (committed)
        └── .env         # Exported plaintext (DELETE after use)
```

## Quick Start

```bash
# 1. Install prerequisites
brew install age sops

# 2. Initialize master key (one-time)
./scripts/init-secrets.sh --init-master

# 3. Create tenant secrets
./scripts/init-secrets.sh --create-tenant acme-corp
./scripts/init-secrets.sh --encrypt acme-corp

# 4. Decrypt for runtime use
./scripts/init-secrets.sh --export-env acme-corp
source .secrets/tenants/acme-corp/.env
```

## Security Rules

- **Never commit** `.secrets/age.key` or any `*.age` private keys
- **Always encrypt** secrets before committing
- **Securely delete** exported `.env` files after use
- **Backup** the master `age.key` to a secure location

## Integration with Docker Compose

```yaml
services:
  api:
    env_file:
      - .secrets/tenants/${TENANT_ID}/.env
```
