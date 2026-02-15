# Dashboard Completion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the Frostbyte ETL Admin Dashboard by implementing mock API endpoints, error handling, React Flow DAG, focused tenant view, simulated WebSocket, and auth improvements.

**Architecture:** Expand the existing React+TypeScript+Tailwind dashboard at `packages/admin-dashboard/`. Add a mock API layer that intercepts all API calls when `VITE_MOCK_API=true`, install `@xyflow/react` for the pipeline DAG, and create a simulated WebSocket service for real-time updates. All new code follows the existing metal dark theme (no pastels, no gradients, no rounded corners).

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS, Zustand, TanStack React Query, @xyflow/react, Immer

---

## Task 1: Install React Flow dependency

**Files:**
- Modify: `packages/admin-dashboard/package.json`

**Step 1: Install @xyflow/react**

Run:
```bash
cd packages/admin-dashboard && npm install @xyflow/react
```

Expected: package.json updated with `@xyflow/react` in dependencies

**Step 2: Verify build still works**

Run:
```bash
cd packages/admin-dashboard && npx tsc --noEmit
```

Expected: No type errors

**Step 3: Commit**

```bash
git add packages/admin-dashboard/package.json packages/admin-dashboard/package-lock.json
git commit -m "chore: add @xyflow/react dependency for pipeline DAG"
```

---

## Task 2: Create mock data module

**Files:**
- Create: `packages/admin-dashboard/src/api/mockData.ts`

**Step 1: Create the mock data file**

This file centralizes all mock API responses. It must NOT import from Zustand stores (separate concerns).

```typescript
import type { DocumentMetadata } from './client'

export interface PipelineStatus {
  mode: 'ONLINE' | 'OFFLINE' | 'HYBRID'
  model: string
  batchSize: number
  online: boolean
  throughput: number
  nodes: Array<{
    id: string
    label: string
    status: 'healthy' | 'processing' | 'error' | 'idle'
    throughput: number
  }>
}

export interface TenantSummary {
  id: string
  name: string
  active: boolean
  documentCount: number
  vectorCount: string
  verificationScore: number
}

export interface PaginatedResponse<T> {
  data: T[]
  meta: { total: number; page: number; limit: number }
}

export interface ChainOfCustodyStep {
  timestamp: string
  operation: string
  operator: string
  fingerprint: string
  verified: boolean
}

export interface VerificationResult {
  gate: string
  result: 'PASS' | 'FAIL'
  score: number
  details: string
  timestamp: string
}

export const MOCK_PIPELINE_STATUS: PipelineStatus = {
  mode: 'ONLINE',
  model: 'NOMIC',
  batchSize: 32,
  online: true,
  throughput: 142,
  nodes: [
    { id: 'intake', label: 'INTAKE', status: 'healthy', throughput: 142 },
    { id: 'parse', label: 'PARSE', status: 'healthy', throughput: 138 },
    { id: 'evidence', label: 'EVIDENCE', status: 'processing', throughput: 124 },
    { id: 'embed', label: 'EMBED', status: 'healthy', throughput: 120 },
    { id: 'vector', label: 'VECTOR', status: 'healthy', throughput: 118 },
    { id: 'metadata', label: 'METADATA', status: 'healthy', throughput: 118 },
    { id: 'verify', label: 'VERIFY', status: 'healthy', throughput: 115 },
  ],
}

export const MOCK_TENANTS: TenantSummary[] = [
  { id: 'PROD-01', name: 'Production Alpha', active: true, documentCount: 1247, vectorCount: '48.2K', verificationScore: 0.98 },
  { id: 'PROD-02', name: 'Production Beta', active: true, documentCount: 892, vectorCount: '32.1K', verificationScore: 0.97 },
  { id: 'PROD-03', name: 'Staging Gamma', active: false, documentCount: 0, vectorCount: '0', verificationScore: 0 },
]

export const MOCK_DOCUMENTS: DocumentMetadata[] = [
  { id: '0001', tenant_id: 'PROD-01', filename: 'contract.pdf', status: 'STORED', created_at: '2026-02-12T14:03:22Z' },
  { id: '0002', tenant_id: 'PROD-01', filename: 'appendix.md', status: 'PARSING', created_at: '2026-02-12T14:02:18Z' },
  { id: '0003', tenant_id: 'PROD-01', filename: 'policy.docx', status: 'FAILED', created_at: '2026-02-12T14:01:55Z' },
  { id: '0004', tenant_id: 'PROD-02', filename: 'invoice-batch.csv', status: 'STORED', created_at: '2026-02-11T09:15:00Z' },
  { id: '0005', tenant_id: 'PROD-02', filename: 'compliance-report.pdf', status: 'VERIFY', created_at: '2026-02-11T10:30:00Z' },
]

export const MOCK_CHAIN_OF_CUSTODY: Record<string, ChainOfCustodyStep[]> = {
  '0001': [
    { timestamp: '2026-02-12 14:03:22', operation: 'UPLOAD', operator: 'system', fingerprint: 'a1b2c3d4', verified: true },
    { timestamp: '2026-02-12 14:03:25', operation: 'PARSE', operator: 'docling-2.7.0', fingerprint: 'e5f6g7h8', verified: true },
    { timestamp: '2026-02-12 14:03:28', operation: 'EVIDENCE_PACK', operator: 'system', fingerprint: 'i9j0k1l2', verified: true },
    { timestamp: '2026-02-12 14:03:31', operation: 'EMBED', operator: 'nomic-v1.5', fingerprint: 'm3n4o5p6', verified: true },
    { timestamp: '2026-02-12 14:03:35', operation: 'STORE', operator: 'pgvector', fingerprint: 'q7r8s9t0', verified: true },
  ],
  '0002': [
    { timestamp: '2026-02-12 14:02:18', operation: 'UPLOAD', operator: 'system', fingerprint: 'u1v2w3x4', verified: true },
    { timestamp: '2026-02-12 14:02:20', operation: 'PARSE', operator: 'docling-2.7.0', fingerprint: 'y5z6a7b8', verified: false },
  ],
  '0003': [
    { timestamp: '2026-02-12 14:01:55', operation: 'UPLOAD', operator: 'system', fingerprint: 'c9d0e1f2', verified: true },
    { timestamp: '2026-02-12 14:01:58', operation: 'PARSE', operator: 'docling-2.7.0', fingerprint: 'g3h4i5j6', verified: false },
  ],
}

export const MOCK_VERIFICATION_RESULTS: VerificationResult[] = [
  { gate: 'EVIDENCE PACKAGING', result: 'PASS', score: 0.98, details: 'All slices signed and verified', timestamp: '2026-02-12 14:03:28' },
  { gate: 'RETRIEVAL QUALITY', result: 'PASS', score: 0.94, details: 'Recall 0.94, Grounding 0.98', timestamp: '2026-02-12 14:03:32' },
  { gate: 'SECURITY AUDIT', result: 'PASS', score: 0.91, details: 'No injection vectors detected', timestamp: '2026-02-12 14:03:35' },
]

export function delay(ms: number = 200): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
```

