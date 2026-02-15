# Dashboard Completion Design
**Date:** 2026-02-15
**Status:** Approved
**Reference:** FROSTBYTE_ETL_DASHBOARD_ENTERPRISE_COMPLETE.md

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend API | Mock all endpoints | Backend is a skeleton; mocking gets a demonstrable product fastest |
| Pipeline DAG | React Flow (@xyflow/react) | Spec requires Manhattan routing + interactive nodes |
| Real-time updates | Simulated WebSocket service | No backend to connect to; mock mirrors Socket.IO interface for easy swap |
| Testing | After features | Avoids context exhaustion; tests easier once API surface is stable |

---

## Phase 1: Mock API Layer

Expand `src/api/client.ts` with all missing spec endpoints backed by mock data.

**New files:**
- `src/api/mockData.ts` - Centralized mock responses, separate from Zustand store data
- `src/components/MockBanner.tsx` - `[MOCK]` indicator when `VITE_MOCK_API=true`

**New endpoints:**

| Endpoint | Returns |
|----------|---------|
| `GET /api/v1/pipeline/status` | Pipeline mode, throughput, node statuses |
| `GET /api/v1/tenants` | Paginated tenant list |
| `GET /api/v1/tenants/:id` | Single tenant with stats |
| `GET /api/v1/documents` | Paginated documents with filters |
| `GET /api/v1/documents/:id/chain` | Chain of custody for Inspector |
| `POST /api/v1/verification/test` | Verification test results |
| `PATCH /api/v1/config` | Config update acknowledgment |

**Pattern:** API client checks `VITE_MOCK_API`. If true, returns mock data with configurable delay. If false, hits real API. Swap is trivial later.

---

## Phase 2: Error Handling & Resilience

**Global Error Boundary** (`src/components/ErrorBoundary.tsx`):
- Catches unhandled React errors
- Metal dark theme error panel
- Stack trace in dev mode, "Reload" button

**`useApi` hook** (`src/hooks/useApi.ts`):
- Wraps TanStack Query with standardized error handling
- 3 retries, exponential backoff
- Returns `{ data, error, isLoading, isOffline }`
- On network failure, sets global `isOffline` state

**Offline Indicator** (Header.tsx):
- Watches `navigator.onLine` + failed API responses
- `OFFLINE` badge (red) / `ONLINE` (muted)

**Component-level errors:**

| Component | Scenario | Behavior |
|-----------|----------|----------|
| Inspector | Document 404 | `DOCUMENT NOT FOUND` inside modal |
| PipelineControlPanel | `[COMMIT]` failure | Button shows `[FAILED]` 3s + inline error |
| PipelineControlPanel | Batch size invalid | Revert to last valid, show `(1-256)` warning |

---

## Phase 3: React Flow Pipeline DAG

Replace `PipelineSchematic.tsx` with React Flow interactive DAG.

**Dependency:** `@xyflow/react`

**Nodes:**
- 7 stages: INTAKE, PARSE, EVIDENCE, EMBED, VECTOR, METADATA, VERIFY
- Custom node: `bg-surface`, `border-border`, `font-mono`
- Status indicators: amber pulse (active), green (healthy), red (error), gray (idle)
- Throughput count per node
- Not draggable (fixed layout)

**Edges:**
- Manhattan routing via `smoothStep` edge type, border radius 0
- Default: `border` color (muted gray)
- Active: `accent` amber, animated dash
- Labels: docs/sec when active

**Layout:**
- Horizontal left-to-right, fixed positions
- Fit-view on mount, zoom/pan enabled

**Integration:**
- Reads from `pipelineStore` (node status + throughput)
- WebSocket simulation drives real-time updates (Phase 5)
- Click node opens Inspector modal

**Files:**
- `src/components/pipeline/PipelineDAG.tsx` - React Flow canvas
- `src/components/pipeline/PipelineNode.tsx` - Custom node
- `src/components/pipeline/PipelineEdge.tsx` - Custom animated edge
- `src/components/pipeline/pipelineLayout.ts` - Positions + edge definitions

---

## Phase 4: Focused Tenant View

**New route:** `/tenants/:id/detail`

**Top section - Tenant Header:**
- Name, ID, status (ACTIVE/INACTIVE)
- Stats: document count, vector count, verification score
- Schema info from `getTenantSchema`

**Bottom section - Isolated Pipeline DAG:**
- Reuses `PipelineDAG` from Phase 3, scoped to tenant data
- Surrounded by dashed border (`border-dashed border-border`)
- Label: `NETWORK ISOLATION BOUNDARY`

**Navigation:**
- `TenantChambers.tsx` cards link to `/tenants/:id/detail`
- Back button returns to `/tenants`

**Error:** Tenant not found shows `TENANT NOT FOUND` (Phase 2 handling)

**Files:**
- `src/pages/TenantDetailView.tsx`
- Route addition in `App.tsx`
- `TenantChambers.tsx` edit for navigation

---

## Phase 5: Simulated WebSocket Service

**Mock service:** `src/services/mockWebSocket.ts`

```
MockPipelineSocket
  connect()     - starts emitting events on intervals
  disconnect()  - stops intervals, cleans up
  on(event, cb) - registers event listeners
  isConnected   - boolean status
```

**Events:**

| Event | Interval | Effect |
|-------|----------|--------|
| `pipeline:throughput` | 2s | Random throughput per node (+-15% jitter) |
| `pipeline:node-status` | 5s | Occasionally flip node to processing/healthy |
| `pipeline:document-progress` | 3s | Move mock document through stages |

**Hook:** `src/hooks/useWebSocket.ts`
- Instantiates mock socket on mount, disconnects on unmount
- Pushes events into `pipelineStore`
- Exposes `{ isConnected, disconnect, reconnect }`

**Header:** `WS CONNECTED` (green-400) / `WS DISCONNECTED` (red-400)

**Consumers:** PipelineDAG nodes animate, DocumentQueue rows update status

**Why not real Socket.IO:** No backend, unnecessary dependency. Mock mirrors the interface for easy swap later.

---

## Phase 6: Auth Improvements

**Token refresh** (`src/hooks/useTokenRefresh.ts`):
- Reads mock JWT expiry (default 30-min TTL)
- Timer refreshes 5 min before expiry
- Mock mode generates new token, updates AuthContext
- Simulated 5% failure rate calls `logout()`

**Session expiry UX** (`src/components/SessionWarning.tsx`):
- Toast notification: `SESSION EXPIRES IN 5:00` (countdown)
- Top-right, metal dark theme, dismissible
- On expiry, redirect to login

**Not included:** No RBAC, no JWT validation, no OIDC (separate enhancement E07)

---

## Out of Scope

- Performance budget measurement (needs production build)
- CSP headers (deployment config)
- CI workflow (needs test suite)
- Actual backend endpoint implementation
- E2E / unit tests (follow-up session)
