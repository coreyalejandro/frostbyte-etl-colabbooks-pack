# Frostbyte ETL — Quick Start

## One Command to Start Everything

```bash
make start
```

Wait 30 seconds, then open: **http://localhost:5174/admin/**

---

## Common Commands

| Command | What It Does |
|---------|--------------|
| `make start` | Start all services |
| `make stop` | Stop all services |
| `make status` | Check if everything is running |
| `make logs` | View all logs |
| `make restart` | Restart everything |

---

## URLs When Running

| Service | URL |
|---------|-----|
| Admin Dashboard | http://localhost:5174/admin/ |
| Pipeline API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |

---

## Troubleshooting

**Dashboard shows "DISCONNECTED"?**

```bash
make status    # Check what's running
make logs-api  # See API errors
make restart   # Try restarting
```

**Still not working?**

```bash
# Full reset (loses data)
make reset
make start
```

---

## Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Admin UI       │ ───→ │  Pipeline API   │ ───→ │  PostgreSQL     │
│  Port: 5174     │      │  Port: 8000     │      │  Port: 5433     │
└─────────────────┘      └────────┬────────┘      └─────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              ┌─────────┐   ┌─────────┐   ┌─────────┐
              │  Redis  │   │  MinIO  │   │ Qdrant  │
              │  6379   │   │  9000   │   │  6333   │
              └─────────┘   └─────────┘   └─────────┘
```

All services start automatically with `make start`.

---

## Files You Should Know

- `docker-compose.yml` — Service definitions
- `Makefile` — Quick commands
- `scripts/start-frostbyte.sh` — Startup script with health checks
- `docs/OPERATIONS.md` — Full operations guide
