// ISSUE #1, #6: Model Activity Monitor Component
// REASONING: Real-time visual feed of all model operations ("eyes on machines")
// ADDED BY: Kombai on 2026-02-14

import { useState } from 'react'
import Panel from '../../components/Panel'
import { useModelEvents, useModelEventStream } from '../../hooks/useModelEvents'
import type { ModelEvent, ModelEventFilters, ModelEventStatus } from '../../types/observability'

interface ModelActivityMonitorProps {
  /**
   * Optional filters to apply to the event feed
   */
  filters?: ModelEventFilters
  /**
   * Callback when an event is clicked for inspection
   */
  onEventClick?: (event: ModelEvent) => void
  /**
   * Max height for scrollable feed
   */
  maxHeight?: string
}

export default function ModelActivityMonitor({ 
  filters, 
  onEventClick,
  maxHeight = '500px' 
}: ModelActivityMonitorProps) {
  const [activeFilters, setActiveFilters] = useState<ModelEventFilters>(filters ?? {})
  const [useStream, setUseStream] = useState(false)
  
  // Fetch historical events
  const { data: historialEvents, isLoading } = useModelEvents(activeFilters)
  
  // Stream real-time events
  const { events: streamEvents, isConnected } = useModelEventStream(activeFilters)
  
  // Use stream events if enabled, otherwise use historical
  const events = useStream ? streamEvents : (historialEvents ?? [])

  const handleFilterChange = (key: keyof ModelEventFilters, value: string) => {
    setActiveFilters(prev => ({
      ...prev,
      [key]: value || undefined,
    }))
  }

  const clearFilters = () => {
    setActiveFilters({})
  }

  return (
    <Panel title="MODEL ACTIVITY MONITOR">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2 mb-4 pb-3 border-b border-border">
        {/* Stream Toggle */}
        <button
          onClick={() => setUseStream(!useStream)}
          className={`px-3 py-1 text-xs font-medium uppercase tracking-wider border ${
            useStream
              ? 'border-accent bg-surface text-accent'
              : 'border-border bg-interactive text-text-primary hover:bg-surface'
          }`}
          aria-label={useStream ? 'Disable live stream' : 'Enable live stream'}
        >
          {useStream ? '[LIVE STREAM ON]' : '[LIVE STREAM OFF]'}
        </button>

        {/* Connection Indicator */}
        {useStream && (
          <span 
            className="flex items-center gap-1 text-xs text-text-secondary"
            role="status"
            aria-live="polite"
          >
            <span className={isConnected ? 'text-accent' : 'text-inactive'}>●</span>
            {isConnected ? 'CONNECTED' : 'DISCONNECTED'}
          </span>
        )}

        {/* Filters */}
        <select
          value={activeFilters.stage ?? ''}
          onChange={(e) => handleFilterChange('stage', e.target.value)}
          className="px-2 py-1 text-xs bg-base border border-border text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
          aria-label="Filter by pipeline stage"
        >
          <option value="">ALL STAGES</option>
          <option value="parse">PARSE</option>
          <option value="embed">EMBED</option>
          <option value="verify">VERIFY</option>
          <option value="evidence">EVIDENCE</option>
        </select>

        <select
          value={activeFilters.status ?? ''}
          onChange={(e) => handleFilterChange('status', e.target.value)}
          className="px-2 py-1 text-xs bg-base border border-border text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
          aria-label="Filter by event status"
        >
          <option value="">ALL STATUS</option>
          <option value="processing">PROCESSING</option>
          <option value="completed">COMPLETED</option>
          <option value="failed">FAILED</option>
        </select>

        {(activeFilters.stage || activeFilters.status) && (
          <button
            onClick={clearFilters}
            className="px-2 py-1 text-xs text-text-secondary hover:text-accent border border-border hover:border-accent"
            aria-label="Clear all filters"
          >
            [CLEAR]
          </button>
        )}

        {isLoading && (
          <span className="text-xs text-text-tertiary ml-auto" aria-live="polite">
            LOADING...
          </span>
        )}
      </div>

      {/* Event Feed */}
      <div 
        className="space-y-2 overflow-y-auto"
        style={{ maxHeight }}
        role="log"
        aria-live="polite"
        aria-label="Model activity event feed"
      >
        {events.length === 0 && (
          <p className="text-sm text-text-tertiary text-center py-8">
            {isLoading ? 'LOADING EVENTS...' : 'NO EVENTS FOUND'}
          </p>
        )}

        {events.map((event) => (
          <ModelEventCard 
            key={event.id} 
            event={event} 
            onClick={() => onEventClick?.(event)}
          />
        ))}
      </div>

      {/* Footer Stats */}
      <div className="mt-4 pt-3 border-t border-border flex justify-between text-xs text-text-tertiary">
        <span>{events.length} EVENTS DISPLAYED</span>
        <span>
          LAST UPDATE: {events[0] ? new Date(events[0].timestamp).toLocaleTimeString() : '—'}
        </span>
      </div>
    </Panel>
  )
}

