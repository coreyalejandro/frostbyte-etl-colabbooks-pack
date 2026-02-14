// ISSUE #1-10: Added Model Metrics Dashboard Widget
// REASONING: Show model observability summary on main dashboard
// ADDED BY: Kombai on 2026-02-14

import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import Panel from '../components/Panel'
import PipelineSchematic from '../features/pipeline/PipelineSchematic'
import TenantChambers from '../features/tenants/TenantChambers'
import DocumentQueue from '../features/documents/DocumentQueue'
import AuditGallery from '../features/audit/AuditGallery'
import { useModelMetrics } from '../hooks/useModelMetrics'

export default function Dashboard() {
  const { data: health, isLoading, error } = useQuery({
    queryKey: ['health'],
    queryFn: api.health,
  })
  const { data: modelMetrics } = useModelMetrics()

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary">
          DASHBOARD
        </h2>
      </div>

      <PipelineSchematic />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <TenantChambers />
        
        <Panel 
          title="MODEL HEALTH"
          actions={
            <Link 
              to="/observatory" 
              className="text-xs text-text-secondary hover:text-accent border border-border hover:border-accent px-2 py-1"
              aria-label="View full model observatory"
            >
              [VIEW ALL]
            </Link>
          }
        >
          {modelMetrics && modelMetrics.length > 0 ? (
            <div className="space-y-2">
              {modelMetrics.slice(0, 3).map(metric => (
                <div key={metric.modelName} className="text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-text-primary font-mono">
                      {metric.modelName.split('-')[0]}
                    </span>
                    <span className={metric.successRate >= 0.95 ? 'text-accent' : 'text-red-400'}>
                      {(metric.successRate * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="text-text-tertiary">
                    {metric.totalInvocations} calls • {metric.avgDurationMs}ms avg
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-tertiary">NO MODEL DATA</p>
          )}
        </Panel>

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
