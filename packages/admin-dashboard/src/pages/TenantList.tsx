import { useTenant } from '../contexts/TenantContext'
import { usePipelineStore } from '../stores/pipelineStore'
import TenantChambers from '../features/tenants/TenantChambers'
import Panel from '../components/Panel'

export default function TenantList() {
  const { selectedTenantId, setSelectedTenantId } = useTenant()
  const { tenants } = usePipelineStore()
  return (
    <div className="space-y-6">
      <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary">
        TENANTS
      </h2>
      <TenantChambers />
      <Panel title="SELECTED TENANT (SCHEMA)">
        <p className="text-text-secondary mb-4">
          Tenant management. Schema extensions via <code className="bg-interactive px-1">/tenants/&#123;id&#125;/schema</code>.
        </p>
        <select
          value={selectedTenantId ?? ''}
          onChange={(e) => setSelectedTenantId(e.target.value || null)}
          className="bg-base border border-border px-3 py-2 text-text-primary focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-0"
        >
          <option value="default">default</option>
          {tenants.map((t) => (
            <option key={t.id} value={t.id}>{t.id}</option>
          ))}
        </select>
      </Panel>
    </div>
  )
}