**Step 2: Commit**

```bash
git add packages/admin-dashboard/src/api/mockData.ts
git commit -m "feat: add centralized mock data module for API simulation"
```

---

## Task 3: Expand API client with mock support

**Files:**
- Modify: `packages/admin-dashboard/src/api/client.ts`

**Step 1: Rewrite the API client**

Replace the entire file. The new version checks `VITE_MOCK_API` env var. When true, returns mock data. When false, calls real API.

```typescript
import {
  MOCK_PIPELINE_STATUS,
  MOCK_TENANTS,
  MOCK_DOCUMENTS,
  MOCK_CHAIN_OF_CUSTODY,
  MOCK_VERIFICATION_RESULTS,
  delay,
  type PipelineStatus,
  type TenantSummary,
  type PaginatedResponse,
  type ChainOfCustodyStep,
  type VerificationResult,
} from './mockData'

const API_BASE = import.meta.env.VITE_API_URL || ''
const IS_MOCK = import.meta.env.VITE_MOCK_API === 'true'

let authToken: string | null = null

export function setAuthToken(token: string | null) {
  authToken = token
}

export function getAuthToken(): string | null {
  return authToken
}

export function isMockMode(): boolean {
  return IS_MOCK
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  }
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }
  const res = await fetch(url, { ...options, headers })
  if (!res.ok) {
    const error = new Error(`API error ${res.status}: ${res.statusText}`) as Error & { status: number }
    error.status = res.status
    throw error
  }
  return res.json() as Promise<T>
}

export interface Health {
  status: string
  timestamp: string
}

export interface DocumentMetadata {
  id: string
  tenant_id?: string
  filename?: string
  status?: string
  modality?: string
  bucket?: string
  object_key?: string
  created_at?: string
}

export async function login(apiKey: string): Promise<{ access_token: string }> {
  if (IS_MOCK) {
    await delay(300)
    if (apiKey === 'invalid') {
      throw new Error('Invalid API key')
    }
    return { access_token: `mock-token-${Date.now()}` }
  }
  const base = API_BASE || ''
  const url = base ? `${base}/api/v1/auth/token` : '/api/v1/auth/token'
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: { message?: string } })?.detail?.message || `Login failed: ${res.status}`)
  }
  return res.json()
}

export const api = {
  health: async (): Promise<Health> => {
    if (IS_MOCK) {
      await delay()
      return { status: 'healthy', timestamp: new Date().toISOString() }
    }
    return fetchApi<Health>('/health')
  },

  getPipelineStatus: async (): Promise<PipelineStatus> => {
    if (IS_MOCK) {
      await delay()
      return { ...MOCK_PIPELINE_STATUS }
    }
    return fetchApi<PipelineStatus>('/api/v1/pipeline/status')
  },

  getTenants: async (page = 1, limit = 20): Promise<PaginatedResponse<TenantSummary>> => {
    if (IS_MOCK) {
      await delay()
      return {
        data: MOCK_TENANTS,
        meta: { total: MOCK_TENANTS.length, page, limit },
      }
    }
    return fetchApi<PaginatedResponse<TenantSummary>>(`/api/v1/tenants?page=${page}&limit=${limit}`)
  },

  getTenant: async (id: string): Promise<TenantSummary> => {
    if (IS_MOCK) {
      await delay()
      const tenant = MOCK_TENANTS.find((t) => t.id === id)
      if (!tenant) {
        const error = new Error('Tenant not found') as Error & { status: number }
        error.status = 404
        throw error
      }
      return { ...tenant }
    }
    return fetchApi<TenantSummary>(`/api/v1/tenants/${id}`)
  },

  getDocuments: async (page = 1, limit = 20, tenantId?: string): Promise<PaginatedResponse<DocumentMetadata>> => {
    if (IS_MOCK) {
      await delay()
      const filtered = tenantId
        ? MOCK_DOCUMENTS.filter((d) => d.tenant_id === tenantId)
        : MOCK_DOCUMENTS
      return {
        data: filtered,
        meta: { total: filtered.length, page, limit },
      }
    }
    const params = new URLSearchParams({ page: String(page), limit: String(limit) })
    if (tenantId) params.set('tenant_id', tenantId)
    return fetchApi<PaginatedResponse<DocumentMetadata>>(`/api/v1/documents?${params}`)
  },

  getDocument: async (id: string): Promise<DocumentMetadata> => {
    if (IS_MOCK) {
      await delay()
      const doc = MOCK_DOCUMENTS.find((d) => d.id === id)
      if (!doc) {
        const error = new Error('Document not found') as Error & { status: number }
        error.status = 404
        throw error
      }
      return { ...doc }
    }
    return fetchApi<DocumentMetadata>(`/api/v1/documents/${id}`)
  },

  getDocumentChain: async (id: string): Promise<ChainOfCustodyStep[]> => {
    if (IS_MOCK) {
      await delay()
      const chain = MOCK_CHAIN_OF_CUSTODY[id]
      if (!chain) {
        const error = new Error('Document not found') as Error & { status: number }
        error.status = 404
        throw error
      }
      return [...chain]
    }
    return fetchApi<ChainOfCustodyStep[]>(`/api/v1/documents/${id}/chain`)
  },

  runVerification: async (testType: string): Promise<VerificationResult[]> => {
    if (IS_MOCK) {
      await delay(500)
      return MOCK_VERIFICATION_RESULTS.map((r) => ({ ...r }))
    }
    return fetchApi<VerificationResult[]>('/api/v1/verification/test', {
      method: 'POST',
      body: JSON.stringify({ test_type: testType }),
    })
  },

  updateConfig: async (config: Record<string, unknown>): Promise<{ acknowledged: boolean }> => {
    if (IS_MOCK) {
      await delay(300)
      return { acknowledged: true }
    }
    return fetchApi<{ acknowledged: boolean }>('/api/v1/config', {
      method: 'PATCH',
      body: JSON.stringify(config),
    })
  },

  getTenantSchema: async (tenantId: string) => {
    if (IS_MOCK) {
      await delay()
      return {
        document_fields: { filename: 'string', status: 'string', created_at: 'datetime' },
        chunk_fields: { content: 'text', embedding: 'vector', chunk_id: 'string' },
      }
    }
    return fetchApi<{ document_fields: Record<string, unknown>; chunk_fields: Record<string, unknown> }>(
      `/tenants/${tenantId}/schema`,
    )
  },
}
```

