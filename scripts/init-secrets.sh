#!/bin/bash
#
# Frostbyte Secrets Management Initialization Script
# ===================================================
# Simple SOPS + age setup for per-tenant secrets encryption
#
# USAGE:
#   ./scripts/init-secrets.sh --init-master     # Initialize master encryption key
#   ./scripts/init-secrets.sh --create-tenant <tenant_id>  # Create tenant-specific secrets
#   ./scripts/init-secrets.sh --encrypt <tenant_id>        # Encrypt tenant secrets
#   ./scripts/init-secrets.sh --decrypt <tenant_id>        # Decrypt tenant secrets
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SECRETS_DIR="${PROJECT_ROOT}/.secrets"
TENANTS_DIR="${SECRETS_DIR}/tenants"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# =============================================================================
# MASTER KEY INITIALIZATION
# =============================================================================

init_master_key() {
    log_info "Initializing master encryption key..."
    
    if [[ -f "${SECRETS_DIR}/age.key" ]]; then
        log_warn "Master key already exists at ${SECRETS_DIR}/age.key"
        log_warn "To regenerate, move or delete the existing key first"
        return 1
    fi
    
    # Generate age key pair
    if ! command -v age-keygen &> /dev/null; then
        log_error "age-keygen not found. Install age: https://github.com/FiloSottile/age"
        log_error "macOS: brew install age"
        log_error "Linux: sudo apt-get install age  or download from GitHub"
        return 1
    fi
    
    age-keygen -o "${SECRETS_DIR}/age.key"
    
    # Extract public key
    PUBLIC_KEY=$(grep "public key:" "${SECRETS_DIR}/age.key" | awk '{print $NF}')
    echo "${PUBLIC_KEY}" > "${SECRETS_DIR}/age.pub"
    
    # Set secure permissions
    chmod 600 "${SECRETS_DIR}/age.key"
    chmod 644 "${SECRETS_DIR}/age.pub"
    
    log_info "Master key created successfully!"
    log_info "Public key: ${PUBLIC_KEY}"
    log_info ""
    log_info "IMPORTANT: Backup ${SECRETS_DIR}/age.key to a secure location"
    log_info "Loss of this key means loss of all encrypted secrets"
    
    # Update .env with the key path
    if [[ -f "${PROJECT_ROOT}/.env" ]]; then
        sed -i '' "s|^SOPS_AGE_KEY_FILE=.*|SOPS_AGE_KEY_FILE=${SECRETS_DIR}/age.key|" "${PROJECT_ROOT}/.env" 2>/dev/null || true
    fi
    
    return 0
}

# =============================================================================
# TENANT SECRETS CREATION
# =============================================================================

create_tenant_secrets() {
    local tenant_id=$1
    
    log_info "Creating secrets structure for tenant: ${tenant_id}"
    
    # Create tenant directory
    mkdir -p "${TENANTS_DIR}/${tenant_id}"
    
    # Generate tenant-specific age key
    if [[ ! -f "${TENANTS_DIR}/${tenant_id}/key.age" ]]; then
        age-keygen -o "${TENANTS_DIR}/${tenant_id}/key.age"
        PUBLIC_KEY=$(grep "public key:" "${TENANTS_DIR}/${tenant_id}/key.age" | awk '{print $NF}')
        echo "${PUBLIC_KEY}" > "${TENANTS_DIR}/${tenant_id}/key.pub"
        chmod 600 "${TENANTS_DIR}/${tenant_id}/key.age"
        chmod 644 "${TENANTS_DIR}/${tenant_id}/key.pub"
        log_info "Tenant encryption key created: ${PUBLIC_KEY}"
    fi
    
    # Create template secrets file
    local secrets_file="${TENANTS_DIR}/${tenant_id}/secrets.yaml"
    if [[ ! -f "${secrets_file}" ]]; then
        cat > "${secrets_file}" << EOF
# Tenant ${tenant_id} Secrets
# WARNING: This file contains sensitive credentials. Encrypt with SOPS!

# Database credentials
postgres_password: $(openssl rand -base64 32 | tr -d '=+/')

# MinIO/S3 credentials
minio_access_key: tenant-${tenant_id}-$(openssl rand -hex 8)
minio_secret_key: $(openssl rand -base64 32 | tr -d '=+/')

# Qdrant API key
qdrant_api_key: $(openssl rand -hex 32)

# Redis password
redis_password: $(openssl rand -base64 32 | tr -d '=+/')

# Tenant API key
tenant_api_key: $(openssl rand -hex 32)

# Additional custom secrets (add as needed)
# custom_secret_name: value
EOF
        log_info "Created secrets template: ${secrets_file}"
        log_warn "Remember to encrypt this file with: $0 --encrypt ${tenant_id}"
    fi
    
    return 0
}

# =============================================================================
# ENCRYPTION / DECRYPTION
# =============================================================================

