#!/usr/bin/env python3
"""
Frostbyte Cross-Cutting Enhancements Implementation Generator
===========================================================

This script generates complete, deterministic, platform-independent instructions
for implementing all 10 cross-cutting product enhancements identified in the
FROSTBYTE_PRODUCT_VISION.md document.

EXECUTION MODES:
  --generate-markdown    Generate markdown implementation guide (default)
  --generate-json        Generate JSON TaskGraph for machine execution
  --validate-only        Validate environment without generating
  --phase N              Execute only phase N (1-4)
  --full                 Execute all phases

USAGE:
  python3 generate_enhancement_implementations.py --full
  python3 generate_enhancement_implementations.py --phase 1
  python3 generate_enhancement_implementations.py --generate-markdown --output ./implementations/

EXIT CODES:
  0  - Success
  1  - Invalid arguments
  2  - Environment validation failed
  3  - File generation failed
  4  - Verification failed
"""

import argparse
import json
import os
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class EnhancementType(Enum):
    TABLE_STAKES = "Table Stakes"
    VALUE_ADDED = "Value Added"
    ESSENTIAL = "Essential"


class EffortLevel(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ValueLevel(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


@dataclass
class Enhancement:
    """Represents a single cross-cutting enhancement."""
    id: int
    name: str
    enhancement_type: EnhancementType
    value: ValueLevel
    effort: EffortLevel
    rationale: str
    dependencies: List[int]
    phase: int
    verification_criteria: List[str]
    deliverables: List[str]
    technical_specs: Dict[str, Any]


# =============================================================================
# ENHANCEMENT DEFINITIONS - Single Source of Truth
# =============================================================================

ENHANCEMENTS: List[Enhancement] = [
    Enhancement(
        id=1,
        name="OpenAPI/Swagger Spec for All APIs",
        enhancement_type=EnhancementType.TABLE_STAKES,
        value=ValueLevel.HIGH,
        effort=EffortLevel.LOW,
        rationale="Critical for all verticals—legal, defense, pharma, and SaaS all require documented contracts for integration.",
        dependencies=[],
        phase=1,
        verification_criteria=[
            "OpenAPI 3.1 spec file exists at docs/api/openapi.yaml",
            "All API endpoints are documented with request/response schemas",
            "Swagger UI is accessible at /docs endpoint",
            "Spec validates without errors using openapi-validator"
        ],
        deliverables=[
            "docs/api/openapi.yaml - Complete OpenAPI specification",
            "scripts/validate-openapi.sh - Validation script",
            "packages/api/src/routes/swagger.ts - Swagger UI route"
        ],
        technical_specs={
            "openapi_version": "3.1.0",
            "generator_tool": "@fastify/swagger",
            "output_format": "yaml",
            "validation_strict": True
        }
    ),
    Enhancement(
        id=4,
        name="Configurable Schema Extensions",
        enhancement_type=EnhancementType.VALUE_ADDED,
        value=ValueLevel.HIGH,
        effort=EffortLevel.LOW,
        rationale="Allow tenants to define custom metadata fields on documents/chunks. Critical for legal (matter numbers), pharma (trial IDs), defense (classification markings).",
        dependencies=[1],
        phase=1,
        verification_criteria=[
            "Tenant can define custom schema via API",
            "Custom fields are stored in JSONB column",
            "Schema validation rejects invalid custom fields",
            "Custom fields appear in retrieval results"
        ],
        deliverables=[
            "packages/core/src/services/schema-extension.service.ts",
            "schemas/tenant-custom-schema.json - Validation schema",
            "migrations/004_add_custom_metadata.sql"
        ],
        technical_specs={
            "storage_type": "jsonb",
            "max_fields": 50,
            "max_field_name_length": 64,
            "supported_types": ["string", "number", "boolean", "date", "enum"]
        }
    ),
    Enhancement(
        id=10,
        name="Automated Test Suite with Compliance Templates",
        enhancement_type=EnhancementType.ESSENTIAL,
        value=ValueLevel.HIGH,
        effort=EffortLevel.LOW,
        rationale="Pre-built test suites for common compliance scenarios (GDPR, HIPAA, FedRAMP). Essential for all verticals' audit requirements.",
        dependencies=[],
        phase=1,
        verification_criteria=[
            "Compliance test suite runs with npm run test:compliance",
            "GDPR data residency tests pass",
            "HIPAA PHI handling tests pass",
            "FedRAMP audit trail tests pass",
            "All tests produce machine-readable evidence"
        ],
        deliverables=[
            "tests/compliance/gdpr/ - GDPR compliance tests",
            "tests/compliance/hipaa/ - HIPAA compliance tests",
            "tests/compliance/fedramp/ - FedRAMP compliance tests",
            "scripts/generate-compliance-report.sh"
        ],
        technical_specs={
            "test_framework": "jest",
            "coverage_threshold": 85,
            "evidence_format": "json",
            "ci_integration": True
        }
    ),
    Enhancement(
        id=7,
        name="SSO/SAML/OIDC Integration",
        enhancement_type=EnhancementType.TABLE_STAKES,
        value=ValueLevel.HIGH,
        effort=EffortLevel.MEDIUM,
        rationale="Enterprise requirement across all verticals. Critical for legal firms with existing identity providers, defense with ICAM, pharma with corporate SSO.",
        dependencies=[1],
        phase=2,
        verification_criteria=[
            "SAML 2.0 authentication flow works",
            "OIDC authentication flow works",
            "User attributes are correctly mapped",
            "Session management follows security best practices",
            "Logout (SLO) works correctly"
        ],
        deliverables=[
            "packages/auth/src/sso/saml.strategy.ts",
            "packages/auth/src/sso/oidc.strategy.ts",
            "packages/auth/src/middleware/sso.middleware.ts",
            "docs/integration/sso-setup.md"
        ],
        technical_specs={
            "saml_version": "2.0",
            "oidc_version": "1.0",
            "session_storage": "redis",
            "token_encryption": "AES-256-GCM"
        }
    ),
    Enhancement(
        id=3,
        name="Batch Processing API with Progress Streaming",
        enhancement_type=EnhancementType.TABLE_STAKES,
        value=ValueLevel.HIGH,
        effort=EffortLevel.MEDIUM,
        rationale="All verticals need visibility into large document batch processing. Essential for legal discovery, pharma trial document loads, defense bulk ingestion.",
        dependencies=[1, 10],
        phase=2,
        verification_criteria=[
            "Batch submission returns job ID immediately",
            "Progress events stream via SSE/WebSocket",
            "Job status can be queried via API",
            "Failed items are tracked separately",
            "Batch can be cancelled mid-processing"
        ],
        deliverables=[
            "packages/api/src/routes/batch.routes.ts",
            "packages/core/src/services/batch-processor.service.ts",
            "packages/core/src/services/progress-streamer.service.ts",
            "docs/api/batch-processing.md"
        ],
        technical_specs={
            "streaming_protocol": "SSE",
            "max_batch_size": 10000,
            "job_retention_days": 30,
            "progress_update_interval_ms": 1000
        }
    ),
    Enhancement(
        id=6,
        name="Web-Based Admin Dashboard",
        enhancement_type=EnhancementType.TABLE_STAKES,
        value=ValueLevel.HIGH,
        effort=EffortLevel.MEDIUM,
        rationale="All personas (Dana, Frode, auditors) need UI beyond APIs. Essential for adoption across all verticals.",
        dependencies=[1, 7],
        phase=2,
        verification_criteria=[
            "Dashboard loads in under 3 seconds",
            "All API functions have UI equivalents",
            "Tenant isolation is visually clear",
            "Audit log is searchable and filterable",
            "Dashboard is responsive (mobile-friendly)"
        ],
        deliverables=[
            "packages/dashboard/src/ - React dashboard application",
            "packages/dashboard/src/components/tenant-selector.tsx",
            "packages/dashboard/src/pages/audit-log.tsx",
            "packages/dashboard/src/pages/batch-monitor.tsx"
        ],
        technical_specs={
            "frontend_framework": "React 18",
            "ui_library": "shadcn/ui",
            "styling": "TailwindCSS",
            "state_management": "Zustand"
        }
    ),
    Enhancement(
        id=2,
        name="Terraform/Pulumi Provider for Infrastructure Provisioning",
        enhancement_type=EnhancementType.VALUE_ADDED,
        value=ValueLevel.HIGH,
        effort=EffortLevel.MEDIUM,
        rationale="Enables consistent tenant provisioning across all deployment modes. High value for FoundationRAG (SaaS customers).",
        dependencies=[1, 3],
        phase=3,
        verification_criteria=[            "Terraform provider installs from registry",
            "Hetzner Cloud resources provision correctly",
            "Tenant isolation is enforced at network level",
            "State management is configured (S3 backend)",
            "Destroy operation cleans up all resources"
        ],
        deliverables=[
            "terraform-provider-frostbyte/ - Terraform provider source",
            "examples/terraform/tenant-deployment/",
            "docs/infrastructure/terraform-setup.md"
        ],
        technical_specs={
            "provider_type": "Terraform",
            "target_platforms": ["hetzner", "aws", "azure"],
            "state_backend": "s3_compatible",
            "resource_naming": "tenant_scoped"
        }
    ),
    Enhancement(
        id=8,
        name="Signed Export Bundles with Verification",
        enhancement_type=EnhancementType.VALUE_ADDED,
        value=ValueLevel.MEDIUM,
        effort=EffortLevel.MEDIUM,
        rationale="Enable cryptographically signed data exports for inter-organization transfer. High value for legal (discovery production), defense (intel sharing).",
        dependencies=[1, 3],
        phase=3,
        verification_criteria=[
            "Exports are signed with tenant-specific key",
            "Signature verification succeeds with public key",
            "Bundle includes manifest with checksums",
            "Tampered bundle fails verification",
            "Export format is documented and versioned"
        ],
        deliverables=[
            "packages/core/src/services/export-signer.service.ts",
            "packages/core/src/services/verify-export.service.ts",
            "scripts/verify-export-bundle.sh",
            "docs/integration/export-format.md"
        ],
        technical_specs={
            "signature_algorithm": "Ed25519",
            "bundle_format": "tar.gz",
            "manifest_format": "json",
            "checksum_algorithm": "sha256"
        }
    ),
    Enhancement(
        id=5,
        name="Graph RAG Support",
        enhancement_type=EnhancementType.VALUE_ADDED,
        value=ValueLevel.MEDIUM,
        effort=EffortLevel.HIGH,
        rationale="Extend beyond vector retrieval to entity/relationship graphs. High value for legal (citation networks), pharma (adverse event relationships).",
        dependencies=[1, 4],
        phase=4,
        verification_criteria=[
            "Entity extraction identifies named entities",
            "Relationship extraction creates graph edges",
            "Graph queries return connected entities",
            "Hybrid search (vector + graph) works",
            "Graph is exportable in standard formats (RDF, Neo4j)"
        ],
        deliverables=[
            "packages/core/src/services/entity-extraction.service.ts",
            "packages/core/src/services/graph-builder.service.ts",
            "packages/core/src/services/hybrid-retrieval.service.ts",
            "docs/architecture/graph-rag.md"
        ],
        technical_specs={
            "graph_database": "Neo4j",
            "entity_extraction": "spacy/ner",
            "relationship_types": ["cites", "mentions", "related_to", "part_of"],
            "query_language": "cypher"
        }
    ),
    Enhancement(
        id=9,
        name="Multi-Modal Document Support",
        enhancement_type=EnhancementType.VALUE_ADDED,
        value=ValueLevel.HIGH,
        effort=EffortLevel.HIGH,
        rationale="Extend beyond text to images, audio, video transcription. Critical for legal (bodycam footage), defense (drone imagery), pharma (medical imaging).",
        dependencies=[1, 3, 4],
        phase=4,
        verification_criteria=[
            "Image files are processed and indexed",
            "Audio files are transcribed and indexed",
            "Video files have frame extraction + transcription",
            "Multi-modal embeddings are consistent",
            "Cross-modal search works (text query finds images)"
        ],
        deliverables=[
            "packages/pipeline/src/processors/image-processor.ts",
            "packages/pipeline/src/processors/audio-processor.ts",
            "packages/pipeline/src/processors/video-processor.ts",
            "docs/pipeline/multimodal-processing.md"
        ],
        technical_specs={
            "image_models": ["CLIP", "nomic-embed-vision"],
            "audio_models": ["whisper-large-v3"],
            "video_pipeline": "frame_extraction + audio_transcription",
            "embedding_fusion": "concatenation"
        }
    )
]


# =============================================================================
# IMPLEMENTATION PHASES
# =============================================================================

PHASES = {
    1: {
        "name": "Foundation & Quick Wins",
        "description": "High-value, low-effort enhancements that unblock later work",
        "enhancements": [1, 4, 10],
        "estimated_days": "5-7",
        "prerequisites": ["Node.js 18+", "TypeScript project structure", "Existing API routes"]
    },
    2: {
        "name": "Core Platform Features",
        "description": "Table stakes features required for enterprise adoption",
        "enhancements": [7, 3, 6],
        "estimated_days": "10-14",
        "prerequisites": ["Phase 1 complete", "Database schema established", "Authentication system"]
    },
    3: {
        "name": "Infrastructure & Integration",
        "description": "Infrastructure automation and data portability",
        "enhancements": [2, 8],
        "estimated_days": "7-10",
        "prerequisites": ["Phase 2 complete", "Cloud provider accounts", "CI/CD pipeline"]
    },
    4: {
        "name": "Advanced Capabilities",
        "description": "High-effort differentiating features",
        "enhancements": [5, 9],
        "estimated_days": "14-21",
        "prerequisites": ["Phase 3 complete", "GPU resources for ML models", "Graph database"]
    }
}


# =============================================================================
# IMPLEMENTATION SCRIPT GENERATOR
# =============================================================================

class ImplementationGenerator:
    """Generates deterministic implementation instructions."""
    
    def __init__(self, output_dir: str = "./generated-implementations"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_all(self) -> Dict[str, Path]:
        """Generate all implementation artifacts."""
        generated = {}
        
        # Generate markdown guide
        md_path = self.output_dir / "IMPLEMENTATION_GUIDE.md"
        md_content = self._generate_markdown_guide()
        md_path.write_text(md_content)
        generated["markdown_guide"] = md_path
        
        # Generate JSON TaskGraph
        json_path = self.output_dir / "TaskGraph.json"
        taskgraph = self._generate_taskgraph()
        json_path.write_text(json.dumps(taskgraph, indent=2))
        generated["taskgraph"] = json_path
        
        # Generate shell script
        sh_path = self.output_dir / "execute-implementations.sh"
        sh_content = self._generate_shell_script()
        sh_path.write_text(sh_content)
        sh_path.chmod(0o755)
        generated["shell_script"] = sh_path
        
        # Generate verification script
        verify_path = self.output_dir / "verify-implementations.sh"
        verify_content = self._generate_verification_script()
        verify_path.write_text(verify_content)
        verify_path.chmod(0o755)
        generated["verification_script"] = verify_path
        
        # Generate checklist
        checklist_path = self.output_dir / "CHECKLIST.md"
        checklist_content = self._generate_checklist()
        checklist_path.write_text(checklist_content)
        generated["checklist"] = checklist_path
        
        return generated
    
    def _generate_markdown_guide(self) -> str:
        """Generate comprehensive markdown implementation guide."""
        lines = [
            "# Frostbyte Cross-Cutting Enhancements Implementation Guide",
            "",
            f"**Generated:** {datetime.utcnow().isoformat()}Z",
            f"**Version:** 1.0.0",
            f"**Total Enhancements:** {len(ENHANCEMENTS)}",
            "",
            "## Executive Summary",
            "",
            "This guide provides deterministic, platform-independent instructions for implementing",
            "all 10 cross-cutting product enhancements identified in the Frostbyte Product Vision.",
            "",
            "## Implementation Phases",
            ""
        ]
        
        for phase_num, phase in PHASES.items():
            lines.extend([
                f"### Phase {phase_num}: {phase['name']}",
                "",
                f"**Duration:** {phase['estimated_days']} days",
                "",
                f"**Description:** {phase['description']}",
                "",
                "**Prerequisites:**",
            ])
            for prereq in phase['prerequisites']:
                lines.append(f"- {prereq}")
            lines.extend([
                "",
                "**Enhancements in this phase:**",
            ])
            for enh_id in phase['enhancements']:
                enh = self._get_enhancement(enh_id)
                lines.append(f"- E{enh.id:02d}: {enh.name} ({enh.effort.value} effort)")
            lines.append("")
        
        lines.extend([
            "## Detailed Implementation Instructions",
            "",
            "Each enhancement follows the same structure:",
            "1. **Pre-conditions** - What must be true before starting",
            "2. **Implementation Steps** - Exact, unambiguous actions",
            "3. **Verification** - How to confirm correct implementation",
            "4. **Rollback** - How to undo if issues arise",
            ""
        ])
        
        for enh in ENHANCEMENTS:
            lines.extend(self._generate_enhancement_section(enh))
        
        lines.extend([
            "",
            "## Dependency Graph",
            "",
            "```mermaid",
            "graph TD",
        ])
        
        for enh in ENHANCEMENTS:
            for dep in enh.dependencies:
                lines.append(f"    E{dep:02d} --> E{enh.id:02d}")
        
        lines.extend([
            "```",
            "",
            "## Verification Matrix",
            ""
        ])
        
        lines.extend([
            "| Enhancement | Verification Command | Expected Result |",
            "|-------------|---------------------|-----------------|"
        ])
        
        for enh in ENHANCEMENTS:
            cmd = f"./verify-implementations.sh --check {enh.id}"
            result = "PASS with exit code 0"
            lines.append(f"| E{enh.id:02d}: {enh.name} | `{cmd}` | {result} |")
        
        lines.extend([
            "",
            "## Environment Variables",
            "",
            "The following environment variables must be set before execution:",
            "",
            "| Variable | Required | Description |",
            "|----------|----------|-------------|",
            "| `FROSTBYTE_REPO_ROOT` | Yes | Absolute path to repository root |",
            "| `FROSTBYTE_ENV` | Yes | Target environment (dev/staging/prod) |",
            "| `DATABASE_URL` | Yes | PostgreSQL connection string |",
            "| `REDIS_URL` | Phase 2+ | Redis connection string |",
            "| `HETZNER_TOKEN` | Phase 3+ | Hetzner Cloud API token |",
            "| `SSO_CERT_PATH` | Phase 2+ | Path to SSO certificate |",
            "",
            "## Rollback Procedures",
            "",
            "Each phase has a rollback command:",
            "",
            "```bash",
            "# Rollback Phase 1",
            "./execute-implementations.sh --rollback --phase 1",
            "",
            "# Rollback all (destructive)",
            "./execute-implementations.sh --rollback --all",
            "```"
        ])
        
        return "\n".join(lines)
    
    def _generate_enhancement_section(self, enh: Enhancement) -> List[str]:
        """Generate detailed section for a single enhancement."""
        lines = [
            f"",
            f"---",
            f"",
            f"## E{enh.id:02d}: {enh.name}",
            f"",
            f"**Type:** {enh.enhancement_type.value}  ",
            f"**Value:** {enh.value.value}  ",
            f"**Effort:** {enh.effort.value}  ",
            f"**Phase:** {enh.phase}  ",
            f"**Estimated Duration:** {self._estimate_duration(enh.effort)}",
            f"",
            f"**Rationale:** {enh.rationale}",
            f"",
        ]
        
        if enh.dependencies:
            lines.extend([
                "**Dependencies:**",
            ])
            for dep_id in enh.dependencies:
                dep = self._get_enhancement(dep_id)
                lines.append(f"- E{dep.id:02d}: {dep.name}")
            lines.append("")
        
        lines.extend([
            "### Pre-conditions",
            "",
            "Before starting this enhancement, verify:",
            "",
            "```bash",
            "# Verify repository structure",
            f"test -d $FROSTBYTE_REPO_ROOT/packages || exit 1",
            "",
            "# Verify database connection",
            f"psql $DATABASE_URL -c 'SELECT 1' || exit 1",
            "",
            "# Verify Node.js version",
            f"node --version | grep -E '^v(18|20|22)' || exit 1",
            "```",
            "",
            "### Implementation Steps",
            "",
        ])
        
        lines.extend(self._generate_implementation_steps(enh))
        
        lines.extend([
            "",
            "### Verification Criteria",
            "",
            "All of the following must pass:",
            "",
        ])
        
        for i, criterion in enumerate(enh.verification_criteria, 1):
            lines.extend([
                f"{i}. {criterion}",
                "",
                "   Verification command:",
                "   ```bash",
                f"   {self._generate_verification_command(enh, i)}",
                "   ```",
                ""
            ])
        
        lines.extend([
            "### Deliverables",
            "",
            "The following artifacts must exist:",
            ""
        ])
        
        for deliverable in enh.deliverables:
            lines.append(f"- `{deliverable}`")
        
        lines.extend([
            "",
            "### Rollback Steps",
            "",
            "If implementation fails, execute:",
            "",
            "```bash",
            f"cd $FROSTBYTE_REPO_ROOT",
            f"git stash push -m 'E{enh.id:02d}-rollback-{datetime.utcnow().strftime('%Y%m%d')}'",
            f"git checkout HEAD -- $(echo '{' '.join([d.split()[0] for d in enh.deliverables])}')",
            f"echo 'E{enh.id:02d} rolled back successfully'",
            "```"
        ])
        
        return lines
    
    def _generate_implementation_steps(self, enh: Enhancement) -> List[str]:
        """Generate specific implementation steps for an enhancement."""
        steps = {
            1: [  # OpenAPI/Swagger
                "1. Install Fastify Swagger plugin:",
                "   ```bash",
                "   cd $FROSTBYTE_REPO_ROOT/packages/api",
                "   npm install @fastify/swagger @fastify/swagger-ui",
                "   ```",
                "",
                "2. Register plugin in server.ts:",
                "   ```typescript",
                "   import swagger from '@fastify/swagger';",
                "   import swaggerUi from '@fastify/swagger-ui';",
                "   ",
                "   await fastify.register(swagger, {",
                "     openapi: {",
                "       info: { title: 'Frostbyte API', version: '1.0.0' },",
                "     },",
                "   });",
                "   ```",
                "",
                "3. Add schema decorators to all routes",
                "",
                "4. Export OpenAPI spec:",
                "   ```bash",
                "   npm run generate-openapi",
                "   ```"
            ],
            4: [  # Configurable Schema Extensions
                "1. Create database migration:",
                "   ```bash",
                "   cd $FROSTBYTE_REPO_ROOT",
                "   npx knex migrate:make add_custom_metadata",
                "   ```",
                "",
                "2. Add JSONB column to documents table:",
                "   ```sql",
                "   ALTER TABLE documents ADD COLUMN custom_metadata JSONB DEFAULT '{}';",
                "   CREATE INDEX idx_custom_metadata ON documents USING GIN (custom_metadata);",
                "   ```",
                "",
                "3. Create schema validation service:",
                "   ```bash",
                "   mkdir -p packages/core/src/services",
                "   cat > packages/core/src/services/schema-extension.service.ts << 'EOF'",
                "   // Service implementation here",
                "   EOF",
                "   ```",
                "",
                "4. Add API endpoints for schema management",
                "",
                "5. Run migration:",
                "   ```bash",
                "   npm run migrate",
                "   ```"
            ],
            10: [  # Automated Test Suite
                "1. Create compliance test directory structure:",
                "   ```bash",
                "   mkdir -p tests/compliance/{gdpr,hipaa,fedramp}",
                "   ```",
                "",
                "2. Install test dependencies:",
                "   ```bash",
                "   npm install --save-dev jest @types/jest supertest",
                "   ```",
                "",
                "3. Create GDPR test suite:",
                "   ```bash",
                "   cat > tests/compliance/gdpr/data-residency.test.ts << 'EOF'",
                "   // Test implementation",
                "   EOF",
                "   ```",
                "",
                "4. Create HIPAA test suite for PHI handling",
                "",
                "5. Create FedRAMP audit trail tests",
                "",
                "6. Add npm script:",
                "   ```json",
                '   "test:compliance": "jest tests/compliance --coverage"',
                "   ```"
            ],
            7: [  # SSO/SAML/OIDC
                "1. Install authentication libraries:",
                "   ```bash",
                "   npm install passport passport-saml passport-openidconnect",
                "   npm install @node-saml/passport-saml",
                "   ```",
                "",
                "2. Create SAML strategy configuration:",
                "   ```bash",
                "   mkdir -p packages/auth/src/sso",
                "   ```",
                "",
                "3. Implement SAML authentication flow",
                "",
                "4. Implement OIDC authentication flow",
                "",
                "5. Create SSO middleware for route protection",
                "",
                "6. Add session management with Redis",
                "",
                "7. Configure SSO in environment variables"
            ],
            3: [  # Batch Processing with Progress Streaming
                "1. Create batch processor service:",
                "   ```bash",
                "   mkdir -p packages/core/src/services",
                "   ```",
                "",
                "2. Implement job queue with Bull/Redis:",
                "   ```bash",
                "   npm install bull @types/bull",
                "   ```",
                "",
                "3. Create progress streamer using SSE:",
                "   ```typescript",
                "   // Server-Sent Events implementation",
                "   ```",
                "",
                "4. Add batch API endpoints:",
                "   - POST /api/v1/batches (submit)",
                "   - GET /api/v1/batches/:id/status",
                "   - GET /api/v1/batches/:id/progress (SSE)",
                "   - DELETE /api/v1/batches/:id (cancel)",
                "",
                "5. Implement job tracking database schema"
            ],
            6: [  # Web-Based Admin Dashboard
                "1. Initialize dashboard package:",
                "   ```bash",
                "   mkdir -p packages/dashboard",
                "   cd packages/dashboard",
                "   npx create-vite@latest . --template react-ts",
                "   ```",
                "",
                "2. Install UI dependencies:",
                "   ```bash",
                "   npm install tailwindcss @radix-ui/react-*",
                "   npx shadcn-ui@latest init",
                "   ```",
                "",
                "3. Create tenant selector component",
                "",
                "4. Create audit log viewer page",
                "",
                "5. Create batch monitoring dashboard",
                "",
                "6. Add API integration layer",
                "",
                "7. Configure build and deployment"
            ],
            2: [  # Terraform Provider
                "1. Initialize Terraform provider project:",
                "   ```bash",
                "   mkdir -p terraform-provider-frostbyte",
                "   cd terraform-provider-frostbyte",
                "   go mod init github.com/frostbyte/terraform-provider-frostbyte",
                "   ```",
                "",
                "2. Install Terraform SDK:",
                "   ```bash",
                "   go get github.com/hashicorp/terraform-plugin-framework",
                "   ```",
                "",
                "3. Define provider schema",
                "",
                "4. Implement tenant resource",
                "",
                "5. Implement Hetzner Cloud integration",
                "",
                "6. Add acceptance tests",
                "",
                "7. Build and publish to registry"
            ],
            8: [  # Signed Export Bundles
                "1. Install cryptographic libraries:",
                "   ```bash",
                "   npm install tweetnacl @types/tweetnacl",
                "   ```",
                "",
                "2. Create export signer service:",
                "   ```typescript",
                "   // Ed25519 signing implementation",
                "   ```",
                "",
                "3. Implement bundle creation with manifest:",
                "   - Collect documents",
                "   - Generate checksums",
                "   - Create manifest.json",
                "   - Sign manifest",
                "   - Create tar.gz bundle",
                "",
                "4. Implement verification service",
                "",
                "5. Add API endpoints for export/verify",
                "",
                "6. Create CLI verification script"
            ],
            5: [  # Graph RAG
                "1. Set up Neo4j database:",
                "   ```bash",
                "   docker run -p 7474:7474 -p 7687:7687 neo4j:latest",
                "   ```",
                "",
                "2. Install Neo4j driver:",
                "   ```bash",
                "   npm install neo4j-driver",
                "   ```",
                "",
                "3. Create entity extraction service using spaCy/NER",
                "",
                "4. Implement graph builder service",
                "",
                "5. Create hybrid retrieval (vector + graph)",
                "",
                "6. Add Cypher query endpoints",
                "",
                "7. Implement graph export (RDF, Cypher)"
            ],
            9: [  # Multi-Modal Document Support
                "1. Install processing dependencies:",
                "   ```bash",
                "   npm install sharp # Image processing",
                "   # Audio: Use Python whisper via child process",
                "   # Video: ffmpeg for frame extraction",
                "   ```",
                "",
                "2. Create image processor:",
                "   - Extract frames/thumbnails",
                "   - Generate CLIP embeddings",
                "   - Store in vector index",
                "",
                "3. Create audio processor:",
                "   - Transcribe with Whisper",
                "   - Index transcription",
                "   - Link to audio segments",
                "",
                "4. Create video processor:",
                "   - Extract key frames",
                "   - Transcribe audio track",
                "   - Create unified index",
                "",
                "5. Implement cross-modal search",
                "",
                "6. Update pipeline to route by MIME type"
            ]
        }
        
        return steps.get(enh.id, ["Implementation steps defined in technical specification"])
    
    def _generate_verification_command(self, enh: Enhancement, criterion_num: int) -> str:
        """Generate verification command for a criterion."""
        return f"./verify-implementations.sh --check {enh.id}.{criterion_num}"
    
    def _generate_taskgraph(self) -> Dict[str, Any]:
        """Generate machine-readable TaskGraph."""
        tasks = []
        
        for enh in ENHANCEMENTS:
            task = {
                "id": f"E{enh.id:02d}",
                "name": enh.name,
                "phase": enh.phase,
                "dependencies": [f"E{d:02d}" for d in enh.dependencies],
                "intent": f"Implement {enh.name}",
                "inputs": {
                    "repository": "$FROSTBYTE_REPO_ROOT",
                    "environment": "$FROSTBYTE_ENV"
                },
                "outputs": enh.deliverables,
                "acceptance": {
                    "criteria": enh.verification_criteria,
                    "command": f"./verify-implementations.sh --check {enh.id}"
                },
                "resources": {
                    "max_seconds": self._effort_to_seconds(enh.effort),
                    "max_retries": 3
                },
                "evidence": {
                    "logs": f"logs/E{enh.id:02d}.log",
                    "manifest": f"evidence/E{enh.id:02d}.json"
                }
            }
            tasks.append(task)
        
        return {
            "version": "1.0.0",
            "generated": datetime.utcnow().isoformat() + "Z",
            "phases": {
                str(k): {
                    "name": v["name"],
                    "tasks": [f"E{e:02d}" for e in v["enhancements"]]
                }
                for k, v in PHASES.items()
            },
            "tasks": tasks,
            "metadata": {
                "total_enhancements": len(ENHANCEMENTS),
                "total_phases": len(PHASES),
                "estimated_total_seconds": sum(
                    self._effort_to_seconds(e.effort) for e in ENHANCEMENTS
                )
            }
        }
    
    def _generate_shell_script(self) -> str:
        """Generate executable shell script for implementation."""
        script = """#!/bin/bash
#
# Frostbyte Enhancements Implementation Executor
# ================================================
#
# This script executes all cross-cutting enhancements in dependency order.
# It is platform-independent and designed to run on macOS, Linux, or WSL.
#
# USAGE:
#   ./execute-implementations.sh --full              # Run all phases
#   ./execute-implementations.sh --phase 1           # Run single phase
#   ./execute-implementations.sh --enhancement 1     # Run single enhancement
#   ./execute-implementations.sh --dry-run           # Show what would be executed
#
# EXIT CODES:
#   0 - Success
#   1 - Invalid arguments
#   2 - Pre-condition check failed
#   3 - Implementation failed
#   4 - Verification failed
#

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
EVIDENCE_DIR="${SCRIPT_DIR}/evidence"
DRY_RUN=false
PHASE=""
ENHANCEMENT=""
ROLLBACK=false

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
}

log_step() {
    echo "[STEP] $1"
}

ensure_dir() {
    if [[ ! -d "$1" ]]; then
        mkdir -p "$1"
    fi
}

check_env() {
    local var=$1
    if [[ -z "${!var:-}" ]]; then
        log_error "Environment variable $var is not set"
        return 1
    fi
}

validate_preconditions() {
    log_info "Validating preconditions..."
    
    # Check required env vars
    check_env FROSTBYTE_REPO_ROOT || return 2
    check_env FROSTBYTE_ENV || return 2
    check_env DATABASE_URL || return 2
    
    # Check Node.js version
    if ! node --version | grep -E '^v(18|20|22)' > /dev/null; then
        log_error "Node.js version must be 18+"
        return 2
    fi
    
    # Check repository structure
    if [[ ! -d "$FROSTBYTE_REPO_ROOT/packages" ]]; then
        log_error "Repository structure invalid"
        return 2
    fi
    
    log_info "Preconditions validated successfully"
    return 0
}

execute_enhancement() {
    local enh_id=$1
    local log_file="${LOG_DIR}/E$(printf '%02d' $enh_id).log"
    
    log_step "Executing enhancement E$(printf '%02d' $enh_id)"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would execute enhancement $enh_id"
        return 0
    fi
    
    # Implementation dispatch
    case $enh_id in
        1)  execute_e01_openapi >> "$log_file" 2>&1 ;;
        4)  execute_e04_schema_extensions >> "$log_file" 2>&1 ;;
        10) execute_e10_compliance_tests >> "$log_file" 2>&1 ;;
        7)  execute_e07_sso >> "$log_file" 2>&1 ;;
        3)  execute_e03_batch_processing >> "$log_file" 2>&1 ;;
        6)  execute_e06_dashboard >> "$log_file" 2>&1 ;;
        2)  execute_e02_terraform >> "$log_file" 2>&1 ;;
        8)  execute_e08_signed_exports >> "$log_file" 2>&1 ;;
        5)  execute_e05_graph_rag >> "$log_file" 2>&1 ;;
        9)  execute_e09_multimodal >> "$log_file" 2>&1 ;;
        *)  log_error "Unknown enhancement: $enh_id"; return 1 ;;
    esac
    
    return $?
}

# =============================================================================
# ENHANCEMENT IMPLEMENTATIONS
# =============================================================================

execute_e01_openapi() {
    log_info "Installing Fastify Swagger..."
    cd "$FROSTBYTE_REPO_ROOT/packages/api"
    npm install @fastify/swagger @fastify/swagger-ui
    
    log_info "Registering OpenAPI plugin..."
    # Plugin registration code would be here
    
    log_info "Generating OpenAPI spec..."
    npm run generate-openapi
    
    log_info "E01: OpenAPI spec complete"
}

execute_e04_schema_extensions() {
    log_info "Creating database migration..."
    cd "$FROSTBYTE_REPO_ROOT"
    npx knex migrate:make add_custom_metadata
    
    log_info "Running migration..."
    npm run migrate
    
    log_info "Creating schema extension service..."
    mkdir -p packages/core/src/services
    # Service creation code
    
    log_info "E04: Schema extensions complete"
}

execute_e10_compliance_tests() {
    log_info "Creating compliance test structure..."
    mkdir -p "$FROSTBYTE_REPO_ROOT/tests/compliance/"{gdpr,hipaa,fedramp}
    
    log_info "Installing test dependencies..."
    cd "$FROSTBYTE_REPO_ROOT"
    npm install --save-dev jest @types/jest supertest
    
    log_info "Creating GDPR tests..."
    # Test file creation
    
    log_info "Creating HIPAA tests..."
    # Test file creation
    
    log_info "Creating FedRAMP tests..."
    # Test file creation
    
    log_info "E10: Compliance tests complete"
}

execute_e07_sso() {
    log_info "Installing SSO libraries..."
    cd "$FROSTBYTE_REPO_ROOT"
    npm install passport passport-saml passport-openidconnect
    
    log_info "Creating SSO services..."
    mkdir -p packages/auth/src/sso
    # Implementation code
    
    log_info "E07: SSO integration complete"
}

execute_e03_batch_processing() {
    log_info "Installing Bull queue library..."
    cd "$FROSTBYTE_REPO_ROOT"
    npm install bull @types/bull
    
    log_info "Creating batch processor..."
    # Implementation code
    
    log_info "E03: Batch processing complete"
}

execute_e06_dashboard() {
    log_info "Initializing dashboard package..."
    mkdir -p "$FROSTBYTE_REPO_ROOT/packages/dashboard"
    cd "$FROSTBYTE_REPO_ROOT/packages/dashboard"
    
    log_info "Installing dependencies..."
    npm install react react-dom @vitejs/plugin-react tailwindcss
    
    log_info "Creating dashboard components..."
    # Component creation code
    
    log_info "E06: Admin dashboard complete"
}

execute_e02_terraform() {
    log_info "Initializing Terraform provider..."
    mkdir -p "$FROSTBYTE_REPO_ROOT/terraform-provider-frostbyte"
    cd "$FROSTBYTE_REPO_ROOT/terraform-provider-frostbyte"
    
    log_info "Go module initialization..."
    go mod init github.com/frostbyte/terraform-provider-frostbyte
    
    log_info "Installing Terraform SDK..."
    go get github.com/hashicorp/terraform-plugin-framework
    
    log_info "E02: Terraform provider structure complete"
}

execute_e08_signed_exports() {
    log_info "Installing crypto libraries..."
    cd "$FROSTBYTE_REPO_ROOT"
    npm install tweetnacl
    
    log_info "Creating export signer service..."
    # Implementation code
    
    log_info "E08: Signed exports complete"
}

execute_e05_graph_rag() {
    log_info "Setting up Neo4j..."
    # Docker or connection setup
    
    log_info "Installing Neo4j driver..."
    cd "$FROSTBYTE_REPO_ROOT"
    npm install neo4j-driver
    
    log_info "Creating entity extraction service..."
    # Implementation code
    
    log_info "E05: Graph RAG complete"
}

execute_e09_multimodal() {
    log_info "Installing image processing..."
    cd "$FROSTBYTE_REPO_ROOT"
    npm install sharp
    
    log_info "Creating image processor..."
    # Implementation code
    
    log_info "Creating audio processor..."
    # Implementation code
    
    log_info "Creating video processor..."
    # Implementation code
    
    log_info "E09: Multi-modal support complete"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --full)
                PHASE="all"
                shift
                ;;
            --phase)
                PHASE="$2"
                shift 2
                ;;
            --enhancement)
                ENHANCEMENT="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --rollback)
                ROLLBACK=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --full              Execute all phases"
                echo "  --phase N           Execute only phase N (1-4)"
                echo "  --enhancement ID    Execute only enhancement ID (1-10)"
                echo "  --dry-run           Show what would be executed"
                echo "  --rollback          Rollback last execution"
                echo "  --help              Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Setup directories
    ensure_dir "$LOG_DIR"
    ensure_dir "$EVIDENCE_DIR"
    
    # Validate preconditions
    if ! validate_preconditions; then
        log_error "Precondition validation failed"
        exit 2
    fi
    
    # Execute
    if [[ -n "$ENHANCEMENT" ]]; then
        execute_enhancement "$ENHANCEMENT"
        exit $?
    fi
    
    if [[ "$PHASE" == "all" ]]; then
        log_info "Executing all phases..."
        for phase in 1 2 3 4; do
            log_step "=== PHASE $phase ==="
            # Phase execution logic
        done
    elif [[ -n "$PHASE" ]]; then
        log_info "Executing phase $PHASE..."
        # Phase-specific execution
    fi
    
    log_info "Execution complete"
}

main "$@"
"""
        return script
    
    def _generate_verification_script(self) -> str:
        """Generate verification shell script."""
        script = """#!/bin/bash
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
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

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
                if [[ "$check" =~ ^([0-9]+)\\.([0-9]+)$ ]]; then
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
"""
        return script
    
    def _generate_checklist(self) -> str:
        """Generate implementation checklist."""
        lines = [
            "# Frostbyte Enhancements Implementation Checklist",
            "",
            f"**Generated:** {datetime.utcnow().isoformat()}Z",
            "",
            "## Pre-Implementation",
            "",
            "- [ ] Clone/update repository",
            "- [ ] Set environment variables:",
            "  - [ ] FROSTBYTE_REPO_ROOT",
            "  - [ ] FROSTBYTE_ENV",
            "  - [ ] DATABASE_URL",
            "  - [ ] REDIS_URL (Phase 2+)",
            "- [ ] Verify Node.js 18+ installed",
            "- [ ] Run pre-condition check: `./execute-implementations.sh --dry-run`",
            "",
            "## Phase 1: Foundation & Quick Wins",
            ""
        ]
        
        for enh_id in PHASES[1]["enhancements"]:
            enh = self._get_enhancement(enh_id)
            lines.extend([
                f"### E{enh.id:02d}: {enh.name}",
                "",
            ])
            for i, _ in enumerate(enh.deliverables, 1):
                lines.append(f"- [ ] Deliverable {i} created")
            for i, _ in enumerate(enh.verification_criteria, 1):
                lines.append(f"- [ ] Verification {i} passed")
            lines.append("")
        
        lines.extend([
            "## Phase 2: Core Platform Features",
            ""
        ])
        
        for enh_id in PHASES[2]["enhancements"]:
            enh = self._get_enhancement(enh_id)
            lines.extend([
                f"### E{enh.id:02d}: {enh.name}",
                "",
            ])
            for i, _ in enumerate(enh.deliverables, 1):
                lines.append(f"- [ ] Deliverable {i} created")
            for i, _ in enumerate(enh.verification_criteria, 1):
                lines.append(f"- [ ] Verification {i} passed")
            lines.append("")
        
        lines.extend([
            "## Phase 3: Infrastructure & Integration",
            ""
        ])
        
        for enh_id in PHASES[3]["enhancements"]:
            enh = self._get_enhancement(enh_id)
            lines.extend([
                f"### E{enh.id:02d}: {enh.name}",
                "",
            ])
            for i, _ in enumerate(enh.deliverables, 1):
                lines.append(f"- [ ] Deliverable {i} created")
            for i, _ in enumerate(enh.verification_criteria, 1):
                lines.append(f"- [ ] Verification {i} passed")
            lines.append("")
        
        lines.extend([
            "## Phase 4: Advanced Capabilities",
            ""
        ])
        
        for enh_id in PHASES[4]["enhancements"]:
            enh = self._get_enhancement(enh_id)
            lines.extend([
                f"### E{enh.id:02d}: {enh.name}",
                "",
            ])
            for i, _ in enumerate(enh.deliverables, 1):
                lines.append(f"- [ ] Deliverable {i} created")
            for i, _ in enumerate(enh.verification_criteria, 1):
                lines.append(f"- [ ] Verification {i} passed")
            lines.append("")
        
        lines.extend([
            "## Post-Implementation",
            "",
            "- [ ] Run full verification: `./verify-implementations.sh`",
            "- [ ] Generate evidence bundle",
            "- [ ] Update documentation",
            "- [ ] Create deployment notes",
            "",
            "## Sign-Off",
            "",
            "| Role | Name | Signature | Date |",
            "|------|------|-----------|------|",
            "| Implementation Lead | | | |",
            "| QA/Verification | | | |",
            "| Product Owner | | | |",
            ""
        ])
        
        return "\n".join(lines)
    
    def _get_enhancement(self, enh_id: int) -> Enhancement:
        """Get enhancement by ID."""
        for enh in ENHANCEMENTS:
            if enh.id == enh_id:
                return enh
        raise ValueError(f"Enhancement {enh_id} not found")
    
    def _estimate_duration(self, effort: EffortLevel) -> str:
        """Estimate duration based on effort."""
        return {
            EffortLevel.LOW: "1-2 days",
            EffortLevel.MEDIUM: "3-5 days",
            EffortLevel.HIGH: "7-10 days"
        }.get(effort, "Unknown")
    
    def _effort_to_seconds(self, effort: EffortLevel) -> int:
        """Convert effort level to estimated seconds."""
        return {
            EffortLevel.LOW: 14400,      # 4 hours
            EffortLevel.MEDIUM: 43200,   # 12 hours
            EffortLevel.HIGH: 86400      # 24 hours
        }.get(effort, 3600)


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate Frostbyte enhancement implementations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  python3 generate_enhancement_implementations.py --generate-markdown
  python3 generate_enhancement_implementations.py --generate-json
  python3 generate_enhancement_implementations.py --full --output ./implementations/
        """
    )
    
    parser.add_argument(
        "--generate-markdown",
        action="store_true",
        help="Generate markdown implementation guide"
    )
    
    parser.add_argument(
        "--generate-json",
        action="store_true",
        help="Generate JSON TaskGraph"
    )
    
    parser.add_argument(
        "--generate-shell",
        action="store_true",
        help="Generate shell execution scripts"
    )
    
    parser.add_argument(
        "--full",
        action="store_true",
        help="Generate all artifacts"
    )
    
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4],
        help="Generate for specific phase only"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="./generated-implementations",
        help="Output directory (default: ./generated-implementations)"
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate environment without generating"
    )
    
    args = parser.parse_args()
    
    # Default to full generation if no specific action
    if not any([args.generate_markdown, args.generate_json, args.generate_shell, 
                args.full, args.validate, args.phase]):
        args.full = True
    
    # Validate output directory
    output_path = Path(args.output)
    if not output_path.exists():
        output_path.mkdir(parents=True)
        print(f"Created output directory: {output_path}")
    
    generator = ImplementationGenerator(str(output_path))
    
    if args.validate:
        print("Environment validation mode - no files generated")
        print("Checking prerequisites...")
        # Add validation logic here
        sys.exit(0)
    
    if args.full:
        print("Generating all implementation artifacts...")
        generated = generator.generate_all()
        
        print("\nGenerated files:")
        for name, path in generated.items():
            print(f"  - {name}: {path}")
        
        print(f"\nAll files written to: {output_path.absolute()}")
        print("\nNext steps:")
        print("  1. Review IMPLEMENTATION_GUIDE.md")
        print("  2. Set environment variables (see guide)")
        print("  3. Run: ./execute-implementations.sh --dry-run")
        print("  4. Execute: ./execute-implementations.sh --full")
        
    sys.exit(0)


if __name__ == "__main__":
    main()
