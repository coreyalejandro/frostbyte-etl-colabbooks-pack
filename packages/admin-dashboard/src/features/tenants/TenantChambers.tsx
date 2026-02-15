import { useNavigate } from 'react-router-dom'
import { usePipelineStore } from '../../stores/pipelineStore'
import { useTenant } from '../../contexts/TenantContext'
import Panel from '../../components/Panel'

export default function TenantChambers() {
  const { tenants } = usePipelineStore()
  const { setSelectedTenantId } = useTenant()
  const navigate = useNavigate()

  return (
    <Panel title="TENANT CHAMBERS">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tenants.map((t) => (
          <button
            key={t.id}
            onClick={() => {
              setSelectedTenantId(t.id)
              navigate(`/tenants/${t.id}/detail`)
            }}
            className="text-left border border-border p-3 bg-surface hover:border-inactive min-w-0 overflow-hidden"
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <span className="text-xs font-medium uppercase tracking-wider text-text-secondary truncate">
                TENANT-{t.id.replace('PROD-', '')}
              </span>
              <span className={`text-xs shrink-0 ${t.active ? 'text-accent' : 'text-inactive'}`}>
                [{t.active ? 'ACTIVE' : 'INACTIVE'}]
              </span>
            </div>
            <div className="space-y-1 text-xs text-text-primary font-mono">
              <div className="flex justify-between">
                <span>DOC:</span>
                <span>{t.docs.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span>VEC:</span>
                <span>{t.vec}</span>
              </div>
              <div className="flex justify-between">
                <span>VER:</span>
                <span>{t.ver.toFixed(2)}</span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </Panel>
  )
}