encrypt_tenant_secrets() {
    local tenant_id=$1
    
    local plaintext_file="${TENANTS_DIR}/${tenant_id}/secrets.yaml"
    local encrypted_file="${TENANTS_DIR}/${tenant_id}/secrets.enc.yaml"
    local pub_key_file="${TENANTS_DIR}/${tenant_id}/key.pub"
    
    if [[ ! -f "${plaintext_file}" ]]; then
        log_error "Plaintext secrets not found: ${plaintext_file}"
        log_error "Create with: $0 --create-tenant ${tenant_id}"
        return 1
    fi
    
    if [[ ! -f "${pub_key_file}" ]]; then
        log_error "Tenant public key not found: ${pub_key_file}"
        return 1
    fi
    
    if ! command -v sops &> /dev/null; then
        log_error "sops not found. Install: https://github.com/getsops/sops"
        log_error "macOS: brew install sops"
        log_error "Linux: Download from https://github.com/getsops/sops/releases"
        return 1
    fi
    
    local recipient=$(cat "${pub_key_file}")
    
    log_info "Encrypting secrets for tenant ${tenant_id}..."
    sops --age "${recipient}" --encrypt "${plaintext_file}" > "${encrypted_file}"
    
    # Securely delete plaintext
    if command -v shred &> /dev/null; then
        shred -u "${plaintext_file}"
    else
        rm -f "${plaintext_file}"
    fi
    
    log_info "Secrets encrypted: ${encrypted_file}"
    log_info "Plaintext securely deleted"
    
    return 0
}

decrypt_tenant_secrets() {
    local tenant_id=$1
    
    local encrypted_file="${TENANTS_DIR}/${tenant_id}/secrets.enc.yaml"
    local key_file="${TENANTS_DIR}/${tenant_id}/key.age"
    
    if [[ ! -f "${encrypted_file}" ]]; then
        log_error "Encrypted secrets not found: ${encrypted_file}"
        return 1
    fi
    
    if [[ ! -f "${key_file}" ]]; then
        log_error "Tenant private key not found: ${key_file}"
        return 1
    fi
    
    log_info "Decrypting secrets for tenant ${tenant_id}..."
    SOPS_AGE_KEY_FILE="${key_file}" sops --decrypt "${encrypted_file}"
    
    return 0
}

# =============================================================================
# ENVIRONMENT EXPORT
# =============================================================================

export_tenant_env() {
    local tenant_id=$1
    local output_file="${TENANTS_DIR}/${tenant_id}/.env"
    
    log_info "Exporting secrets as environment variables for tenant ${tenant_id}..."
    
    # Decrypt and convert to .env format
    decrypt_tenant_secrets "${tenant_id}" | grep -E '^[a-z_]+:' | sed 's/: /=/' > "${output_file}"
    
    log_info "Exported to: ${output_file}"
    log_warn "WARNING: This file contains plaintext secrets. Delete after use!"
    
    return 0
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    case "${1:-}" in
        --init-master|-i)
            init_master_key
            ;;
        --create-tenant|-c)
            if [[ -z "${2:-}" ]]; then
                log_error "Usage: $0 --create-tenant <tenant_id>"
                exit 1
            fi
            create_tenant_secrets "$2"
            ;;
        --encrypt|-e)
            if [[ -z "${2:-}" ]]; then
                log_error "Usage: $0 --encrypt <tenant_id>"
                exit 1
            fi
            encrypt_tenant_secrets "$2"
            ;;
        --decrypt|-d)
            if [[ -z "${2:-}" ]]; then
                log_error "Usage: $0 --decrypt <tenant_id>"
                exit 1
            fi
            decrypt_tenant_secrets "$2"
            ;;
        --export-env)
            if [[ -z "${2:-}" ]]; then
                log_error "Usage: $0 --export-env <tenant_id>"
                exit 1
            fi
            export_tenant_env "$2"
            ;;
        --help|-h|*)
            cat << EOF
Frostbyte Secrets Management Script

USAGE:
  $0 --init-master                 Initialize master encryption key
  $0 --create-tenant <id>          Create new tenant with secrets template
  $0 --encrypt <id>                Encrypt tenant secrets with SOPS
  $0 --decrypt <id>                Decrypt and display tenant secrets
  $0 --export-env <id>             Export secrets as .env file

PREREQUISITES:
  - age (encryption tool): https://github.com/FiloSottile/age
  - sops (secrets manager): https://github.com/getsops/sops

EXAMPLES:
  # First time setup
  $0 --init-master

  # Create and encrypt secrets for tenant "acme-corp"
  $0 --create-tenant acme-corp
  $0 --encrypt acme-corp

  # View decrypted secrets
  $0 --decrypt acme-corp

  # Export for runtime use
  $0 --export-env acme-corp
  source .secrets/tenants/acme-corp/.env

SECURITY NOTES:
  - Master key (.secrets/age.key) must be backed up securely
  - Plaintext secrets.yaml files are shredded after encryption
  - Exported .env files should be deleted immediately after use
  - Private keys have 600 permissions; public keys have 644

EOF
            ;;
    esac
}

main "$@"