**Step 2: Add `VITE_MOCK_API=true` to .env**

Modify: `packages/admin-dashboard/.env`

Append `VITE_MOCK_API=true` to the env file.

**Step 3: Verify build**

Run:
```bash
cd packages/admin-dashboard && npx tsc --noEmit
```

Expected: No type errors

**Step 4: Commit**

```bash
git add packages/admin-dashboard/src/api/client.ts packages/admin-dashboard/.env
git commit -m "feat: expand API client with mock mode for all spec endpoints"
```

---

## Task 4: Create MockBanner component

**Files:**
- Create: `packages/admin-dashboard/src/components/MockBanner.tsx`

**Step 1: Create the component**

```typescript
import { isMockMode } from '../api/client'

export default function MockBanner() {
  if (!isMockMode()) return null

  return (
    <div className="bg-surface-elevated border-b border-border px-4 py-1 text-center">
      <span className="text-xs font-medium uppercase tracking-wider text-accent">
        [MOCK] API SIMULATION ACTIVE
      </span>
    </div>
  )
}
```

**Step 2: Add to Layout**

Modify: `packages/admin-dashboard/src/components/Layout.tsx`

Import `MockBanner` and render it above the Header.

**Step 3: Commit**

```bash
git add packages/admin-dashboard/src/components/MockBanner.tsx packages/admin-dashboard/src/components/Layout.tsx
git commit -m "feat: add [MOCK] banner indicator for API simulation mode"
```

---

## Task 5: Create ErrorBoundary component

**Files:**
- Create: `packages/admin-dashboard/src/components/ErrorBoundary.tsx`

**Step 1: Create the error boundary**

```typescript
import { Component, type ReactNode, type ErrorInfo } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-base flex items-center justify-center p-8">
          <div className="bg-surface border border-border p-8 max-w-lg w-full">
            <h1 className="text-sm font-medium uppercase tracking-wider text-red-400 mb-4">
              SYSTEM ERROR
            </h1>
            <p className="text-text-primary font-mono text-sm mb-4">
              {this.state.error?.message ?? 'An unexpected error occurred'}
            </p>
            {import.meta.env.DEV && this.state.error?.stack && (
              <pre className="text-xs text-text-tertiary font-mono overflow-auto max-h-48 mb-4 p-2 bg-base border border-border">
                {this.state.error.stack}
              </pre>
            )}
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 border border-border bg-interactive text-text-primary text-xs font-medium uppercase tracking-wider hover:bg-surface"
            >
              [RELOAD]
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
```

**Step 2: Wrap App in ErrorBoundary**

Modify: `packages/admin-dashboard/src/App.tsx`

Import `ErrorBoundary` and wrap the entire `QueryClientProvider` with it.

**Step 3: Commit**

```bash
git add packages/admin-dashboard/src/components/ErrorBoundary.tsx packages/admin-dashboard/src/App.tsx
git commit -m "feat: add global ErrorBoundary with metal dark theme"
```

---

## Task 6: Create useApi hook and offline detection

