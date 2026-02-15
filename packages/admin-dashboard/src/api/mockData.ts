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
