// ISSUE #1-10: Model Observability Types
// REASONING: Define TypeScript interfaces matching backend schema from PRD
// ADDED BY: Kombai on 2026-02-14

/**
 * Model event status representing lifecycle states
 */
export type ModelEventStatus = 'started' | 'processing' | 'completed' | 'failed'

/**
 * Pipeline stages where models operate
 */
export type PipelineStage = 'intake' | 'parse' | 'evidence' | 'embed' | 'vector' | 'metadata' | 'verify'

/**
 * Model types in the Frostbyte pipeline
 */
export type ModelType = 'parser' | 'embedder' | 'policy'

/**
 * Real-time model activity event streamed via SSE
 * Matches backend schema: model_events table
 */
export interface ModelEvent {
  id: string
  timestamp: string
  tenantId: string
  documentId: string
  documentName?: string
  stage: PipelineStage
  modelName: string
  modelVersion: string
  operation: string
  status: ModelEventStatus
  durationMs?: number
  inputTokens?: number
  outputTokens?: number
  costUsd?: number
  errorMessage?: string
  metadata?: Record<string, unknown>
}

/**
 * Decision trace with input/output for model transparency
 * Matches backend schema: decision_traces table
 */
export interface DecisionTrace {
  id: string
  eventId: string
  event?: ModelEvent // Populated when joined
  inputData: unknown
  outputData: unknown
  decisionRationale?: string
  confidenceScore?: number
}

/**
 * Model version deployment record
 * Matches backend schema: model_versions table
 */
export interface ModelVersion {
  id: string
  modelName: string
  version: string
  deployedAt: string
  deployedBy: string
  configuration: Record<string, unknown>
  isActive: boolean
}

/**
 * Aggregated model performance metrics
 */
export interface ModelMetrics {
  modelName: string
  modelVersion: string
  totalInvocations: number
  successRate: number
  avgDurationMs: number
  avgCostUsd: number
  totalCostUsd: number
  lastInvocation: string
}

/**
 * SSE event payload for real-time streaming
 */
export interface ModelEventSSE {
  type: 'model_event' | 'model_metric' | 'model_alert'
  data: ModelEvent | ModelMetrics | { message: string; severity: 'info' | 'warning' | 'error' }
  timestamp: string
}

/**
 * Filters for model activity queries
 */
export interface ModelEventFilters {
  tenantId?: string
  documentId?: string
  stage?: PipelineStage
  modelName?: string
  status?: ModelEventStatus
  startDate?: string
  endDate?: string
  limit?: number
  offset?: number
}

/**
 * Model deployment request
 */
export interface DeployModelRequest {
  modelName: string
  version: string
  configuration: Record<string, unknown>
}

/**
 * Rollback request for model version
 */
export interface RollbackModelRequest {
  modelName: string
  targetVersion: string
}
