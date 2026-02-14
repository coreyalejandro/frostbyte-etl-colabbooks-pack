// ISSUE #3, #17: Model Versions API Hook
// REASONING: TanStack Query hook for model provenance and version history
// ADDED BY: Kombai on 2026-02-14

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { ModelVersion, DeployModelRequest, RollbackModelRequest } from '../types/observability'
import { MOCK_MODEL_VERSIONS } from '../data/mockObservability'

/**
 * Fetch all model versions
 */
export function useModelVersions() {
  return useQuery({
    queryKey: ['model-versions'],
    queryFn: async (): Promise<ModelVersion[]> => {
      await new Promise(resolve => setTimeout(resolve, 300))
      return MOCK_MODEL_VERSIONS.sort((a, b) => 
        new Date(b.deployedAt).getTime() - new Date(a.deployedAt).getTime()
      )
    },
  })
}

/**
 * Fetch versions for a specific model
 */
export function useModelVersionHistory(modelName: string) {
  return useQuery({
    queryKey: ['model-versions', modelName],
    queryFn: async (): Promise<ModelVersion[]> => {
      await new Promise(resolve => setTimeout(resolve, 200))
      return MOCK_MODEL_VERSIONS
        .filter(v => v.modelName === modelName)
        .sort((a, b) => new Date(b.deployedAt).getTime() - new Date(a.deployedAt).getTime())
    },
  })
}

/**
 * Deploy a new model version
 * TODO: Implement real API call when backend ready
 */
export function useDeployModel() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (request: DeployModelRequest): Promise<ModelVersion> => {
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // Mock successful deployment
      const newVersion: ModelVersion = {
        id: `ver_${Date.now()}`,
        modelName: request.modelName,
        version: request.version,
        deployedAt: new Date().toISOString(),
        deployedBy: 'admin@frostbyte.io',
        configuration: request.configuration,
        isActive: true,
      }
      
      return newVersion
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['model-versions'] })
    },
  })
}

/**
 * Rollback to a previous model version
 * TODO: Implement real API call when backend ready
 */
export function useRollbackModel() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (_request: RollbackModelRequest): Promise<void> => {
      await new Promise(resolve => setTimeout(resolve, 500))
      // Mock rollback success
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['model-versions'] })
    },
  })
}
