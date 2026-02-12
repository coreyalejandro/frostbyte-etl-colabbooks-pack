# Docker Troubleshooting

## 500 Internal Server Error

**Symptom:** `docker compose up -d` or `docker pull` returns:

```
request returned 500 Internal Server Error for API route and version
http://.../v1.51/images/.../json, check if the server supports the requested API version
```

**Causes:**

- Docker Desktop/daemon is unhealthy or outdated
- API version mismatch between CLI and daemon

**Remediation:**

1. Restart Docker Desktop (full quit and reopen)
2. Update Docker Desktop to the latest version
3. Reset Docker to factory defaults (Docker Desktop → Settings → Reset)
4. If using Colima/Rancher Desktop, try `colima restart` or equivalent
5. Verify: `docker info` and `docker version` both succeed

## End-to-End Verification

Once Docker is healthy:

```bash
./scripts/verify_e2e.sh
```

Or manually per `BUILD_1HR.md`:

1. `docker compose up -d`
2. `./scripts/run_migrations.sh`
3. `cd pipeline && uvicorn pipeline.main:app --port 8000`
4. `curl -X POST http://localhost:8000/api/v1/intake -F "file=@/tmp/test.txt" -F "tenant_id=default"`
