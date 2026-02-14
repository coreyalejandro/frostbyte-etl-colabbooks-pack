// ISSUE #2, #7: Decision Traces API Hook
// REASONING: TanStack Query hook for fetching model decision traces
// ADDED BY: Kombai on 2026-02-14

import { useQuery } from '@tanstack/react-query'
import type { DecisionTrace } from '../types/observability'
import { MOCK_DECISION_TRACES } from '../data/mockObservability'

/**
 * Fetch decision trace by event ID
 * Shows input/output for model transparency
 * TODO: Replace mock data with real API call when backend ready
 */
export function useDecisionTrace(eventId: string | null) {
  return useQuery({
    queryKey: ['decision-trace', eventId],
    queryFn: async (): Promise<DecisionTrace | null> => {
      if (!eventId) return null
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 200))
      
      return MOCK_DECISION_TRACES.find(t => t.eventId === eventId) ?? null
    },
    enabled: !!eventId,
  })
}

/**
 * Fetch all decision traces (for administrative review)
 */
export function useDecisionTraces() {
  return useQuery({
    queryKey: ['decision-traces'],
    queryFn: async (): Promise<DecisionTrace[]> => {
      await new Promise(resolve => setTimeout(resolve, 300))
      return MOCK_DECISION_TRACES
    },
  })
}
