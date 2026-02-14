// ISSUE #2, #7: Decision Tracer Component
// REASONING: Interactive inspection of model inputs/outputs for transparency
// ADDED BY: Kombai on 2026-02-14

import { useState } from 'react'
import Panel from '../../components/Panel'
import { useDecisionTrace } from '../../hooks/useDecisionTraces'
import type { ModelEvent } from '../../types/observability'

interface DecisionTracerProps {
  /**
   * Model event to trace
   */
  event: ModelEvent | null
  /**
   * Callback to close the tracer
   */
  onClose?: () => void
}

export default function DecisionTracer({ event, onClose }: DecisionTracerProps) {
  const { data: trace, isLoading } = useDecisionTrace(event?.id ?? null)
  const [activeTab, setActiveTab] = useState<'input' | 'output' | 'rationale'>('input')

  if (!event) {
    return (
      <Panel title="DECISION TRACER">
        <p className="text-sm text-text-tertiary text-center py-8">
          SELECT AN EVENT FROM ACTIVITY MONITOR TO TRACE
        </p>
      </Panel>
    )
  }

  return (
    <Panel title="DECISION TRACER">
      {/* Event Header */}
      <div className="pb-3 mb-4 border-b border-border">
        <div className="flex items-start justify-between mb-2">
          <div>
            <h4 className="text-sm font-medium text-text-primary">
              {event.modelName} <span className="text-text-tertiary">v{event.modelVersion}</span>
            </h4>
            <p className="text-xs text-text-secondary mt-1">
              {event.operation} → {event.documentName ?? event.documentId}
            </p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="px-2 py-1 text-xs border border-border hover:border-accent text-text-secondary hover:text-accent"
              aria-label="Close decision tracer"
            >
              [CLOSE]
            </button>
          )}
        </div>

        <div className="flex items-center gap-3 text-xs text-text-tertiary">
          <span>EVENT ID: {event.id}</span>
          <span>•</span>
          <span>{new Date(event.timestamp).toLocaleString()}</span>
          {trace?.confidenceScore !== undefined && (
            <>
              <span>•</span>
              <span className={trace.confidenceScore >= 0.7 ? 'text-accent' : 'text-red-400'}>
                CONFIDENCE: {(trace.confidenceScore * 100).toFixed(1)}%
              </span>
            </>
          )}
        </div>
      </div>

      {isLoading && (
        <p className="text-sm text-text-tertiary text-center py-8">
          LOADING TRACE DATA...
        </p>
      )}

      {!isLoading && !trace && (
        <p className="text-sm text-text-tertiary text-center py-8">
          NO TRACE DATA AVAILABLE FOR THIS EVENT
        </p>
      )}

      {!isLoading && trace && (
        <>
          {/* Tabs */}
          <div className="flex gap-1 mb-4">
            <button
              onClick={() => setActiveTab('input')}
              className={`px-3 py-1 text-xs font-medium uppercase tracking-wider border ${
                activeTab === 'input'
                  ? 'border-accent bg-surface text-accent'
                  : 'border-border bg-interactive text-text-secondary hover:text-text-primary'
              }`}
            >
              [INPUT]
            </button>
            <button
              onClick={() => setActiveTab('output')}
              className={`px-3 py-1 text-xs font-medium uppercase tracking-wider border ${
                activeTab === 'output'
                  ? 'border-accent bg-surface text-accent'
                  : 'border-border bg-interactive text-text-secondary hover:text-text-primary'
              }`}
            >
              [OUTPUT]
            </button>
            {trace.decisionRationale && (
              <button
                onClick={() => setActiveTab('rationale')}
                className={`px-3 py-1 text-xs font-medium uppercase tracking-wider border ${
                  activeTab === 'rationale'
                    ? 'border-accent bg-surface text-accent'
                    : 'border-border bg-interactive text-text-secondary hover:text-text-primary'
                }`}
              >
                [RATIONALE]
              </button>
            )}
          </div>

          {/* Content */}
          <div className="bg-base border border-border p-4 font-mono text-xs overflow-x-auto max-h-96 overflow-y-auto">
            {activeTab === 'input' && (
              <JsonView data={trace.inputData} label="Model Input" />
            )}
            {activeTab === 'output' && (
              <JsonView data={trace.outputData} label="Model Output" />
            )}
            {activeTab === 'rationale' && trace.decisionRationale && (
              <div className="text-text-primary whitespace-pre-wrap">
                {trace.decisionRationale}
              </div>
            )}
          </div>
        </>
      )}
    </Panel>
  )
}

/**
 * JSON viewer with collapsible tree structure
 */
function JsonView({ data }: { data: unknown; label?: string }) {
  if (data === null || data === undefined) {
    return <span className="text-text-tertiary">null</span>
  }

  if (typeof data === 'string') {
    return <span className="text-accent">"{data}"</span>
  }

  if (typeof data === 'number' || typeof data === 'boolean') {
    return <span className="text-blue-400">{String(data)}</span>
  }

  if (Array.isArray(data)) {
    return (
      <details open className="ml-2">
        <summary className="cursor-pointer text-text-secondary hover:text-accent">
          Array[{data.length}]
        </summary>
        <div className="ml-4 mt-1 border-l border-border pl-2">
          {data.map((item, i) => (
            <div key={i} className="mb-1">
              <span className="text-text-tertiary">[{i}]: </span>
              <JsonView data={item} label={`${i}`} />
            </div>
          ))}
        </div>
      </details>
    )
  }

  if (typeof data === 'object') {
    const entries = Object.entries(data as Record<string, unknown>)
    return (
      <details open className="ml-2">
        <summary className="cursor-pointer text-text-secondary hover:text-accent">
          Object{'{'}...{'}'}
        </summary>
        <div className="ml-4 mt-1 border-l border-border pl-2">
          {entries.map(([key, value]) => (
            <div key={key} className="mb-1">
              <span className="text-text-primary">{key}: </span>
              <JsonView data={value} label={key} />
            </div>
          ))}
        </div>
      </details>
    )
  }

  return <span className="text-text-tertiary">Unknown type</span>
}
