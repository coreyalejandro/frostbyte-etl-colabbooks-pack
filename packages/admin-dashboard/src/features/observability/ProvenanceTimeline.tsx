// PRIORITY 1: Extreme Observability - Provenance Timeline
// Model version history, deployment tracking, rollback capability

import { useState } from 'react'
import Panel from '../../components/Panel'

interface ModelVersion {
  id: string
  modelName: string
  version: string
  deployedAt: string
  deployedBy: string
  configuration: Record<string, unknown>
  isActive: boolean
  performanceMetrics?: {
    accuracy: number
    latencyP95: number
    costPerCall: number
  }
  changeSummary: string
}

interface ProvenanceTimelineProps {
  modelName?: string
}

// Mock data - would come from API
const MOCK_VERSIONS: ModelVersion[] = [
  {
    id: '1',
    modelName: 'docling',
    version: 'v2.70',
    deployedAt: '2026-02-10T14:30:00Z',
    deployedBy: 'admin@frostbyte.ai',
    configuration: {
      chunkSize: 512,
      overlap: 64,
      extractTables: true,
      extractImages: false,
    },
    isActive: true,
    performanceMetrics: {
      accuracy: 0.987,
      latencyP95: 4200,
      costPerCall: 0.0008,
    },
    changeSummary: 'Added table extraction, improved OCR',
  },
  {
    id: '2',
    modelName: 'docling',
    version: 'v2.69',
    deployedAt: '2026-02-05T09:15:00Z',
    deployedBy: 'admin@frostbyte.ai',
    configuration: {
      chunkSize: 512,
      overlap: 32,
      extractTables: false,
      extractImages: false,
    },
    isActive: false,
    performanceMetrics: {
      accuracy: 0.972,
      latencyP95: 3800,
      costPerCall: 0.0006,
    },
    changeSummary: 'Baseline configuration',
  },
  {
    id: '3',
    modelName: 'nomic-embed-text-v1',
    version: 'v1.5.0',
    deployedAt: '2026-02-12T10:00:00Z',
    deployedBy: 'admin@frostbyte.ai',
    configuration: {
      embeddingDimension: 768,
      batchSize: 32,
      normalize: true,
    },
    isActive: true,
    performanceMetrics: {
      accuracy: 0.945,
      latencyP95: 2850,
      costPerCall: 0.00012,
    },
    changeSummary: 'Upgraded to latest Nomic model',
  },
]

