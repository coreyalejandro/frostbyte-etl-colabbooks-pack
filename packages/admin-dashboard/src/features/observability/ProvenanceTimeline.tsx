// ISSUE #3, #17: Provenance Timeline Component
// REASONING: Model version history and deployment tracking for audibility
// ADDED BY: Kombai on 2026-02-14

import { useState } from 'react'
import Panel from '../../components/Panel'
import { useModelVersions, useRollbackModel } from '../../hooks/useModelVersions'
import type { ModelVersion } from '../../types/observability'

interface ProvenanceTimelineProps {
  /**
   * Optional model name to filter versions
   */
  modelName?: string
  /**
   * Show rollback controls
   */
  allowRollback?: boolean
}

export default function ProvenanceTimeline({ modelName, allowRollback = true }: ProvenanceTimelineProps) {
  const { data: allVersions, isLoading } = useModelVersions()
  const rollbackMutation = useRollbackModel()
  const [selectedVersion, setSelectedVersion] = useState<ModelVersion | null>(null)

  // Filter by model name if provided
  const versions = modelName
    ? allVersions?.filter(v => v.modelName === modelName)
    : allVersions

  // Group by model name
  const versionsByModel = versions?.reduce((acc, version) => {
    if (!acc[version.modelName]) {
      acc[version.modelName] = []
    }
    acc[version.modelName].push(version)
    return acc
  }, {} as Record<string, ModelVersion[]>)

  const handleRollback = (version: ModelVersion) => {
    if (!window.confirm(`Rollback ${version.modelName} to version ${version.version}?`)) {
      return
    }

    rollbackMutation.mutate({
      modelName: version.modelName,
      targetVersion: version.version,
    })
  }

  return (
    <Panel title="MODEL PROVENANCE TIMELINE">
      {isLoading && (
        <p className="text-sm text-text-tertiary text-center py-8">
          LOADING VERSION HISTORY...
        </p>
      )}

      {!isLoading && (!versions || versions.length === 0) && (
        <p className="text-sm text-text-tertiary text-center py-8">
          NO MODEL VERSIONS FOUND
        </p>
      )}

      {!isLoading && versionsByModel && (
        <div className="space-y-6">
          {Object.entries(versionsByModel).map(([model, modelVersions]) => (
            <div key={model}>
              {/* Model Header */}
              <h4 className="text-sm font-medium text-text-primary mb-3 uppercase tracking-wider">
                {model}
              </h4>

              {/* Timeline */}
              <div className="space-y-3">
                {modelVersions.map((version, index) => (
                  <div
                    key={version.id}
                    className="relative pl-6 pb-3 border-l-2 border-border last:border-l-0 last:pb-0"
                  >
                    {/* Timeline Dot */}
                    <div
                      className={`absolute left-0 top-1 -ml-[5px] w-2 h-2 rounded-full ${
                        version.isActive ? 'bg-accent' : 'bg-inactive'
                      }`}
                      aria-hidden="true"
                    />

                    {/* Version Card */}
                    <div
                      onClick={() => setSelectedVersion(selectedVersion?.id === version.id ? null : version)}
                      className="w-full text-left bg-surface border border-border hover:border-accent/50 p-3 transition-colors cursor-pointer"
                      style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)' }}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          setSelectedVersion(selectedVersion?.id === version.id ? null : version)
                        }
                      }}
                      aria-expanded={selectedVersion?.id === version.id}
                    >
                      <div className="flex items-start justify-between gap-3">
                        {/* Left: Version Info */}
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-medium text-text-primary font-mono">
                              v{version.version}
                            </span>
                            {version.isActive && (
                              <span className="text-xs text-accent uppercase tracking-wider border border-accent px-1">
                                ACTIVE
                              </span>
                            )}
                            {index === 0 && !version.isActive && (
                              <span className="text-xs text-text-tertiary uppercase tracking-wider border border-border px-1">
                                LATEST
                              </span>
                            )}
                          </div>

                          <div className="text-xs text-text-secondary space-y-1">
                            <div>
                              Deployed {new Date(version.deployedAt).toLocaleString()}
                            </div>
                            <div>
                              by {version.deployedBy}
                            </div>
                          </div>
                        </div>

                        {/* Right: Actions */}
                        {allowRollback && !version.isActive && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleRollback(version)
                            }}
                            disabled={rollbackMutation.isPending}
                            className="px-2 py-1 text-xs border border-border hover:border-accent text-text-secondary hover:text-accent disabled:opacity-50 disabled:cursor-not-allowed"
                            aria-label={`Rollback to version ${version.version}`}
                          >
                            {rollbackMutation.isPending ? '[ROLLING BACK...]' : '[ROLLBACK]'}
                          </button>
                        )}
                      </div>

                      {/* Expanded Configuration */}
                      {selectedVersion?.id === version.id && (
                        <div className="mt-3 pt-3 border-t border-border">
                          <div className="text-xs text-text-tertiary mb-2 uppercase tracking-wider">
                            CONFIGURATION
                          </div>
                          <div className="bg-base border border-border p-2 font-mono text-xs overflow-x-auto">
                            <pre className="text-text-primary">
                              {JSON.stringify(version.configuration, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  )
}
