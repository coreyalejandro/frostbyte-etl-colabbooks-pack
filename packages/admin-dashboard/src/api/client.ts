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
