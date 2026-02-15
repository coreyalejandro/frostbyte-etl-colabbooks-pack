import { useCallback, useMemo, useState } from 'react'
import { ReactFlow, Background, type NodeMouseHandler } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { usePipelineStore } from '../../stores/pipelineStore'
import Inspector from '../Inspector'
import PipelineNodeComponent from './PipelineNode'
import PipelineEdgeComponent from './PipelineEdge'
import { createPipelineNodes, createPipelineEdges } from './pipelineLayout'

const nodeTypes = { pipelineNode: PipelineNodeComponent }
const edgeTypes = { pipelineEdge: PipelineEdgeComponent }

interface PipelineDAGProps {
  tenantId?: string
}

export default function PipelineDAG({ tenantId: _tenantId }: PipelineDAGProps) {
  const { nodes: storeNodes } = usePipelineStore()
  const [inspectorNode, setInspectorNode] = useState<string | null>(null)

  const nodeStatuses = useMemo(() => {
    const statuses: Record<string, { status: string; throughput: number }> = {}
    for (const node of storeNodes) {
      statuses[node.id] = {
        status: node.active ? 'healthy' : 'idle',
        throughput: node.active ? Math.floor(100 + Math.random() * 50) : 0,
      }
    }
    return statuses
  }, [storeNodes])

  const nodes = useMemo(() => createPipelineNodes(nodeStatuses), [nodeStatuses])
  const activeNodeIds = useMemo(
    () => new Set(storeNodes.filter((n) => n.active).map((n) => n.id)),
    [storeNodes],
  )
  const edges = useMemo(() => createPipelineEdges(activeNodeIds), [activeNodeIds])

  const onNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    setInspectorNode(node.id)
  }, [])

  const chain = [
    { ts: '2026-02-12 14:03:22', op: 'UPLOAD', ok: true },
    { ts: '2026-02-12 14:03:25', op: 'PARSE', ok: true },
    { ts: '2026-02-12 14:03:28', op: 'SIGN', ok: true },
  ]

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