**Files:**
- Create: `packages/admin-dashboard/src/hooks/useApi.ts`
- Create: `packages/admin-dashboard/src/stores/networkStore.ts`

**Step 1: Create the network store**

```typescript
import { create } from 'zustand'

interface NetworkState {
  isOffline: boolean
  setOffline: (offline: boolean) => void
}

export const useNetworkStore = create<NetworkState>()((set) => ({
  isOffline: typeof navigator !== 'undefined' ? !navigator.onLine : false,
  setOffline: (offline) => set({ isOffline: offline }),
}))

if (typeof window !== 'undefined') {
  window.addEventListener('online', () => useNetworkStore.getState().setOffline(false))
  window.addEventListener('offline', () => useNetworkStore.getState().setOffline(true))
}
```

**Step 2: Create the useApi hook**

```typescript
import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { useNetworkStore } from '../stores/networkStore'

export function useApi<T>(
  queryKey: string[],
  queryFn: () => Promise<T>,
  options?: Omit<UseQueryOptions<T, Error>, 'queryKey' | 'queryFn'>,
) {
  const { isOffline, setOffline } = useNetworkStore()

  const query = useQuery<T, Error>({
    queryKey,
    queryFn: async () => {
      try {
        const result = await queryFn()
        if (isOffline) setOffline(false)
        return result
      } catch (error) {
        if (error instanceof TypeError && error.message.includes('fetch')) {
          setOffline(true)
        }
        throw error
      }
    },
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    enabled: !isOffline,
    ...options,
  })

  return {
    ...query,
    isOffline,
  }
}
```

**Step 3: Update Header with offline indicator**

Modify: `packages/admin-dashboard/src/components/Header.tsx`

Import `useNetworkStore` and add an offline/online indicator next to the pipeline status dot:

```typescript
const { isOffline } = useNetworkStore()
```

Add after the pipeline status span:
```tsx
<span className={`text-xs font-medium uppercase tracking-wider ${isOffline ? 'text-red-400' : 'text-text-tertiary'}`}>
  {isOffline ? 'OFFLINE' : 'ONLINE'}
</span>
```

**Step 4: Commit**

```bash
git add packages/admin-dashboard/src/hooks/useApi.ts packages/admin-dashboard/src/stores/networkStore.ts packages/admin-dashboard/src/components/Header.tsx
git commit -m "feat: add useApi hook with retry logic and offline detection"
```

---

## Task 7: Add error handling to PipelineControlPanel

**Files:**
- Modify: `packages/admin-dashboard/src/features/control/PipelineControlPanel.tsx`

**Step 1: Add commit error handling and batch validation**

Import `useState` from React and `api` from the client. Update the `[COMMIT]` button to:
- Call `api.updateConfig()` on click
- Show `[COMMITTING...]` while in progress
- Show `[FAILED]` for 3 seconds on error with inline error text
- Show `[COMMITTED]` for 2 seconds on success

Add batch size validation:
- On blur, if value is outside 1-256, revert to last valid value
- Show inline warning text `VALID RANGE: 1-256` when invalid input detected

**Step 2: Commit**

```bash
git add packages/admin-dashboard/src/features/control/PipelineControlPanel.tsx
git commit -m "feat: add error handling for config commit and batch validation"
```

---

## Task 8: Create React Flow pipeline layout

**Files:**
- Create: `packages/admin-dashboard/src/components/pipeline/pipelineLayout.ts`

**Step 1: Define node positions and edge connections**

```typescript
import type { Node, Edge } from '@xyflow/react'

export interface PipelineNodeData {
  label: string
  description: string
  status: 'healthy' | 'processing' | 'error' | 'idle'
  throughput: number
  model?: { name: string; version: string }
}

const NODE_WIDTH = 140
const NODE_HEIGHT = 80
const NODE_GAP = 60

const STAGE_MODELS: Record<string, { name: string; version: string }> = {
  parse: { name: 'docling', version: '2.7.0' },
  embed: { name: 'nomic-embed-text-v1', version: '1.5.0' },
  verify: { name: 'policy-classifier', version: '1.2.3' },
}

export const PIPELINE_STAGES = [
  { id: 'intake', label: 'INTAKE', description: 'upload' },
  { id: 'parse', label: 'PARSE', description: 'extract text' },
  { id: 'evidence', label: 'EVIDENCE', description: 'verify' },
  { id: 'embed', label: 'EMBED', description: 'vectorize' },
  { id: 'vector', label: 'VECTOR', description: 'store' },
  { id: 'metadata', label: 'METADATA', description: 'index' },
  { id: 'verify', label: 'VERIFY', description: 'validate' },
] as const

export function createPipelineNodes(
  nodeStatuses?: Record<string, { status: string; throughput: number }>,
): Node<PipelineNodeData>[] {
  return PIPELINE_STAGES.map((stage, i) => ({
    id: stage.id,
    type: 'pipelineNode',
    position: { x: i * (NODE_WIDTH + NODE_GAP), y: 0 },
    draggable: false,
    data: {
      label: stage.label,
      description: stage.description,
      status: (nodeStatuses?.[stage.id]?.status as PipelineNodeData['status']) ?? 'healthy',
      throughput: nodeStatuses?.[stage.id]?.throughput ?? 0,
      model: STAGE_MODELS[stage.id],
    },
  }))
}

export function createPipelineEdges(activeNodeIds?: Set<string>): Edge[] {
  return PIPELINE_STAGES.slice(0, -1).map((stage, i) => {
    const nextStage = PIPELINE_STAGES[i + 1]
    const isActive = activeNodeIds?.has(stage.id) ?? true
    return {
      id: `${stage.id}-${nextStage.id}`,
      source: stage.id,
      target: nextStage.id,
      type: 'pipelineEdge',
      data: { active: isActive },
    }
  })
}
```

