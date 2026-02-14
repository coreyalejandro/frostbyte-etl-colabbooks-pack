# Frostbyte ETL Pipeline — Operations Guide

## Quick Start (The New Way)

```bash
# Start everything with one command
make start

# Or use the script directly
./scripts/start-frostbyte.sh start
```

That's it. All services start in the correct order with health checks.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Docker Compose Stack                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Presentation Layer                               │   │
│  │  ┌─────────────────┐                                                │   │
│  │  │ Admin Dashboard │  Port: 5174                                     │   │
│  │  │   (React/Vite)  │  Depends on: Pipeline API                       │   │
│  │  └────────┬────────┘                                                │   │
│  └───────────┼─────────────────────────────────────────────────────────┘   │
│              │                                                              │
│              ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Application Layer                               │   │
│  │  ┌─────────────────┐                                                │   │
│  │  │  Pipeline API   │  Port: 8000                                     │   │
│  │  │   (FastAPI)     │  Depends on: Redis, PostgreSQL, MinIO, Qdrant   │   │
│  │  └────────┬────────┘                                                │   │
│  └───────────┼─────────────────────────────────────────────────────────┘   │
│              │                                                              │
│              ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Infrastructure Layer                             │   │
│  │  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐                 │   │
│  │  │  Redis  │ │PostgreSQL│ │  MinIO  │ │ Qdrant   │                 │   │
│  │  │ 6379    │ │  5433    │ │ 9000    │ │ 6333     │                 │   │
│  │  └─────────┘ └──────────┘ └─────────┘ └──────────┘                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Service Dependencies

Services start in this order (Docker Compose handles this):

```
Phase 1: Infrastructure (parallel)
├── Redis (healthcheck: redis-cli ping)
├── PostgreSQL (healthcheck: pg_isready)
├── MinIO (healthcheck: /minio/health/live)
└── Qdrant (healthcheck: /readyz)
         │
         ▼ (waits for all healthy)
Phase 2: Application
└── Pipeline API (healthcheck: /health)
         │
         ▼ (waits for healthy)
Phase 3: Presentation
└── Admin Dashboard (healthcheck: /admin/)
```

---

## What Changed (Band-aid vs Permanent Fix)

### Before (Band-aid Issues)

| Problem | Why It Failed |
|---------|---------------|
| Manual service startup | Easy to forget one service |
| No dependency ordering | Pipeline API started before PostgreSQL ready |
| No health checks | Services appeared "up" but weren't accepting traffic |
| Silent failures | No indication of which service failed |
| Frontend showed "DISCONNECTED" | Couldn't distinguish API down vs network issue |

### After (Permanent Fix)

| Solution | Implementation |
|----------|----------------|
| **One-command startup** | `make start` or `./scripts/start-frostbyte.sh` |
| **Dependency ordering** | Docker Compose `depends_on` with `condition: service_healthy` |
| **Health checks** | Every service has defined health endpoint |
| **Auto-restart** | `restart: unless-stopped` policy |
| **Better diagnostics** | Startup script verifies each service, shows actionable errors |

---

## Command Reference

### Daily Development

```bash
# Start everything
make start

# Check status
make status

# View logs
make logs              # All services
make logs-api          # Pipeline API only
make logs-dashboard    # Admin Dashboard only

# Stop everything
make stop

# Restart
make restart
```

### Troubleshooting

```bash
# Run diagnostics
make check

# Open shells
make shell-api         # Pipeline API container
make shell-db          # PostgreSQL
make shell-redis       # Redis CLI

# Reset everything (DANGER: loses data)
make reset
```

### Development Mode (Local Hot Reload)

```bash
# Start only infrastructure in Docker
make dev

# Then in another terminal, run API locally for hot reload
cd pipeline
uvicorn pipeline.main:app --reload --port 8000
```

---

## Health Check Endpoints

| Service | URL | Expected Response |
|---------|-----|-------------------|
| Pipeline API | http://localhost:8000/health | `{"status": "healthy"}` |
| Admin Dashboard | http://localhost:5174/admin/ | HTML page |
| MinIO | http://localhost:9000/minio/health/live | 200 OK |
| Qdrant | http://localhost:6333/readyz | 200 OK |
| PostgreSQL | Internal | `pg_isready` |
| Redis | Internal | `PING` → `PONG` |

---

## Environment Variables

Create a `.env` file in project root:

```bash
# Required for local development
FROSTBYTE_AUTH_BYPASS=true
FROSTBYTE_ADMIN_API_KEY=dev-key-change-in-production
JWT_SECRET=dev-secret-min-32-characters

# Optional: Override defaults
# POSTGRES_URL=postgresql+asyncpg://frostbyte:frostbyte@postgres:5432/frostbyte
# REDIS_URL=redis://redis:6379/0
# MINIO_ENDPOINT=http://minio:9000
```

---

## Common Issues

### "DISCONNECTED" Still Shows

1. **Check service status**: `make status`
2. **Check logs**: `make logs-api`
3. **Verify ports not in use**: `lsof -i :8000` or `lsof -i :5174`
4. **Restart**: `make restart`

### Port Already in Use

```bash
# Find what's using port 8000
lsof -i :8000

# Kill it or change port in docker-compose.yml
```

### Database Connection Issues

```bash
# Check PostgreSQL
make shell-db

# Inside container
psql -U frostbyte -d frostbyte -c "SELECT 1;"
```

### SSE Stream Not Working

```bash
# Test directly
curl -N http://localhost:8000/api/v1/pipeline/stream

# Should see: data: {"stage": "SYSTEM", ...}
```

---

## Production Deployment

For production:

1. **Set strong secrets**:
   ```bash
   FROSTBYTE_ADMIN_API_KEY=<random-64-char-string>
   JWT_SECRET=<random-64-char-string>
   FROSTBYTE_AUTH_BYPASS=false
   ```

2. **Use production build**:
   ```bash
   make prod
   ```

3. **Enable HTTPS** (via reverse proxy):
   - Use nginx or traefik in front
   - Terminate TLS at reverse proxy

4. **Monitoring**:
   - Health checks run every 10s
   - Unhealthy services auto-restart
   - Logs aggregated via `make logs`

---

## Files Reference

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Complete service orchestration |
| `Makefile` | Quick commands |
| `scripts/start-frostbyte.sh` | Intelligent startup with health checks |
| `scripts/check-pipeline-connection.sh` | Diagnostics |
| `pipeline/Dockerfile` | Pipeline API container |
| `packages/admin-dashboard/Dockerfile` | Admin Dashboard container |

---

## Migration from Old Setup

If you were running services manually:

```bash
# 1. Stop any manually running services
# (Ctrl+C in any terminals running uvicorn or npm)

# 2. Clean up (optional)
docker-compose down -v

# 3. Start new way
make start

# 4. Verify
make status
```

---

**Result**: Pipeline connection issues are now prevented by design, not caught by diagnostics.
