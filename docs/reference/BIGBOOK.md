# Frostbyte ETL

> Multi-tenant document processing pipeline: document in → structure out → stored in DB and vector store.

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Architecture](#architecture)
4. [How-To Guides](#how-to-guides)
5. [Reference](#reference)
6. [Development](#development)
7. [Operations](#operations)
8. [Troubleshooting](#troubleshooting)
9. [Project Status](#project-status)
10. [Appendix](#appendix)

---

## Overview

### What is Frostbyte ETL?

A document processing pipeline that:
1. **Intakes** documents via API (PDF, DOCX, TXT, images)
2. **Parses** content using Docling/Unstructured
3. **Embeds** text into 768-dimensional vectors (Nomic)
4. **Stores** in three locations: MinIO (raw), PostgreSQL (metadata), Qdrant (vectors)
5. **Serves** via RAG API with retrieval proofs

### Key Features

| Feature | Status |
|---------|--------|
| Multi-tenant isolation | ✅ Complete |
| Real-time event streaming | ✅ Fixed & working |
| Model observability dashboard | ✅ Complete |
| Batch document processing | ✅ Complete |
| Offline mode (Docker bundle) | 📋 Planned |

### System Requirements

- Docker Desktop
- Python 3.12+
- 8GB RAM minimum
- Ports: 5174 (UI), 8000 (API), 5433, 6379, 9000, 6333

---

## Getting Started

### Quick Start (5 minutes)

```bash
# 1. Start infrastructure and pipeline
make start

# 2. Open dashboard
open http://localhost:5174/admin/

# 3. Upload a test document
curl -X POST http://localhost:8000/api/v1/intake \
  -F "file=@/path/to/document.pdf" \
  -F "tenant_id=default"
```

### First Time Setup

```bash
# Install dependencies
cd pipeline && pip install -e .

# Run migrations
./scripts/run_migrations.sh

# Start infrastructure only (if using local dev)
docker-compose up -d redis postgres minio qdrant

# Start pipeline API
make pipeline
```

### Verify Installation

```bash
# Check all services
make status

# Test event streaming
./scripts/test-event-stream.sh

# Health check
curl http://localhost:8000/health
```

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        PRESENTATION                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Admin UI   │  │   Document   │  │   Model          │  │
│  │   (React)    │  │   Upload     │  │   Observatory    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
└─────────┼────────────────┼───────────────────┼─────────────┘
          │                │                   │
          └────────────────┴───────────────────┘
                          │
                   ┌──────▼──────┐
                   │  Pipeline   │
                   │    API      │
                   │  (FastAPI)  │
                   └──────┬──────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
┌───▼────┐  ┌───────────▼────────┐  ┌────────▼─────┐
│ PARSE  │  │       EMBED        │  │    VECTOR    │
│Docling │  │Nomic/OpenRouter 768d│  │   Qdrant     │
└───┬────┘  └───────────┬────────┘  └────────┬─────┘
    │                   │                    │
    └───────────────────┴────────────────────┘
                        │
              ┌─────────▼──────────┐
              │  Event Stream      │
              │  (Redis pub/sub)   │
              └────────────────────┘
```

### Data Flow

1. **Intake** → Document uploaded, validated, stored in MinIO
2. **Parse** → Text extracted, chunked, structured JSON created
3. **Embed** → 768d vectors generated per chunk
4. **Vector** → Embeddings stored in Qdrant per tenant
5. **Metadata** → Document info indexed in PostgreSQL

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | React + Vite + Tailwind | Admin dashboard |
| API | FastAPI (Python) | HTTP API + SSE streaming |
| Parsing | Unstructured + Docling | Document text extraction |
| Embeddings | Nomic (local) / OpenRouter | 768d text vectors |
| Vector DB | Qdrant | Similarity search |
| Object Store | MinIO | Raw document storage |
| Database | PostgreSQL | Metadata and audit |
| Cache/Queue | Redis | Events and job queue |

---

## How-To Guides

### How to Upload a Document

**Via Dashboard:**
1. Navigate to `/documents`
2. Drag file to upload area or click to browse
3. Watch Pipeline Log for processing events

**Via API:**
```bash
curl -X POST http://localhost:8000/api/v1/intake \
  -F "file=@document.pdf" \
  -F "tenant_id=default"
```

### How to Monitor Processing

1. **Pipeline Log** - Real-time events from all stages
2. **Model Activity Monitor** - Model-level events with filtering
3. **Decision Tracer** - Inspect model inputs/outputs (click any event)

### How to Configure LLM Providers

1. Go to `/settings`
2. Select "LLM Providers" tab
3. Toggle providers on/off
4. Configure API keys and endpoints

### How to Rollback a Model Version

1. Go to `/observatory`
2. Click "Provenance Timeline"
3. Select previous version
4. Click "[ROLLBACK]"

### How to Troubleshoot Failed Documents

1. Check Pipeline Log for error messages
2. Click failed document in Document Queue
3. View Decision Tracer for detailed error
4. Retry via `[RETRY]` button

---

## Reference

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/intake` | POST | Upload document |
| `/api/v1/pipeline/stream` | GET | SSE event stream |
| `/api/v1/documents/{id}` | GET | Get document metadata |
| `/health` | GET | Health check |

### Event Types

| Stage | Event | Description |
|-------|-------|-------------|
| INTAKE | `File received` | Document uploaded |
| INTAKE | `Stored to MinIO` | Raw file saved |
| PARSE | `Starting parse` | Parsing begun |
| PARSE | `Parse complete` | Text extracted |
| EMBED | `Generated 768d embedding` | Vectors created |
| VECTOR | `Upserted to Qdrant` | Stored in vector DB |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FROSTBYTE_AUTH_BYPASS` | `false` | Disable auth for dev |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `POSTGRES_URL` | `postgresql://...` | Database connection |
| `MINIO_ENDPOINT` | `http://localhost:9000` | Object storage |
| `QDRANT_URL` | `http://localhost:6333` | Vector database |

### File Structure

```
frostbyte/
├── pipeline/              # Backend API
│   ├── pipeline/         # Main package
│   │   ├── main.py       # FastAPI app
│   │   ├── events.py     # Event publishing
│   │   ├── parsing/      # Document parsing
│   │   └── multimodal/   # Image/audio/video
│   └── tests/            # Test suite
├── packages/
│   └── admin-dashboard/  # Frontend
│       ├── src/
│       │   ├── features/ # Components
│       │   ├── pages/    # Route pages
│       │   └── hooks/    # React hooks
│       └── package.json
├── scripts/              # Operational scripts
├── docs/                 # Documentation
├── docker-compose.yml    # Infrastructure
└── Makefile             # Quick commands
```

---

## Development

### Setting Up Development Environment

```bash
# 1. Clone and install
git clone <repo>
cd pipeline && pip install -e ".[dev]"

# 2. Start infrastructure
docker-compose up -d

# 3. Run migrations
./scripts/run_migrations.sh

# 4. Start API in dev mode
cd pipeline
uvicorn pipeline.main:app --reload --port 8000

# 5. In another terminal, start frontend
cd packages/admin-dashboard
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
cd pipeline
pytest

# Frontend linting
cd packages/admin-dashboard
npm run lint
```

### Adding a New Pipeline Stage

1. Create processor in `pipeline/pipeline/{stage}/`
2. Add event publishing using `publish_async()`
3. Update PipelineSchematic component
4. Add tests

---

## Operations

### Starting the System

```bash
# Full production start
make start

# Development (hot reload)
make dev

# Just infrastructure
docker-compose up -d
```

### Monitoring

```bash
# Check all services
make status

# View logs
make logs
make logs-api       # Pipeline only
make logs-dashboard # Frontend only

# Check specific service
docker ps
redis-cli ping
```

### Stopping the System

```bash
# Stop everything
make stop

# Stop just pipeline
make pipeline-stop

# Full reset (DESTROYS DATA)
make reset
```

### Backup and Restore

```bash
# Backup PostgreSQL
docker exec frostbyte-postgres pg_dump -U frostbyte frostbyte > backup.sql

# Restore PostgreSQL
docker exec -i frostbyte-postgres psql -U frostbyte frostbyte < backup.sql
```

---

## Troubleshooting

### Pipeline Shows "DISCONNECTED"

**Symptoms:** Dashboard shows red dot, no events appearing

**Solutions:**
1. Check if pipeline is running: `make pipeline-status`
2. Start pipeline: `make pipeline`
3. Check Redis: `redis-cli ping`
4. Test SSE: `curl -N http://localhost:8000/api/v1/pipeline/stream`

### Document Upload Fails

**Symptoms:** Upload returns error or hangs

**Solutions:**
1. Check file size (< 100MB)
2. Check file type (PDF, DOCX, TXT supported)
3. Check CORS: Open browser dev tools → Network tab
4. Verify tenant_id is correct
5. Check pipeline logs: `make pipeline-logs`

### Events Stop After Intake

**Symptoms:** See INTAKE event, then nothing

**Causes:**
- Parsing/embedding workers not running
- Python dependencies missing

**Fix:**
```bash
cd pipeline
pip install -e ".[parse,embed]"
```

### Port Already in Use

**Symptoms:** "Address already in use" error

**Fix:**
```bash
# Kill process on port 8000
kill -9 $(lsof -t -i:8000)

# Or use different port
uvicorn pipeline.main:app --port 8001
```

### Database Connection Errors

**Symptoms:** "Connection refused" to Postgres

**Fix:**
```bash
# Check if Postgres is running
docker ps | grep postgres

# Restart if needed
docker-compose restart postgres

# Run migrations
./scripts/run_migrations.sh
```

---

## Project Status

### Implementation Progress

| Phase | Status | Completion |
|-------|--------|------------|
| 1. Product Definition | ✅ Complete | 2026-02-08 |
| 2. Tenant Isolation | ✅ Complete | 2026-02-09 |
| 3. Audit & Safety | ✅ Complete | 2026-02-11 |
| 4. Foundation Layer | ✅ Complete | 2026-02-11 |
| 5. Intake & Parsing | ✅ Complete | 2026-02-11 |
| 6. Policy/Embed/Serve | 📋 Planned | — |
| 7. Deployment | 📋 Docs only | — |
| 8. Team Readiness | 🟡 2/3 | 08-03 pending |

### Design Review Status

**Source:** `.kombai/resources/design-review-frostbyte-admin-comprehensive-20260214.md`

| Priority | Issues | Complete | Remaining |
|----------|--------|----------|-----------|
| 1. Observability | 10 | ✅ 10/10 | 0 |
| 2. Accessibility | 5 | ✅ 4/5 | 1 (real API) |
| 3. Mobile | 4 | ❌ 0/4 | 4 |
| 4. Error Handling | 9 | ✅ 7/9 | 2 (pagination) |
| 5. UX Polish | 19 | ✅ 17/19 | 2 |

**Total:** 67 issues identified, 52 complete, 15 remaining

### Known Issues

1. **Mobile responsive design** - Dashboard breaks on screens < 768px
2. **Pagination missing** - Document queue loads all at once
3. **Mock data** - Some components use hardcoded data
4. **Role play scenarios** - 08-03 documentation incomplete

### Next Milestones

1. ✅ Fix event streaming (COMPLETED)
2. 🔄 Mobile responsive design
3. 🔄 Pagination implementation
4. 📋 Policy engine implementation
5. 📋 Embedding service hardening

---

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| **ETL** | Extract, Transform, Load |
| **SSE** | Server-Sent Events |
| **RAG** | Retrieval-Augmented Generation |
| **Embedding** | Vector representation of text |
| **Tenant** | Isolated customer workspace |
| **Provenance** | History/trace of changes |
| **Observability** | Ability to monitor system internals |

### Changelog

| Date | Change |
|------|--------|
| 2026-02-14 | Fixed event streaming in all pipeline stages |
| 2026-02-14 | Created unified documentation (BigBook) |
| 2026-02-14 | Completed Settings and Jobs pages |
| 2026-02-14 | Implemented Model Observatory components |

### Related Documents

- `.planning/PROJECT.md` - Original project planning
- `.kombai/resources/design-review-*.md` - Design review findings
- `docs/product/PRD.md` - Product requirements
- `docs/reference/TECH_DECISIONS.md` - Technology choices

### License

MIT License - See LICENSE file

---

**End of Document**

*This is the single source of truth for the Frostbyte ETL project. All other documents are subordinate to this one.*
