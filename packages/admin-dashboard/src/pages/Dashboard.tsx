import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import PipelineSchematic from '../features/pipeline/PipelineSchematic'
import TenantChambers from '../features/tenants/TenantChambers'
import DocumentQueue from '../features/documents/DocumentQueue'
import AuditGallery from '../features/audit/AuditGallery'

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      className="bg-surface border border-border p-4"
      style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }}
    >
      <h3 className="text-xs font-medium uppercase tracking-wider text-text-secondary mb-2">
        {title}
      </h3>
      {children}
    </div>
  )
}

export default function Dashboard() {
  const { data: health, isLoading, error } = useQuery({
    queryKey: ['health'],
    queryFn: api.health,
  })

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary">
          DASHBOARD
        </h2>
      </div>

      <PipelineSchematic />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <TenantChambers />
        <Panel title="API HEALTH">
          <p className="text-2xl font-medium text-text-primary">
            {isLoading ? '...' : error ? 'FAIL' : health?.status ?? '—'}
          </p>
          <p className="text-xs text-text-tertiary mt-1">
            {health?.timestamp ? new Date(health.timestamp).toLocaleString() : ''}
          </p>
        </Panel>
      </div>

      <DocumentQueue />

      <AuditGallery />
    </div>
  )
}