**Step 2: Commit**

```bash
git add packages/admin-dashboard/src/components/pipeline/pipelineLayout.ts
git commit -m "feat: add pipeline DAG layout configuration"
```

---

## Task 9: Create PipelineNode custom component

**Files:**
- Create: `packages/admin-dashboard/src/components/pipeline/PipelineNode.tsx`

**Step 1: Create the custom node**

```typescript
import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { PipelineNodeData } from './pipelineLayout'

const STATUS_STYLES: Record<string, string> = {
  healthy: 'bg-green-400',
  processing: 'bg-accent animate-pulse',
  error: 'bg-red-400',
  idle: 'bg-inactive',
}

function PipelineNodeComponent({ data }: NodeProps) {
  const nodeData = data as unknown as PipelineNodeData
  const statusClass = STATUS_STYLES[nodeData.status] ?? STATUS_STYLES.idle

  return (
    <>
      <Handle type="target" position={Position.Left} className="!bg-border !border-0 !w-2 !h-2" />
      <div className="bg-surface border border-border px-3 py-2 min-w-[8.5rem] font-mono select-none">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium uppercase tracking-wider text-text-primary">
            [{nodeData.label}]
          </span>
          <span className={`w-2 h-2 ${statusClass}`} title={nodeData.status} />
        </div>
        <span className="text-[10px] text-text-tertiary lowercase tracking-wide block">
          {nodeData.description}
        </span>
        {nodeData.throughput > 0 && (
          <span className="text-[10px] text-accent mt-1 block">
            {nodeData.throughput} docs/s
          </span>
        )}
        {nodeData.model && (
          <span className="text-[9px] text-text-tertiary mt-1 block">
            {nodeData.model.name}
          </span>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-border !border-0 !w-2 !h-2" />
    </>
  )
}

export default memo(PipelineNodeComponent)
```

**Step 2: Commit**

```bash
git add packages/admin-dashboard/src/components/pipeline/PipelineNode.tsx
git commit -m "feat: add custom PipelineNode component for React Flow DAG"
```

---

## Task 10: Create PipelineEdge custom component

**Files:**
- Create: `packages/admin-dashboard/src/components/pipeline/PipelineEdge.tsx`

**Step 1: Create the animated edge**

```typescript
import { memo } from 'react'
import { getSmoothStepPath, type EdgeProps } from '@xyflow/react'

function PipelineEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps) {
  const isActive = (data as { active?: boolean })?.active ?? false

  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 0,
  })

  return (
    <>
      <path
        id={id}
        d={edgePath}
        fill="none"
        stroke={isActive ? '#fbbf24' : '#3c4045'}
        strokeWidth={isActive ? 2 : 1}
        strokeDasharray={isActive ? '8 4' : 'none'}
        className={isActive ? 'animate-dash' : ''}
      />
    </>
  )
}

export default memo(PipelineEdgeComponent)
```

**Step 2: Add dash animation to tailwind config**

Modify: `packages/admin-dashboard/tailwind.config.js`

Add to `theme.extend`:
```javascript
keyframes: {
  dash: {
    to: { strokeDashoffset: '-24' },
  },
},
animation: {
  dash: 'dash 1s linear infinite',
},
```

**Step 3: Commit**

```bash
git add packages/admin-dashboard/src/components/pipeline/PipelineEdge.tsx packages/admin-dashboard/tailwind.config.js
git commit -m "feat: add animated PipelineEdge component with Manhattan routing"
```

---

## Task 11: Create PipelineDAG main component

**Files:**
- Create: `packages/admin-dashboard/src/components/pipeline/PipelineDAG.tsx`

**Step 1: Create the React Flow canvas**

```typescript
import { useCallback, useMemo, useState } from 'react'
import { ReactFlow, Background, type NodeMouseHandler } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { usePipelineStore } from '../../stores/pipelineStore'
import Inspector from '../Inspector'
import PipelineNodeComponent from './PipelineNode'
import PipelineEdgeComponent from './PipelineEdge'
import { createPipelineNodes, createPipelineEdges } from './pipelineLayout'

const nodeTypes = { pipelineNode: PipelineNodeComponent }
const edgeTypes = { pipelineEdge: PipelineEdgeComponent }

interface PipelineDAGProps {
  tenantId?: string
}

export default function PipelineDAG({ tenantId: _tenantId }: PipelineDAGProps) {
  const { nodes: storeNodes } = usePipelineStore()
  const [inspectorNode, setInspectorNode] = useState<string | null>(null)

  const nodeStatuses = useMemo(() => {
    const statuses: Record<string, { status: string; throughput: number }> = {}
    for (const node of storeNodes) {
      statuses[node.id] = {
        status: node.active ? 'healthy' : 'idle',
        throughput: node.active ? Math.floor(100 + Math.random() * 50) : 0,
      }
    }
    return statuses
  }, [storeNodes])

  const nodes = useMemo(() => createPipelineNodes(nodeStatuses), [nodeStatuses])
  const activeNodeIds = useMemo(
    () => new Set(storeNodes.filter((n) => n.active).map((n) => n.id)),
    [storeNodes],
  )
  const edges = useMemo(() => createPipelineEdges(activeNodeIds), [activeNodeIds])

  const onNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    setInspectorNode(node.id)
  }, [])

  const chain = [
    { ts: '2026-02-12 14:03:22', op: 'UPLOAD', ok: true },
    { ts: '2026-02-12 14:03:25', op: 'PARSE', ok: true },
    { ts: '2026-02-12 14:03:28', op: 'SIGN', ok: true },
  ]

  return (
    <>
      <div className="w-full h-64 bg-base border border-border">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          proOptions={{ hideAttribution: true }}
          minZoom={0.5}
          maxZoom={2}
        >
          <Background color="#3c4045" gap={20} size={1} />
        </ReactFlow>
      </div>

      {inspectorNode && (
        <Inspector
          title={storeNodes.find((n) => n.id === inspectorNode)?.label ?? inspectorNode}
          chain={chain}
          onClose={() => setInspectorNode(null)}
        />
      )}
    </>
  )
}
```

