# Frostbyte Auto-Start Guide

## Quick Start - Choose Your Method

### Method 1: VS Code (Recommended)

When you open VS Code, the Pipeline API will auto-start if not running.

Or press `Cmd+Shift+P` (Mac) / `Ctrl+Shift+P` (Windows) and type:

- "Tasks: Run Task" → "Start Pipeline API"

### Method 2: Terminal (One Command)

```bash
make pipeline
```

This checks infrastructure, retries on failure, and keeps logs.

### Method 3: Dashboard Auto-Start Button

If you see "DISCONNECTED" in the dashboard:

1. Click **"Auto-Start Pipeline"** button
2. Wait for it to turn green
3. Or click "Show manual instructions" for terminal commands

---

## What Auto-Start Does

```
┌─────────────────────────────────────────────────────────────┐
│                  Auto-Start Sequence                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Check Infrastructure                                    │
│     ├── Redis (port 6379)      ✓ or ✗ (show fix)            │
│     ├── PostgreSQL (5433)      ✓ or ✗ (show fix)            │
│     ├── MinIO (9000)           ✓ or ✗ (show fix)            │
│     └── Qdrant (6333)          ✓ or ✗ (show fix)            │
│                                                              │
│  2. Start Pipeline API                                      │
│     ├── Attempt 1...          (up to 5 retries)             │
│     ├── Wait for health...    (30s timeout)                 │
│     └── Verify SSE stream...                                │
│                                                              │
│  3. Monitor & Restart                                       │
│     └── Auto-reconnect on failure                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Available Commands

### Terminal

```bash
# Start with full diagnostics
make pipeline

# Silent auto-start (for scripts)
make pipeline-auto

# Stop
make pipeline-stop

# Restart
make pipeline-restart

# Check status
make pipeline-status

# View logs
make pipeline-logs

# Full diagnostic
./scripts/pipeline-manager.sh diagnose
```

### VS Code Tasks

Press `Cmd+Shift+P` / `Ctrl+Shift+P`:

| Task | What It Does |
|------|--------------|
| "Start Pipeline API" | Full start with retry |
| "Stop Pipeline API" | Stop cleanly |
| "Restart Pipeline API" | Stop + start |
| "Check Pipeline Status" | Show all services |
| "View Pipeline Logs" | Follow logs |
| "Start Infrastructure" | Docker services only |

---

## Troubleshooting

### "Port 8000 in use"

```bash
# Kill existing process
make pipeline-stop
# or
kill -9 $(lsof -t -i:8000)
```

### "Infrastructure not running"

```bash
# Start Docker services
docker-compose up -d
# or
make dev
```

### "Auto-start keeps failing"

```bash
# Check detailed diagnostics
./scripts/pipeline-manager.sh diagnose

# View logs
tail -f /tmp/frostbyte-pipeline.log
```

### "Still DISCONNECTED after starting"

1. Check: `curl http://localhost:8000/health`
2. Check firewall isn't blocking port 8000
3. Try refresh browser

---

## Files Reference

| File | Purpose |
|------|---------|
| `scripts/pipeline-manager.sh` | Main auto-start script with retry logic |
| `scripts/auto-start-http.sh` | HTTP endpoint for remote triggering |
| `.vscode/tasks.json` | VS Code task definitions |
| `Makefile` | Quick command shortcuts |
| `/tmp/frostbyte-pipeline.log` | Runtime logs |
| `/tmp/frostbyte-pipeline.pid` | Process ID file |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Machine                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐     ┌───────────────────────────────┐  │
│  │  VS Code /      │────→│  pipeline-manager.sh          │  │
│  │  Browser        │     │  • Infrastructure checks      │  │
│  │                 │     │  • Retry logic (5 attempts)   │  │
│  │  Auto-Start     │     │  • Health verification        │  │
│  │  Button         │     │  • Log rotation               │  │
│  └─────────────────┘     └───────────────┬───────────────┘  │
│                                          │                   │
│                                          ▼                   │
│                              ┌───────────────────┐           │
│                              │  Pipeline API     │           │
│                              │  Port: 8000       │           │
│                              └─────────┬─────────┘           │
│                                        │                     │
│                    ┌───────────────────┼───────────────────┐ │
│                    ▼                   ▼                   ▼ │
│              ┌─────────┐      ┌──────────┐      ┌─────────┐ │
│              │  Redis  │      │PostgreSQL│      │  MinIO  │ │
│              └─────────┘      └──────────┘      └─────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Success Indicators

| Indicator | Means |
|-----------|-------|
| 🟢 Green dot + "LIVE" | Pipeline connected |
| "Auto-Start Pipeline" button visible | Pipeline is down, click to fix |
| No error messages | Everything working |
| Logs flowing | Documents being processed |
