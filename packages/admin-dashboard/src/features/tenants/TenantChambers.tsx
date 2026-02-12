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
              navigate(`/tenants/${t.id}`)
            }}
            className="text-left border border-border p-4 bg-surface hover:border-inactive"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-medium uppercase tracking-wider text-text-secondary">
                TENANT-{t.id.replace('PROD-', '')}
              </span>
              <span className={t.active ? 'text-accent' : 'text-inactive'}>
                [{t.active ? 'ACTIVE' : 'INACTIVE'}]
              </span>
            </div>
            <p className="text-sm text-text-primary font-mono">
              DOC: {t.docs.toLocaleString()} | VEC: {t.vec} | VER: {t.ver.toFixed(2)}
            </p>
          </button>
        ))}
      </div>
    </Panel>
  )
}
