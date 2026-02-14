// PRIORITY 1: Extreme Observability - Decision Tracer
// Interactive inspection of model inputs/outputs for compliance

import { useState } from 'react'
import Panel from '../../components/Panel'

interface DecisionTrace {
  id: string
  eventId: string
  timestamp: string
  modelName: string
  modelVersion: string
  stage: string
  documentId: string
  input: unknown
  output: unknown
  rationale?: string
  confidence?: number
  latencyMs: number
  costUsd?: number
}

interface DecisionTracerProps {
  trace?: DecisionTrace
  onClose?: () => void
}

export default function DecisionTracer({ trace, onClose }: DecisionTracerProps) {
  const [activeTab, setActiveTab] = useState<'input' | 'output' | 'comparison'>('comparison')
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set()))

  if (!trace) {
    return (
      <Panel title="DECISION TRACER">
        <div className="text-center py-12 text-text-tertiary">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-accent/10 flex items-center justify-center">
            <span className="text-2xl text-accent">🔍</span>
          </div>
          <p className="text-sm">Select a model event from the Activity Monitor<br/>to inspect inputs, outputs, and decision rationale.</p>
        </div>
      </Panel>
    )
  }

  const toggleSection = (section: string) => {
    const newSet = new Set(expandedSections)
    if (newSet.has(section)) {
      newSet.delete(section)
    } else {
      newSet.add(section)
    }
    setExpandedSections(newSet)
  }

  const renderJsonTree = (data: unknown, path = '', depth = 0): React.ReactNode => {
    if (data === null) return <span className="text-text-tertiary">null</span>
    if (typeof data === 'undefined') return <span className="text-text-tertiary">undefined</span>
    if (typeof data === 'string') return <span className="text-green-400">"{data}"</span>
    if (typeof data === 'number') return <span className="text-blue-400">{data}</span>
    if (typeof data === 'boolean') return <span className="text-accent">{data.toString()}</span>

    if (Array.isArray(data)) {
      const isExpanded = expandedSections.has(path)
      return (
        <div className={`pl-${depth * 2}`}>
          <button
            onClick={() => toggleSection(path)}
            className="text-text-secondary hover:text-accent flex items-center gap-1"
          >
            <span>{isExpanded ? '▼' : '▶'}</span>
            <span className="text-text-tertiary">Array({data.length})</span>
          </button>
          {isExpanded && (
            <div className="pl-4 border-l border-border ml-1">
              {data.map((item, i) => (
                <div key={i} className="py-0.5">
                  <span className="text-text-tertiary mr-2">{i}:</span>
                  {renderJsonTree(item, `${path}[${i}]`, depth + 1)}
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

    if (typeof data === 'object') {
      const obj = data as Record<string, unknown>
      const keys = Object.keys(obj)
      const isExpanded = expandedSections.has(path) || depth < 2
      
      return (
        <div className={`pl-${depth * 2}`}>
          <button
            onClick={() => toggleSection(path)}
            className="text-text-secondary hover:text-accent flex items-center gap-1"
          >
            <span>{isExpanded ? '▼' : '▶'}</span>
            <span className="text-text-tertiary">{'{}'}</span>
          </button>
          {isExpanded && (
            <div className="pl-4 border-l border-border ml-1">
              {keys.map((key) => (
                <div key={key} className="py-0.5">
                  <span className="text-accent mr-2">"{key}"</span>
                  <span className="text-text-tertiary">:</span>
                  {renderJsonTree(obj[key], `${path}.${key}`, depth + 1)}
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

    return null
  }

  return (
    <Panel title="DECISION TRACER">
      {/* Header */}
      <div className="flex items-start justify-between mb-4 pb-3 border-b border-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-accent">{trace.modelName}</span>
            <span className="text-[10px] text-text-tertiary">v{trace.modelVersion}</span>
            <span className="text-[10px] text-text-tertiary uppercase">[{trace.stage}]</span>
          </div>
          <div className="text-[10px] text-text-secondary">
            {new Date(trace.timestamp).toLocaleString()} · Document: {trace.documentId}
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary px-2 py-1"
            aria-label="Close tracer"
          >
            ✕
          </button>
        )}
      </div>

      {/* Metrics */}
      <div className="flex gap-4 mb-4 text-xs">
        <div className="px-2 py-1 bg-surface-elevated rounded">
          <span className="text-text-tertiary">Latency: </span>
          <span className="text-text-primary font-mono">{trace.latencyMs}ms</span>
        </div>
        {trace.costUsd !== undefined && (
          <div className="px-2 py-1 bg-surface-elevated rounded">
            <span className="text-text-tertiary">Cost: </span>
            <span className="text-accent font-mono">${trace.costUsd.toFixed(6)}</span>
          </div>
        )}
        {trace.confidence !== undefined && (
          <div className="px-2 py-1 bg-surface-elevated rounded">
            <span className="text-text-tertiary">Confidence: </span>
            <span className={trace.confidence >= 0.7 ? 'text-green-400' : 'text-red-400'}>
              {(trace.confidence * 100).toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      {/* Rationale */}
      {trace.rationale && (
        <div className="mb-4 p-3 bg-accent/5 border border-accent/20 rounded">
          <div className="text-[10px] uppercase tracking-wider text-accent mb-1">Decision Rationale</div>
          <p className="text-sm text-text-secondary">{trace.rationale}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-3 border-b border-border">
        {(['comparison', 'input', 'output'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-1.5 text-xs font-medium uppercase tracking-wider transition-colors ${
              activeTab === tab
                ? 'text-accent border-b-2 border-accent'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="bg-surface-elevated rounded p-3 font-mono text-xs overflow-auto max-h-80">
        {activeTab === 'comparison' && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-text-tertiary mb-2">Input</div>
              <div className="text-text-secondary">
                {renderJsonTree(trace.input, 'input')}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-text-tertiary mb-2">Output</div>
              <div className="text-text-secondary">
                {renderJsonTree(trace.output, 'output')}
              </div>
            </div>
          </div>
        )}
        {activeTab === 'input' && (
          <div className="text-text-secondary">
            {renderJsonTree(trace.input, 'input')}
          </div>
        )}
        {activeTab === 'output' && (
          <div className="text-text-secondary">
            {renderJsonTree(trace.output, 'output')}
          </div>
        )}
      </div>

      {/* Audit Link */}
      <div className="mt-4 text-xs text-text-tertiary">
        <span>Full audit trail: </span>
        <a
          href={`/audit?event=${trace.eventId}`}
          className="text-accent hover:underline"
        >
          View in Audit Gallery →
        </a>
      </div>
    </Panel>
  )
}
