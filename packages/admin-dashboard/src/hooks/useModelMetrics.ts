// ISSUE #4, #10: Model Metrics API Hook
// REASONING: TanStack Query hook for model performance and cost metrics
// ADDED BY: Kombai on 2026-02-14

import { useQuery } from '@tanstack/react-query'
import type { ModelMetrics } from '../types/observability'
import { MOCK_MODEL_METRICS } from '../data/mockObservability'

/**
 * Fetch aggregated metrics for all models
 */
export function useModelMetrics() {
  return useQuery({
    queryKey: ['model-metrics'],
    queryFn: async (): Promise<ModelMetrics[]> => {
      await new Promise(resolve => setTimeout(resolve, 300))
      return MOCK_MODEL_METRICS
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  })
}

/**
 * Fetch metrics for a specific model
 */
export function useModelMetric(modelName: string) {
  return useQuery({
    queryKey: ['model-metrics', modelName],
    queryFn: async (): Promise<ModelMetrics | null> => {
      await new Promise(resolve => setTimeout(resolve, 200))
      return MOCK_MODEL_METRICS.find(m => m.modelName === modelName) ?? null
    },
    refetchInterval: 10000,
  })
}
