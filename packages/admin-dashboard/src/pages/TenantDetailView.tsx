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
