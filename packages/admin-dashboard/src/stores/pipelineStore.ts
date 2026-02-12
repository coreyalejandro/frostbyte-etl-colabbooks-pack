import { create } from 'zustand'
import { produce } from 'immer'

export type PipelineMode = 'ONLINE' | 'OFFLINE' | 'HYBRID'
export type EmbeddingModel = 'OPENAI' | 'QWEN' | 'KIMI' | 'NOMIC'

export type DocStatus = 'PENDING' | 'PARSING' | 'EMBED' | 'VERIFY' | 'STORED' | 'FAILED'

export interface PipelineNode {
  id: string
  label: string
  desc: string
  active: boolean
}

export interface TenantChamber {
  id: string
  active: boolean
  docs: number
  vec: string
  ver: number
}

export interface DocumentRow {
  id: string
  name: string
  size: string
  status: DocStatus
  verification: number
}

export interface GateResult {
  gate: string
  result: 'PASS' | 'FAIL'
  hash?: string
}

export interface AuditEntry {
  timestamp: string
  tenant: string
  operation: string
  fingerprint: string
}

export interface ChainStep {
  ts: string
  op: string
  ok: boolean
}

interface PipelineState {
  mode: PipelineMode
  model: EmbeddingModel
  batchSize: number
  online: boolean

  nodes: PipelineNode[]
  tenants: TenantChamber[]
  documents: DocumentRow[]
  gate1: GateResult[]
  gate2: { query: string; recall: number; grounding: number }[]
  gate3: { score: number; lastTest: string } | null
  audit: AuditEntry[]

  setMode: (m: PipelineMode) => void
  setModel: (m: EmbeddingModel) => void
  setBatchSize: (n: number) => void
  setOnline: (v: boolean) => void
  moveDocument: (id: string, dir: 'up' | 'down') => void
  commitConfig: () => void
}

const NODES: PipelineNode[] = [
  { id: 'intake', label: 'INTAKE', desc: 'upload', active: true },
  { id: 'parse', label: 'PARSE', desc: 'extract text', active: true },
  { id: 'evidence', label: 'EVIDENCE', desc: 'verify', active: true },
  { id: 'embed', label: 'EMBED', desc: 'vectorize', active: true },
  { id: 'vector', label: 'VECTOR', desc: 'store', active: true },
  { id: 'metadata', label: 'METADATA', desc: 'index', active: true },
  { id: 'verify', label: 'VERIFY', desc: 'validate', active: true },
]

const MOCK_TENANTS: TenantChamber[] = [
  { id: 'PROD-01', active: true, docs: 1247, vec: '48.2K', ver: 0.98 },
  { id: 'PROD-02', active: true, docs: 892, vec: '32.1K', ver: 0.97 },
  { id: 'PROD-03', active: false, docs: 0, vec: '0', ver: 0 },
]

const MOCK_DOCS: DocumentRow[] = [
  { id: '0001', name: 'contract.pdf', size: '2.4M', status: 'STORED', verification: 0.99 },
  { id: '0002', name: 'appendix.md', size: '0.8M', status: 'PARSING', verification: 0.87 },
  { id: '0003', name: 'policy.docx', size: '1.2M', status: 'FAILED', verification: 0 },
]

const MOCK_AUDIT: AuditEntry[] = [
  { timestamp: '2026-02-12 14:03:22', tenant: 'PROD-01', operation: 'DOC_UPLOAD', fingerprint: 'a1b2c3d4' },
  { timestamp: '2026-02-12 14:02:18', tenant: 'PROD-01', operation: 'SLICE_SIGN', fingerprint: 'e5f6g7h8' },
  { timestamp: '2026-02-12 14:01:55', tenant: 'PROD-01', operation: 'CHAIN_APPEND', fingerprint: 'i9j0k1l2' },
]

export const usePipelineStore = create<PipelineState>()((set) => ({
  mode: 'ONLINE',
  model: 'NOMIC',
  batchSize: 32,
  online: true,
  nodes: NODES,
  tenants: MOCK_TENANTS,
  documents: MOCK_DOCS,
  gate1: [{ gate: 'EVIDENCE PACKAGING', result: 'PASS', hash: 'a1b2c3d4' }],
  gate2: [{ query: 'Sample query', recall: 0.94, grounding: 0.98 }],
  gate3: { score: 0.91, lastTest: '2026-02-12 13:45:00' },
  audit: MOCK_AUDIT,

  setMode: (m) => set({ mode: m }),
  setModel: (m) => set({ model: m }),
  setBatchSize: (n) => set({ batchSize: Math.max(1, Math.min(256, n)) }),
  setOnline: (v) => set({ online: v }),
  moveDocument: (id, dir) =>
    set(
      produce((s) => {
        const i = s.documents.findIndex((d: DocumentRow) => d.id === id)
        if (i < 0) return
        const j = dir === 'up' ? i - 1 : i + 1
        if (j < 0 || j >= s.documents.length) return
        ;[s.documents[i], s.documents[j]] = [s.documents[j], s.documents[i]]
      }),
    ),
  commitConfig: () =>
    set(
      produce((s) => {
        s.audit.unshift({
          timestamp: new Date().toISOString().slice(0, 19).replace('T', ' '),
          tenant: 'PROD-01',
          operation: 'CONFIG_CHANGE',
          fingerprint: `${Math.random().toString(16).slice(2, 10)}`,
        })
      }),
    ),
}))
