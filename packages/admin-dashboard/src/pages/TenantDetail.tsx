import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { usePipelineStore } from '../stores/pipelineStore'
import Panel from '../components/Panel'

export default function TenantDetail() {
  const { id } = useParams<{ id: string }>()
  const { tenants } = usePipelineStore()
  const chamber = tenants.find((t) => t.id === id)
  const { data: schema, isLoading, error } = useQuery({
    queryKey: ['tenant-schema', id],
    queryFn: () => api.getTenantSchema(id!),
    enabled: !!id,
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          to="/tenants"
          className="text-text-secondary hover:text-text-primary text-xs font-medium uppercase tracking-wider"
        >
          [← BACK]
        </Link>
      </div>
      <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary">
        TENANT: {id}
        {chamber?.active ? (
          <span className="text-accent ml-2">[ACTIVE]</span>
        ) : (
          <span className="text-inactive ml-2">[INACTIVE]</span>
        )}
      </h2>

      <Panel title="ISOLATED PIPELINE SCHEMATIC">
        <div className="flex flex-wrap items-center gap-2 font-mono text-sm">
          {['INTAKE', 'PARSE', 'EVIDENCE', 'EMBED', 'VECTOR', 'METADATA', 'VERIFY'].map((label, i) => (
            <span key={label} className="flex items-center gap-2">
              <span className="px-2 py-1 border border-accent bg-surface text-accent">
                [{label}]
              </span>
              {i < 6 && <span className="text-accent">────►</span>}
            </span>
          ))}
        </div>
        <p className="text-xs text-text-tertiary mt-2">
          Network policies: dashed barriers (tenant isolation)
        </p>
      </Panel>

      {chamber && (
        <Panel title="RESOURCE ALLOCATION">
          <p className="text-text-primary font-mono">
            DOCS: {chamber.docs.toLocaleString()} | VEC: {chamber.vec} | VER: {chamber.ver.toFixed(2)}
          </p>
          <p className="text-text-tertiary text-xs mt-2">CPU 2.1 / 4.0 cores</p>
        </Panel>
      )}

      <Panel title="SCHEMA">
        {isLoading && <p className="text-text-tertiary">LOADING SCHEMA…</p>}
        {error && <p className="text-red-400">FAILED: Tenant schema not found.</p>}
        {schema && (
          <pre className="text-sm bg-base border border-border p-4 overflow-auto max-h-96 text-text-primary">
            {JSON.stringify(schema, null, 2)}
          </pre>
        )}
      </Panel>
    </div>
  )
}