export default function ProvenanceTimeline({ modelName }: ProvenanceTimelineProps) {
  const [selectedVersion, setSelectedVersion] = useState<ModelVersion | null>(null)
  const [showRollbackConfirm, setShowRollbackConfirm] = useState(false)
  const [filter, setFilter] = useState<string>('all')

  const filteredVersions = modelName
    ? MOCK_VERSIONS.filter((v) => v.modelName === modelName)
    : MOCK_VERSIONS

  const uniqueModels = Array.from(new Set(MOCK_VERSIONS.map((v) => v.modelName)))

  const handleRollback = (version: ModelVersion) => {
    // Would call API to rollback
    console.log('Rolling back to:', version)
    setShowRollbackConfirm(false)
    alert(`Rollback to ${version.modelName} ${version.version} initiated`)
  }

  return (
    <Panel title="PROVENANCE TIMELINE">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2 mb-4 pb-3 border-b border-border">
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="px-2 py-1 text-xs bg-surface border border-border text-text-primary"
        >
          <option value="all">ALL MODELS</option>
          {uniqueModels.map((model) => (
            <option key={model} value={model}>
              {model.toUpperCase()}
            </option>
          ))}
        </select>

        <button
          onClick={() => setSelectedVersion(null)}
          className="px-2 py-1 text-xs text-text-secondary hover:text-accent border border-border hover:border-accent"
        >
          [REFRESH]
        </button>
      </div>

      {/* Timeline */}
      <div className="space-y-4 relative">
        {/* Timeline line */}
        <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-border" />

        {filteredVersions.map((version, index) => (
          <div
            key={version.id}
            className="relative pl-8 cursor-pointer group"
            onClick={() => setSelectedVersion(version)}
          >
            {/* Timeline dot */}
            <div
              className={`absolute left-1.5 top-1.5 w-3 h-3 rounded-full border-2 ${
                version.isActive
                  ? 'bg-accent border-accent'
                  : 'bg-surface border-border group-hover:border-accent'
              }`}
            />

            {/* Version card */}
            <div
              className={`p-3 border rounded transition-colors ${
                version.isActive
                  ? 'border-accent bg-accent/5'
                  : 'border-border bg-surface hover:bg-interactive'
              } ${selectedVersion?.id === version.id ? 'ring-1 ring-accent' : ''}`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-text-primary">
                      {version.modelName}
                    </span>
                    <span className="text-xs text-accent font-mono">
                      {version.version}
                    </span>
                    {version.isActive && (
                      <span className="px-1.5 py-0.5 text-[10px] bg-accent text-black rounded uppercase">
                        Active
                      </span>
                    )}
                  </div>

                  <div className="text-xs text-text-secondary mb-2">
                    {version.changeSummary}
                  </div>

                  <div className="flex items-center gap-3 text-[10px] text-text-tertiary">
                    <span>{new Date(version.deployedAt).toLocaleDateString()}</span>
                    <span>by {version.deployedBy}</span>
                  </div>
                </div>

                {/* Metrics */}
                {version.performanceMetrics && (
                  <div className="text-right text-xs space-y-1">
                    <div className="text-text-secondary">
                      {(version.performanceMetrics.accuracy * 100).toFixed(1)}% acc
                    </div>
                    <div className="text-text-tertiary">
                      {version.performanceMetrics.latencyP95}ms
                    </div>
                    <div className="text-accent">
                      ${version.performanceMetrics.costPerCall.toFixed(4)}
                    </div>
                  </div>
                )}
              </div>

              {/* Rollback button for inactive versions */}
              {!version.isActive && (
                <div className="mt-3 pt-3 border-t border-border flex justify-end">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedVersion(version)
                      setShowRollbackConfirm(true)
                    }}
                    className="px-3 py-1 text-xs border border-border hover:border-accent text-text-secondary hover:text-accent transition-colors"
                  >
                    [ROLLBACK]
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Selected version details */}
      {selectedVersion && (
        <div className="mt-4 p-3 bg-surface-elevated rounded border border-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-text-primary">
              Configuration: {selectedVersion.modelName} {selectedVersion.version}
            </span>
            <button
              onClick={() => setSelectedVersion(null)}
              className="text-text-secondary hover:text-text-primary"
            >
              ✕
            </button>
          </div>
          <pre className="text-xs text-text-secondary overflow-auto max-h-32">
            {JSON.stringify(selectedVersion.configuration, null, 2)}
          </pre>
        </div>
      )}

      {/* Rollback confirmation modal */}
      {showRollbackConfirm && selectedVersion && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface border border-border p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-medium text-text-primary mb-4">
              Confirm Rollback
            </h3>
            <p className="text-sm text-text-secondary mb-4">
              Rollback <strong>{selectedVersion.modelName}</strong> from{' '}
              <span className="text-accent">current</span> to{' '}
              <span className="text-accent">{selectedVersion.version}</span>?
            </p>
            <div className="text-xs text-text-tertiary mb-6">
              This will deploy the previous version and may affect documents in progress.
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowRollbackConfirm(false)}
                className="px-4 py-2 text-sm text-text-secondary hover:text-text-primary"
              >
                Cancel
              </button>
              <button
                onClick={() => handleRollback(selectedVersion)}
                className="px-4 py-2 text-sm bg-accent text-black hover:bg-accent-hover"
              >
                Confirm Rollback
              </button>
            </div>
          </div>
        </div>
      )}
    </Panel>
  )
}
