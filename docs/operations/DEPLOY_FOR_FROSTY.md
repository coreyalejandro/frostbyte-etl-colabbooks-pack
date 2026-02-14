# Deploy for Frosty — App + Onboarding Available

**Purpose:** Get the app live so Frosty (Mr. Frostbyte) can use it freely. All onboarding material and parts of the app must be available.

**Single source of truth:** [.planning/PROJECT.md](../../.planning/PROJECT.md)

---

## 1. Do we need Gradio?

**No.** You do not need to wrap a Gradio app around the “two command line” pieces. The app is:

1. **Pipeline API** (FastAPI) — intake, documents, health, tenants; run with `uvicorn pipeline.main:app`.
2. **Admin dashboard** (React + Vite in `packages/admin-dashboard`) — UI for tenants, documents, verify, control, audit.

The “command line” steps (Docker Compose + migrations, then start API) are for **running the backend**; Frosty will use the **deployed** API and dashboard in the browser. A Gradio wrapper would only add a minimal upload UI; the existing dashboard and API already provide the app. Use Gradio only if you explicitly want a one-page ML-demo style upload interface.

---

## 2. Where to deploy

### Vercel (your account) — frontend + onboarding

- **Admin dashboard:** Deploy the React app in `packages/admin-dashboard`. Build command: `npm run build`. Output: `dist`. Set **Root Directory** to `packages/admin-dashboard` (or deploy from that folder). Set env var **`VITE_API_URL`** to your deployed API URL (e.g. `https://your-app.railway.app`).
- **Onboarding material:** Must be available. Two options:
  - **Option A:** Add an **Onboard** page in the dashboard (already added) that lists links to all onboarding docs. Point those links to your GitHub repo’s `docs/` (e.g. `https://github.com/OWNER/REPO/blob/master/docs/team/ENGINEER_ONBOARDING.md`) or to a docs site URL. Set **`VITE_DOCS_BASE`** to the base URL for docs (e.g. `https://github.com/OWNER/REPO/blob/master`).
  - **Option B:** Deploy a second Vercel project (e.g. Next.js or static) that serves the markdown from `docs/` so onboarding is at e.g. `https://frostbyte-docs.vercel.app`. Then set `VITE_DOCS_BASE=https://frostbyte-docs.vercel.app` in the dashboard.

### Backend (API + Postgres, MinIO, Redis, Qdrant)

Vercel cannot run the FastAPI app and its stateful services. Deploy the **API + databases** elsewhere:

- **Railway** — Good fit: Postgres, Redis, optional MinIO-style storage; run the FastAPI app as a service. Add Qdrant via Docker or [Qdrant Cloud](https://qdrant.cloud/). Railway gives you a public URL; use that as `VITE_API_URL` in the dashboard.
- **Render** — Web Service for the API; managed Postgres and Redis; external Qdrant.
- **Fly.io** — Run Docker Compose–style stack (API + Postgres, Redis, MinIO, Qdrant) in one app.
- **Hetzner** — Full control per [DEPLOYMENT_ARCHITECTURE.md](../architecture/DEPLOYMENT_ARCHITECTURE.md); more setup.

**Recommendation:** Use **Vercel for the dashboard (and optionally a docs site)** and **Railway (or Render) for the API + Postgres/Redis**; add Qdrant and MinIO or equivalents as needed.

---

## 3. What must be available

| Item | Where |
|------|--------|
| **App (UI)** | Admin dashboard on Vercel at e.g. `https://frostbyte-admin.vercel.app/admin` |
| **App (API)** | Pipeline API on Railway/Render at e.g. `https://frostbyte-api.railway.app` |
| **Onboarding material** | Linked from dashboard **Onboard** page; targets GitHub `docs/` or a deployed docs site (see above) |
| **Single source of truth** | `.planning/PROJECT.md` in repo; linked from README and dashboard |
| **Build runbook** | `BUILD_1HR.md` in repo; linked from README |

---

## 4. Vercel: deploy the dashboard

1. In Vercel, **Add New Project** → Import your Git repo.
2. Set **Root Directory** to `packages/admin-dashboard`.
3. **Build Command:** `npm run build` (default for Vite).
4. **Output Directory:** `dist`.
5. **Environment variables:**
   - `VITE_API_URL` = `https://your-api.railway.app` (or your backend URL; no trailing slash).
   - `VITE_DOCS_BASE` = `https://github.com/YOUR_ORG/frostbyte_etl_colabbooks_pack_2026-02-07/blob/master` (or your docs site base URL).
6. Deploy. The app will be at `https://your-project.vercel.app/admin` (because of `base: '/admin/'` in `vite.config.ts`).

---

## 5. Backend: deploy the API (e.g. Railway)

1. Create a Railway project; add **PostgreSQL** and **Redis** from the catalog.
2. Add a **Service** for the FastAPI app: connect the repo, set **Root Directory** to repo root (or `pipeline` if you only deploy that).
3. **Build:** e.g. `pip install -e pipeline` or `cd pipeline && pip install -e .`
4. **Start:** e.g. `uvicorn pipeline.main:app --host 0.0.0.0 --port $PORT`
5. **Env vars:** `FROSTBYTE_CONTROL_DB_URL` (from Railway Postgres), `FROSTBYTE_REDIS_URL` (from Railway Redis), `FROSTBYTE_AUTH_BYPASS=0` in production (use JWT or API key). For MinIO and Qdrant use Railway add-ons or external services and set the corresponding env vars.
6. Deploy; copy the public URL into `VITE_API_URL` in Vercel.

---

## 6. Checklist before handing the link to Frosty

- [ ] Dashboard deployed on Vercel; `VITE_API_URL` points to live API.
- [ ] API deployed (Railway/Render); health check returns 200 at `/health`.
- [ ] Onboard page in dashboard lists all onboarding docs and links work (`VITE_DOCS_BASE` or GitHub links).
- [ ] README and BUILD_1HR.md in repo point to `.planning/PROJECT.md` as single source of truth.
- [ ] Frosty has the dashboard URL (e.g. `https://frostbyte-admin.vercel.app/admin`) and any login credentials (API key / JWT as per your auth setup).
