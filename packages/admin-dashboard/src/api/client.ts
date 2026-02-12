/**
 * API client for Frostbyte ETL Pipeline.
 * Calls the pipeline API at VITE_API_URL (default http://localhost:8000).
 * Sends Bearer token when set via setAuthToken().
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
  return res.json() as Promise<T>;
}

export interface Health {
  status: string;
  timestamp: string;
}

export interface DocumentMetadata {
  id: string;
  tenant_id?: string;
  filename?: string;
  status?: string;
  modality?: string;
  bucket?: string;
  object_key?: string;
  created_at?: string;
}

export async function login(apiKey: string): Promise<{ access_token: string }> {
  const base = API_BASE || '';
  const url = base ? `${base}/api/v1/auth/token` : '/api/v1/auth/token';
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: { message?: string } })?.detail?.message || `Login failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => fetchApi<Health>('/health'),
  getDocument: (id: string) => fetchApi<DocumentMetadata>(`/api/v1/documents/${id}`),
  getTenantSchema: (tenantId: string) =>
    fetchApi<{ document_fields: Record<string, unknown>; chunk_fields: Record<string, unknown> }>(
      `/tenants/${tenantId}/schema`,
    ),
};
