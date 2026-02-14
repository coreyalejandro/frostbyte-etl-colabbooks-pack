// ISSUE #1-10: Model Observatory Page
// REASONING: Unified page showing all model observability components
// ADDED BY: Kombai on 2026-02-14

import { useState } from 'react'
import ModelActivityMonitor from '../features/observability/ModelActivityMonitor'
import DecisionTracer from '../features/observability/DecisionTracer'
import ProvenanceTimeline from '../features/observability/ProvenanceTimeline'
import type { ModelEvent } from '../types/observability'

export default function Observatory() {
  const [selectedEvent, setSelectedEvent] = useState<ModelEvent | null>(null)

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary">
            MODEL OBSERVATORY
          </h2>
          <p className="text-xs text-text-tertiary mt-1">
            Real-time visibility into all AI model operations — "Eyes on machines at all times"
          </p>
        </div>
      </div>

      {/* Top Row: Activity Monitor + Decision Tracer */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ModelActivityMonitor 
          onEventClick={setSelectedEvent}
          maxHeight="600px"
        />
        
        <DecisionTracer 
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      </div>

      {/* Bottom Row: Provenance Timeline */}
      <ProvenanceTimeline allowRollback={true} />
    </div>
  )
}