**Step 2: Commit**

```bash
git add packages/admin-dashboard/src/components/pipeline/PipelineDAG.tsx
git commit -m "feat: add PipelineDAG React Flow canvas with interactive nodes"
```

---

## Task 12: Replace PipelineSchematic with PipelineDAG

**Files:**
- Modify: `packages/admin-dashboard/src/features/pipeline/PipelineSchematic.tsx`

**Step 1: Replace the static schematic**

Rewrite `PipelineSchematic.tsx` to use the new `PipelineDAG` component. Keep `Panel` wrapper and `PipelineLogStream`:

```typescript
import Panel from '../../components/Panel'
import PipelineDAG from '../../components/pipeline/PipelineDAG'
import PipelineLogStream from './PipelineLogStream'

export default function PipelineSchematic() {
  return (
    <Panel title="PIPELINE SCHEMATIC">
      <PipelineDAG />
      <PipelineLogStream />
    </Panel>
  )
}
```

**Step 2: Verify build**

Run:
```bash
cd packages/admin-dashboard && npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add packages/admin-dashboard/src/features/pipeline/PipelineSchematic.tsx
git commit -m "refactor: replace static ASCII pipeline with React Flow DAG"
```

---

## Task 13: Create TenantDetailView page

**Files:**
- Create: `packages/admin-dashboard/src/pages/TenantDetailView.tsx`

**Step 1: Create the focused tenant view**

```typescript
import { useParams, useNavigate } from 'react-router-dom'
import { usePipelineStore } from '../stores/pipelineStore'
import Panel from '../components/Panel'
import PipelineDAG from '../components/pipeline/PipelineDAG'

export default function TenantDetailView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { tenants } = usePipelineStore()

  const tenant = tenants.find((t) => t.id === id)

  if (!tenant) {
    return (
      <div className="p-6">
        <Panel title="TENANT NOT FOUND">
          <p className="text-red-400 font-mono text-sm">
            No tenant found with ID: {id}
          </p>
          <button
            onClick={() => navigate('/tenants')}
            className="mt-4 px-4 py-2 border border-border bg-interactive text-text-primary text-xs font-medium uppercase tracking-wider hover:bg-surface"
          >
            [BACK]
          </button>
        </Panel>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/tenants')}
          className="px-3 py-1 border border-border bg-interactive text-text-primary text-xs font-medium uppercase tracking-wider hover:bg-surface"
        >
          [BACK]
        </button>
        <h2 className="text-sm font-medium uppercase tracking-wider text-text-secondary">
          TENANT: {tenant.id}
        </h2>
        <span className={`text-xs ${tenant.active ? 'text-accent' : 'text-inactive'}`}>
          [{tenant.active ? 'ACTIVE' : 'INACTIVE'}]
        </span>
      </div>

      <Panel title="TENANT OVERVIEW">
        <div className="grid grid-cols-3 gap-6">
          <div className="space-y-1">
            <span className="text-xs text-text-tertiary uppercase tracking-wider block">DOCUMENTS</span>
            <span className="text-xl font-mono text-text-primary">{tenant.docs.toLocaleString()}</span>
          </div>
          <div className="space-y-1">
            <span className="text-xs text-text-tertiary uppercase tracking-wider block">VECTORS</span>
            <span className="text-xl font-mono text-text-primary">{tenant.vec}</span>
          </div>
          <div className="space-y-1">
            <span className="text-xs text-text-tertiary uppercase tracking-wider block">VERIFICATION</span>
            <span className="text-xl font-mono text-text-primary">{tenant.ver.toFixed(2)}</span>
          </div>
        </div>
      </Panel>

      <div className="border-2 border-dashed border-border p-4">
        <span className="text-[10px] font-medium uppercase tracking-wider text-text-tertiary mb-3 block">
          NETWORK ISOLATION BOUNDARY
        </span>
        <PipelineDAG tenantId={tenant.id} />
      </div>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add packages/admin-dashboard/src/pages/TenantDetailView.tsx
git commit -m "feat: add focused tenant detail view with isolated pipeline DAG"
```

---

## Task 14: Add TenantDetailView route and navigation

**Files:**
- Modify: `packages/admin-dashboard/src/App.tsx`
- Modify: `packages/admin-dashboard/src/features/tenants/TenantChambers.tsx`

**Step 1: Add route in App.tsx**

Import `TenantDetailView` and add route after the existing `tenants/:id` route:

```typescript
import TenantDetailView from './pages/TenantDetailView'
```

Add inside the Layout route, after `<Route path="tenants/:id" element={<TenantDetail />} />`:

```tsx
<Route path="tenants/:id/detail" element={<TenantDetailView />} />
```

