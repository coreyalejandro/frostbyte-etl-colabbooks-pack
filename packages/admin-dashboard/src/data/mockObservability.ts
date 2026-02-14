// ISSUE #1-10: Mock Observability Data
// REASONING: Realistic test data for observability components matching backend schema
// ADDED BY: Kombai on 2026-02-14

import type { ModelEvent, DecisionTrace, ModelVersion, ModelMetrics } from '../types/observability'

/**
 * Mock model events for testing Activity Monitor
 */
export const MOCK_MODEL_EVENTS: ModelEvent[] = [
  {
    id: 'evt_001',
    timestamp: new Date(Date.now() - 5000).toISOString(),
    tenantId: 'PROD-01',
    documentId: 'doc_0001',
    documentName: 'contract.pdf',
    stage: 'embed',
    modelName: 'nomic-embed-text-v1',
    modelVersion: '1.5.0',
    operation: 'embed_chunks',
    status: 'processing',
    inputTokens: 8192,
  },
  {
    id: 'evt_002',
    timestamp: new Date(Date.now() - 12000).toISOString(),
    tenantId: 'PROD-01',
    documentId: 'doc_0002',
    documentName: 'appendix.md',
    stage: 'parse',
    modelName: 'docling',
    modelVersion: '2.7.0',
    operation: 'extract_text',
    status: 'completed',
    durationMs: 3450,
    inputTokens: 0,
    outputTokens: 2048,
    costUsd: 0.0,
  },
  {
    id: 'evt_003',
    timestamp: new Date(Date.now() - 18000).toISOString(),
    tenantId: 'PROD-02',
    documentId: 'doc_0003',
    documentName: 'policy.docx',
    stage: 'verify',
    modelName: 'policy-classifier',
    modelVersion: '1.2.3',
    operation: 'classify_content',
    status: 'failed',
    durationMs: 1250,
    errorMessage: 'Confidence threshold not met: 0.42 < 0.50',
  },
  {
    id: 'evt_004',
    timestamp: new Date(Date.now() - 25000).toISOString(),
    tenantId: 'PROD-01',
    documentId: 'doc_0001',
    documentName: 'contract.pdf',
    stage: 'parse',
    modelName: 'docling',
    modelVersion: '2.7.0',
    operation: 'extract_text',
    status: 'completed',
    durationMs: 4120,
    outputTokens: 12288,
    costUsd: 0.0,
  },
  {
    id: 'evt_005',
    timestamp: new Date(Date.now() - 32000).toISOString(),
    tenantId: 'PROD-01',
    documentId: 'doc_0004',
    documentName: 'terms_of_service.pdf',
    stage: 'embed',
    modelName: 'nomic-embed-text-v1',
    modelVersion: '1.5.0',
    operation: 'embed_chunks',
    status: 'completed',
    durationMs: 2890,
    inputTokens: 6144,
    outputTokens: 768,
    costUsd: 0.00012,
  },
]

/**
 * Mock decision traces for testing Decision Tracer
 */
export const MOCK_DECISION_TRACES: DecisionTrace[] = [
  {
    id: 'trace_001',
    eventId: 'evt_002',
    inputData: {
      document_path: '/uploads/appendix.md',
      options: {
        extract_tables: true,
        preserve_formatting: true,
      },
    },
    outputData: {
      text_chunks: 42,
      total_tokens: 2048,
      tables_found: 3,
      metadata: {
        language: 'en',
        encoding: 'utf-8',
      },
    },
    decisionRationale: 'Document parsed successfully with table extraction enabled',
    confidenceScore: 0.99,
  },
  {
    id: 'trace_002',
    eventId: 'evt_003',
    inputData: {
      text: 'Policy document content excerpt...',
      classification_threshold: 0.5,
    },
    outputData: {
      classification: 'legal_policy',
      confidence: 0.42,
      rejected: true,
    },
    decisionRationale: 'Classification confidence 0.42 below required threshold 0.50',
    confidenceScore: 0.42,
  },
]

/**
 * Mock model versions for testing Provenance Timeline
 */
export const MOCK_MODEL_VERSIONS: ModelVersion[] = [
  {
    id: 'ver_001',
    modelName: 'docling',
    version: '2.7.0',
    deployedAt: new Date(Date.now() - 86400000 * 7).toISOString(),
    deployedBy: 'admin@frostbyte.io',
    configuration: {
      max_chunk_size: 512,
      overlap_tokens: 50,
      extract_tables: true,
    },
    isActive: true,
  },
  {
    id: 'ver_002',
    modelName: 'docling',
    version: '2.6.1',
    deployedAt: new Date(Date.now() - 86400000 * 30).toISOString(),
    deployedBy: 'admin@frostbyte.io',
    configuration: {
      max_chunk_size: 512,
      overlap_tokens: 50,
      extract_tables: false,
    },
    isActive: false,
  },
  {
    id: 'ver_003',
    modelName: 'nomic-embed-text-v1',
    version: '1.5.0',
    deployedAt: new Date(Date.now() - 86400000 * 14).toISOString(),
    deployedBy: 'ml-ops@frostbyte.io',
    configuration: {
      dimension: 768,
      context_length: 8192,
      batch_size: 32,
    },
    isActive: true,
  },
  {
    id: 'ver_004',
    modelName: 'policy-classifier',
    version: '1.2.3',
    deployedAt: new Date(Date.now() - 86400000 * 3).toISOString(),
    deployedBy: 'ml-ops@frostbyte.io',
    configuration: {
      confidence_threshold: 0.5,
      num_classes: 12,
    },
    isActive: true,
  },
]

/**
 * Mock model metrics for testing performance dashboards
 */
export const MOCK_MODEL_METRICS: ModelMetrics[] = [
  {
    modelName: 'docling',
    modelVersion: '2.7.0',
    totalInvocations: 1247,
    successRate: 0.987,
    avgDurationMs: 3850,
    avgCostUsd: 0.0,
    totalCostUsd: 0.0,
    lastInvocation: new Date(Date.now() - 12000).toISOString(),
  },
  {
    modelName: 'nomic-embed-text-v1',
    modelVersion: '1.5.0',
    totalInvocations: 892,
    successRate: 0.998,
    avgDurationMs: 2650,
    avgCostUsd: 0.00015,
    totalCostUsd: 0.1338,
    lastInvocation: new Date(Date.now() - 5000).toISOString(),
  },
  {
    modelName: 'policy-classifier',
    modelVersion: '1.2.3',
    totalInvocations: 156,
    successRate: 0.923,
    avgDurationMs: 1180,
    avgCostUsd: 0.00008,
    totalCostUsd: 0.0125,
    lastInvocation: new Date(Date.now() - 18000).toISOString(),
  },
]
