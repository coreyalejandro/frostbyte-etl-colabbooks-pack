#!/bin/bash
#
# Frostbyte Enhancements Verification Script
# ===========================================
#
# This script verifies that enhancements have been correctly implemented.
#
# USAGE:
#   ./verify-implementations.sh                    # Verify all
#   ./verify-implementations.sh --check 1          # Verify enhancement 1
#   ./verify-implementations.sh --check 1.2        # Verify enhancement 1, criterion 2
#
# EXIT CODES:
#   0 - All verifications passed
#   1 - Verification failed
#   2 - Invalid arguments
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${FROSTBYTE_REPO_ROOT:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# =============================================================================
# VERIFICATION FUNCTIONS
# =============================================================================

verify_e01() {
    local criterion=${1:-}
    
    if [[ -z "$criterion" ]] || [[ "$criterion" == "1" ]]; then
        # Check OpenAPI spec exists
        if [[ -f "$REPO_ROOT/docs/api/openapi.yaml" ]]; then
            pass "E01.1: OpenAPI spec file exists"
        else
            fail "E01.1: OpenAPI spec file missing at docs/api/openapi.yaml"
            return 1
        fi
    fi
    
    if [[ -z "$criterion" ]] || [[ "$criterion" == "4" ]]; then
        # Validate spec
        if command -v openapi-validator &> /dev/null; then
            if openapi-validator "$REPO_ROOT/docs/api/openapi.yaml"; then
                pass "E01.4: OpenAPI spec validates"
            else
                fail "E01.4: OpenAPI spec validation failed"
                return 1
            fi
        else
            warn "E01.4: openapi-validator not installed, skipping validation"
        fi
    fi
    
    return 0
}

verify_e04() {
    local criterion=${1:-}
    
    if [[ -z "$criterion" ]] || [[ "$criterion" == "1" ]]; then
        # Check service exists
        if [[ -f "$REPO_ROOT/packages/core/src/services/schema-extension.service.ts" ]]; then
            pass "E04.1: Schema extension service exists"
        else
            fail "E04.1: Schema extension service missing"
            return 1
        fi
    fi
    
    return 0
}

verify_e10() {
    local criterion=${1:-}
    
    if [[ -z "$criterion" ]] || [[ "$criterion" == "1" ]]; then
        # Check test command works
        if npm run test:compliance --silent 2>/dev/null; then
            pass "E10.1: Compliance test suite runs"
        else
            fail "E10.1: Compliance test suite failed or not configured"
            return 1
        fi
    fi
    
    return 0
}

verify_e07() {
    local criterion=${1:-}
    
    if [[ -z "$criterion" ]] || [[ "$criterion" == "1" ]]; then
        # Check SAML strategy exists
        if [[ -f "$REPO_ROOT/packages/auth/src/sso/saml.strategy.ts" ]]; then
            pass "E07.1: SAML strategy exists"
        else
            fail "E07.1: SAML strategy missing"
            return 1
        fi
    fi
    
    return 0
}

verify_e03() {
    local criterion=${1:-}
    
    if [[ -z "$criterion" ]] || [[ "$criterion" == "1" ]]; then
        # Check batch routes exist
        if [[ -f "$REPO_ROOT/packages/api/src/routes/batch.routes.ts" ]]; then
            pass "E03.1: Batch routes exist"
        else
            fail "E03.1: Batch routes missing"
            return 1
        fi
    fi
    
    return 0
}

verify_e06() {
    local criterion=${1:-}
    
    if [[ -z "$criterion" ]] || [[ "$criterion" == "1" ]]; then
        # Check dashboard exists
        if [[ -d "$REPO_ROOT/packages/dashboard" ]]; then
            pass "E06.1: Dashboard package exists"
        else
            fail "E06.1: Dashboard package missing"
            return 1
        fi
    fi
    
    return 0
}

verify_e02() {
    local criterion=${1:-}
    
    if [[ -z "$criterion" ]] || [[ "$criterion" == "1" ]]; then
        # Check Terraform provider exists
        if [[ -d "$REPO_ROOT/terraform-provider-frostbyte" ]]; then
            pass "E02.1: Terraform provider directory exists"
        else
            fail "E02.1: Terraform provider directory missing"
            return 1
        fi
    fi
    
    return 0
}

verify_e08() {
    local criterion=${1:-}
    
    if [[ -z "$criterion" ]] || [[ "$criterion" == "1" ]]; then
        # Check export signer exists
        if [[ -f "$REPO_ROOT/packages/core/src/services/export-signer.service.ts" ]]; then
            pass "E08.1: Export signer service exists"
        else
            fail "E08.1: Export signer service missing"
            return 1
        fi
    fi
    
    return 0
}

verify_e05() {
    local criterion=${1:-}
    
    if [[ -z "$criterion" ]] || [[ "$criterion" == "1" ]]; then
        # Check entity extraction exists
        if [[ -f "$REPO_ROOT/packages/core/src/services/entity-extraction.service.ts" ]]; then
            pass "E05.1: Entity extraction service exists"
        else
            fail "E05.1: Entity extraction service missing"
            return 1
        fi
    fi
    
    return 0
}

verify_e09() {
    local criterion=${1:-}
    
    if [[ -z "$criterion" ]] || [[ "$criterion" == "1" ]]; then
        # Check image processor exists
        if [[ -f "$REPO_ROOT/packages/pipeline/src/processors/image-processor.ts" ]]; then
            pass "E09.1: Image processor exists"
        else
            fail "E09.1: Image processor missing"
            return 1
        fi
    fi
    
    return 0
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    if [[ $# -eq 0 ]]; then
        # Verify all
        echo "Verifying all enhancements..."
        for i in 1 4 10 7 3 6 2 8 5 9; do
            "verify_e$(printf '%02d' $i)" || exit 1
        done
        echo ""
        echo "All verifications passed!"
        exit 0
    fi
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --check)
                check="$2"
                shift 2
                
                # Parse enhancement.criterion format
                if [[ "$check" =~ ^([0-9]+)\.([0-9]+)$ ]]; then
                    enh="${BASH_REMATCH[1]}"
                    criterion="${BASH_REMATCH[2]}"
                    "verify_e$(printf '%02d' $enh)" "$criterion"
                    exit $?
                elif [[ "$check" =~ ^[0-9]+$ ]]; then
                    "verify_e$(printf '%02d' $check)"
                    exit $?
                else
                    echo "Invalid check format: $check"
                    exit 2
                fi
                ;;
            *)
                echo "Unknown option: $1"
                exit 2
                ;;
        esac
    done
}

main "$@"