**Step 2: Update TenantChambers navigation**

In `TenantChambers.tsx`, change the `navigate` call from `/tenants/${t.id}` to `/tenants/${t.id}/detail`:

```typescript
navigate(`/tenants/${t.id}/detail`)
```

**Step 3: Verify build**

Run:
```bash
cd packages/admin-dashboard && npx tsc --noEmit
```

**Step 4: Commit**

```bash
git add packages/admin-dashboard/src/App.tsx packages/admin-dashboard/src/features/tenants/TenantChambers.tsx
git commit -m "feat: wire up tenant detail route and navigation from chambers"
```

---

## Task 15: Create MockWebSocket service

**Files:**
- Create: `packages/admin-dashboard/src/services/mockWebSocket.ts`

**Step 1: Create the mock socket service**

```typescript
type EventCallback = (data: unknown) => void

export interface ThroughputEvent {
  nodeId: string
  throughput: number
}

export interface NodeStatusEvent {
  nodeId: string
  status: 'healthy' | 'processing' | 'error' | 'idle'
}

export interface DocumentProgressEvent {
  documentId: string
  stage: string
  progress: number
}

export class MockPipelineSocket {
  private listeners: Map<string, Set<EventCallback>> = new Map()
  private intervals: number[] = []
  private _isConnected = false

  get isConnected(): boolean {
    return this._isConnected
  }

  connect(): void {
    if (this._isConnected) return
    this._isConnected = true
    this.emit('connection', { connected: true })
    this.startEmitting()
  }

  disconnect(): void {
    this._isConnected = false
    for (const interval of this.intervals) {
      clearInterval(interval)
    }
    this.intervals = []
    this.emit('connection', { connected: false })
  }

  on(event: string, callback: EventCallback): () => void {
    const existing = this.listeners.get(event)
    if (existing) {
      existing.add(callback)
    } else {
      this.listeners.set(event, new Set([callback]))
    }
    return () => {
      this.listeners.get(event)?.delete(callback)
    }
  }

  private emit(event: string, data: unknown): void {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      for (const cb of callbacks) {
        cb(data)
      }
    }
  }

  private startEmitting(): void {
    const STAGES = ['intake', 'parse', 'evidence', 'embed', 'vector', 'metadata', 'verify']
    const baseThroughputs: Record<string, number> = {
      intake: 142, parse: 138, evidence: 124, embed: 120,
      vector: 118, metadata: 118, verify: 115,
    }

    // Throughput updates every 2s
    this.intervals.push(
      window.setInterval(() => {
        if (!this._isConnected) return
        for (const nodeId of STAGES) {
          const base = baseThroughputs[nodeId]
          const jitter = base * 0.15
          const throughput = Math.round(base + (Math.random() * 2 - 1) * jitter)
          this.emit('pipeline:throughput', { nodeId, throughput } satisfies ThroughputEvent)
        }
      }, 2000),
    )

    // Node status changes every 5s
    this.intervals.push(
      window.setInterval(() => {
        if (!this._isConnected) return
        if (Math.random() > 0.3) return // Only 70% chance of status change
        const nodeId = STAGES[Math.floor(Math.random() * STAGES.length)]
        const status = Math.random() > 0.15 ? 'processing' : 'healthy'
        this.emit('pipeline:node-status', { nodeId, status } satisfies NodeStatusEvent)
      }, 5000),
    )

    // Document progress every 3s
    this.intervals.push(
      window.setInterval(() => {
        if (!this._isConnected) return
        const stageIndex = Math.floor(Math.random() * STAGES.length)
        this.emit('pipeline:document-progress', {
          documentId: `mock-${Math.random().toString(16).slice(2, 6)}`,
          stage: STAGES[stageIndex],
          progress: Math.round(Math.random() * 100),
        } satisfies DocumentProgressEvent)
      }, 3000),
    )
  }
}
```

**Step 2: Commit**

```bash
git add packages/admin-dashboard/src/services/mockWebSocket.ts
git commit -m "feat: add MockPipelineSocket service for simulated real-time updates"
```

---

## Task 16: Create useWebSocket hook

**Files:**
- Create: `packages/admin-dashboard/src/hooks/useWebSocket.ts`

**Step 1: Create the hook**

```typescript
import { useEffect, useRef, useState, useCallback } from 'react'
import { MockPipelineSocket } from '../services/mockWebSocket'
import { usePipelineStore } from '../stores/pipelineStore'
import type { ThroughputEvent, NodeStatusEvent } from '../services/mockWebSocket'

export function useWebSocket() {
  const socketRef = useRef<MockPipelineSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const store = usePipelineStore

  useEffect(() => {
    const socket = new MockPipelineSocket()
    socketRef.current = socket

    socket.on('connection', (data) => {
      setIsConnected((data as { connected: boolean }).connected)
    })

    socket.on('pipeline:throughput', (_data) => {
      // Throughput updates are consumed by PipelineDAG via store
      // Future: update store with per-node throughput
    })

    socket.on('pipeline:node-status', (data) => {
      const { nodeId, status } = data as NodeStatusEvent
      store.setState((state) => ({
        nodes: state.nodes.map((n) =>
          n.id === nodeId ? { ...n, active: status !== 'idle' } : n
        ),
      }))
    })

    socket.connect()

    return () => {
      socket.disconnect()
      socketRef.current = null
    }
  }, [])

  const disconnect = useCallback(() => {
    socketRef.current?.disconnect()
  }, [])

  const reconnect = useCallback(() => {
    socketRef.current?.connect()
  }, [])

  return { isConnected, disconnect, reconnect }
}
```

