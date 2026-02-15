import type { Node, Edge } from '@xyflow/react'

export interface PipelineNodeData extends Record<string, unknown> {
  label: string
  description: string
  status: 'healthy' | 'processing' | 'error' | 'idle'
  throughput: number
  model?: { name: string; version: string }
}

const NODE_WIDTH = 140
const NODE_GAP = 60

const STAGE_MODELS: Record<string, { name: string; version: string }> = {
  parse: { name: 'docling', version: '2.7.0' },
  embed: { name: 'nomic-embed-text-v1', version: '1.5.0' },
  verify: { name: 'policy-classifier', version: '1.2.3' },
}

export const PIPELINE_STAGES = [
  { id: 'intake', label: 'INTAKE', description: 'upload' },
  { id: 'parse', label: 'PARSE', description: 'extract text' },
  { id: 'evidence', label: 'EVIDENCE', description: 'verify' },
  { id: 'embed', label: 'EMBED', description: 'vectorize' },
  { id: 'vector', label: 'VECTOR', description: 'store' },
  { id: 'metadata', label: 'METADATA', description: 'index' },
  { id: 'verify', label: 'VERIFY', description: 'validate' },
] as const

export function createPipelineNodes(
  nodeStatuses?: Record<string, { status: string; throughput: number }>,
): Node<PipelineNodeData>[] {
  return PIPELINE_STAGES.map((stage, i) => ({
    id: stage.id,
    type: 'pipelineNode',
    position: { x: i * (NODE_WIDTH + NODE_GAP), y: 0 },
    draggable: false,
    data: {
      label: stage.label,
      description: stage.description,
      status: (nodeStatuses?.[stage.id]?.status as PipelineNodeData['status']) ?? 'healthy',
      throughput: nodeStatuses?.[stage.id]?.throughput ?? 0,
      model: STAGE_MODELS[stage.id],
    },
  }))
}

export function createPipelineEdges(activeNodeIds?: Set<string>): Edge[] {
  return PIPELINE_STAGES.slice(0, -1).map((stage, i) => {
    const nextStage = PIPELINE_STAGES[i + 1]
    const isActive = activeNodeIds?.has(stage.id) ?? true
    return {
      id: `${stage.id}-${nextStage.id}`,
      source: stage.id,
      target: nextStage.id,
      type: 'pipelineEdge',
      data: { active: isActive },
    }
  })
}
