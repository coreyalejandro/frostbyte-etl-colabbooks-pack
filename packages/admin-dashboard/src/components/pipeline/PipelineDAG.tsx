import { useCallback, useMemo, useState } from 'react'
import { ReactFlow, Background, type NodeMouseHandler } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { usePipelineStore } from '../../stores/pipelineStore'
import { api } from '../../api/client'
import Inspector from '../Inspector'
import PipelineNodeComponent from './PipelineNode'
import PipelineEdgeComponent from './PipelineEdge'
import { createPipelineNodes, createPipelineEdges } from './pipelineLayout'

const nodeTypes = { pipelineNode: PipelineNodeComponent }
const edgeTypes = { pipelineEdge: PipelineEdgeComponent }

interface PipelineDAGProps {
  tenantId?: string
}

export default function PipelineDAG({ tenantId }: PipelineDAGProps) {
  const { nodes: storeNodes, nodeThroughput } = usePipelineStore()
  const [inspectorNode, setInspectorNode] = useState<string | null>(null)
  const [chain, setChain] = useState<Array<{ ts: string; op: string; ok: boolean }>>([])

  const nodeStatuses = useMemo(() => {
    const statuses: Record<string, { status: string; throughput: number }> = {}
    for (const node of storeNodes) {
      statuses[node.id] = {
        status: node.active ? 'healthy' : 'idle',
        throughput: nodeThroughput[node.id] ?? 0,
      }
    }
    return statuses
  }, [storeNodes, nodeThroughput])

  const filteredNodes = useMemo(() => {
    if (!tenantId) return storeNodes
    return storeNodes.map((node) => ({
      ...node,
      active: node.active,
    }))
  }, [storeNodes, tenantId])

  const nodes = useMemo(() => createPipelineNodes(nodeStatuses), [nodeStatuses])
  const activeNodeIds = useMemo(
    () => new Set(filteredNodes.filter((n) => n.active).map((n) => n.id)),
    [filteredNodes],
  )
  const edges = useMemo(() => createPipelineEdges(activeNodeIds), [activeNodeIds])

  const onNodeClick: NodeMouseHandler = useCallback(async (_event, node) => {
    setInspectorNode(node.id)
    try {
      const chainData = await api.getDocumentChain('0001')
      setChain(
        chainData.map((step) => ({
          ts: step.timestamp,
          op: step.operation,
          ok: step.verified,
        })),
      )
    } catch {
      setChain([])
    }
  }, [])

  return (
    <>
      <div className="w-full h-64 bg-base border border-border">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          proOptions={{ hideAttribution: true }}
          minZoom={0.5}
          maxZoom={2}
        >
          <Background color="#3c4045" gap={20} size={1} />
        </ReactFlow>
      </div>

      {inspectorNode && (
        <Inspector
          title={storeNodes.find((n) => n.id === inspectorNode)?.label ?? inspectorNode}
          chain={chain}
          onClose={() => setInspectorNode(null)}
        />
      )}
    </>
  )
}