**Step 2: Commit**

```bash
git add packages/admin-dashboard/src/hooks/useWebSocket.ts
git commit -m "feat: add useWebSocket hook connecting mock socket to pipeline store"
```

---

## Task 17: Integrate WebSocket into Header

**Files:**
- Modify: `packages/admin-dashboard/src/components/Header.tsx`

**Step 1: Add WebSocket status indicator**

Import `useWebSocket` and add connection status display. The full Header should now show:
- Tenant selector (existing)
- Pipeline status dot (existing)
- `ONLINE`/`OFFLINE` network status (from Task 6)
- `WS CONNECTED`/`WS DISCONNECTED` indicator (new)
- Logout button (existing)

Add the WebSocket import and hook call:

```typescript
import { useWebSocket } from '../hooks/useWebSocket'
```

Inside the component:
```typescript
const { isConnected: wsConnected } = useWebSocket()
```

Add after the offline/online span:
```tsx
<span className={`text-xs font-medium uppercase tracking-wider ${wsConnected ? 'text-green-400' : 'text-red-400'}`}>
  {wsConnected ? 'WS CONNECTED' : 'WS DISCONNECTED'}
</span>
```

**Step 2: Commit**

```bash
git add packages/admin-dashboard/src/components/Header.tsx
git commit -m "feat: add WebSocket connection status indicator to header"
```

---

## Task 18: Create useTokenRefresh hook

**Files:**
- Create: `packages/admin-dashboard/src/hooks/useTokenRefresh.ts`

**Step 1: Create the token refresh hook**

```typescript
import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { isMockMode } from '../api/client'

const TOKEN_TTL_MS = 30 * 60 * 1000 // 30 minutes
const WARN_BEFORE_MS = 5 * 60 * 1000 // 5 minutes
const MOCK_REFRESH_FAILURE_RATE = 0.05

export function useTokenRefresh() {
  const { isAuthenticated, logout } = useAuth()
  const [expiresIn, setExpiresIn] = useState<number | null>(null)
  const [showWarning, setShowWarning] = useState(false)
  const expiryRef = useRef<number>(Date.now() + TOKEN_TTL_MS)
  const timerRef = useRef<number | null>(null)

  const refreshToken = useCallback(async () => {
    if (!isMockMode()) return

    if (Math.random() < MOCK_REFRESH_FAILURE_RATE) {
      logout()
      return
    }

    expiryRef.current = Date.now() + TOKEN_TTL_MS
    setShowWarning(false)
    setExpiresIn(TOKEN_TTL_MS)
  }, [logout])

  useEffect(() => {
    if (!isAuthenticated) {
      setShowWarning(false)
      setExpiresIn(null)
      return
    }

    expiryRef.current = Date.now() + TOKEN_TTL_MS

    timerRef.current = window.setInterval(() => {
      const remaining = expiryRef.current - Date.now()
      setExpiresIn(remaining)

      if (remaining <= WARN_BEFORE_MS && remaining > 0) {
        setShowWarning(true)
      }

      if (remaining <= 0) {
        refreshToken()
      }
    }, 1000)

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [isAuthenticated, refreshToken])

  const dismissWarning = useCallback(() => {
    setShowWarning(false)
  }, [])

  return { expiresIn, showWarning, dismissWarning }
}
```

**Step 2: Commit**

```bash
git add packages/admin-dashboard/src/hooks/useTokenRefresh.ts
git commit -m "feat: add useTokenRefresh hook with mock token lifecycle"
```

---

## Task 19: Create SessionWarning component

**Files:**
- Create: `packages/admin-dashboard/src/components/SessionWarning.tsx`

**Step 1: Create the session warning toast**

```typescript
import { useTokenRefresh } from '../hooks/useTokenRefresh'

function formatTime(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

export default function SessionWarning() {
  const { expiresIn, showWarning, dismissWarning } = useTokenRefresh()

  if (!showWarning || expiresIn === null) return null

  return (
    <div className="fixed top-4 right-4 z-50 bg-surface border border-accent p-4 max-w-xs">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-accent mb-1">
            SESSION EXPIRES IN
          </p>
          <p className="text-lg font-mono text-text-primary">
            {formatTime(expiresIn)}
          </p>
        </div>
        <button
          onClick={dismissWarning}
          className="text-text-secondary hover:text-text-primary text-xs"
        >
          [x]
        </button>
      </div>
    </div>
  )
}
```

**Step 2: Add to Layout**

Modify: `packages/admin-dashboard/src/components/Layout.tsx`

Import `SessionWarning` and render it inside the layout (alongside MockBanner).

**Step 3: Commit**

```bash
git add packages/admin-dashboard/src/components/SessionWarning.tsx packages/admin-dashboard/src/components/Layout.tsx
git commit -m "feat: add session expiry warning toast with countdown"
```

---

## Task 20: Final build verification and cleanup

**Files:**
- All modified files

**Step 1: Run TypeScript check**

Run:
```bash
cd packages/admin-dashboard && npx tsc --noEmit
```

Expected: No type errors

**Step 2: Run dev server**

Run:
```bash
cd packages/admin-dashboard && npm run dev
```

Expected: Vite starts without errors on port 5174

**Step 3: Fix any build errors**

If any type errors or build issues, fix them.

**Step 4: Final commit**

```bash
git add -A
git commit -m "fix: resolve any remaining build issues from dashboard completion"
```

Only create this commit if there are actual changes to commit.