/**
 * Individual event card in the activity feed
 */
function ModelEventCard({ event, onClick }: { event: ModelEvent; onClick?: () => void }) {
  const getStatusColor = (status: ModelEventStatus) => {
    switch (status) {
      case 'completed': return 'text-accent border-accent/30'
      case 'failed': return 'text-red-400 border-red-400/30'
      case 'processing': return 'text-blue-400 border-blue-400/30'
      case 'started': return 'text-text-secondary border-border'
      default: return 'text-text-secondary border-border'
    }
  }

  const getStatusIcon = (status: ModelEventStatus) => {
    switch (status) {
      case 'completed': return '✓'
      case 'failed': return '✗'
      case 'processing': return '⟳'
      case 'started': return '○'
      default: return '—'
    }
  }

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2 border bg-surface hover:bg-interactive transition-colors ${getStatusColor(event.status)}`}
      style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)' }}
      aria-label={`View details for ${event.modelName} ${event.operation} event`}
    >
      <div className="flex items-start justify-between gap-3">
        {/* Left: Model Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium">
              {getStatusIcon(event.status)}
            </span>
            <span className="text-xs font-medium text-text-primary truncate">
              {event.modelName}
            </span>
            <span className="text-[10px] text-text-tertiary">
              v{event.modelVersion}
            </span>
            <span className="text-[10px] text-text-tertiary uppercase">
              [{event.stage}]
            </span>
          </div>
          
          <div className="text-xs text-text-secondary">
            <span className="font-mono">{event.operation}</span>
            {event.documentName && (
              <span className="ml-2">→ {event.documentName}</span>
            )}
          </div>

          {event.errorMessage && (
            <div className="text-xs text-red-400 mt-1 font-mono">
              ERROR: {event.errorMessage}
            </div>
          )}
        </div>

        {/* Right: Metrics */}
        <div className="text-right text-xs text-text-tertiary space-y-1">
          <div>{new Date(event.timestamp).toLocaleTimeString()}</div>
          {event.durationMs !== undefined && (
            <div className="font-mono">{event.durationMs}ms</div>
          )}
          {event.costUsd !== undefined && event.costUsd > 0 && (
            <div className="font-mono text-accent">${event.costUsd.toFixed(6)}</div>
          )}
        </div>
      </div>

      {/* Tokens */}
      {(event.inputTokens !== undefined || event.outputTokens !== undefined) && (
        <div className="mt-2 pt-2 border-t border-border/50 flex gap-3 text-[10px] text-text-tertiary font-mono">
          {event.inputTokens !== undefined && (
            <span>IN: {event.inputTokens.toLocaleString()} tokens</span>
          )}
          {event.outputTokens !== undefined && (
            <span>OUT: {event.outputTokens.toLocaleString()} tokens</span>
          )}
        </div>
      )}
    </button>
  )
}
