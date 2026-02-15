import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { PipelineNodeData } from './pipelineLayout'

const STATUS_STYLES: Record<string, string> = {
  healthy: 'bg-green-400',
  processing: 'bg-accent animate-pulse',
  error: 'bg-red-400',
  idle: 'bg-inactive',
}

function PipelineNodeComponent({ data }: NodeProps) {
  const nodeData = data as unknown as PipelineNodeData
  const statusClass = STATUS_STYLES[nodeData.status] ?? STATUS_STYLES.idle

  return (
    <>
      <Handle type="target" position={Position.Left} className="!bg-border !border-0 !w-2 !h-2" />
      <div className="bg-surface border border-border px-3 py-2 min-w-[8.5rem] font-mono select-none">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium uppercase tracking-wider text-text-primary">
            [{nodeData.label}]
          </span>
          <span className={`w-2 h-2 ${statusClass}`} title={nodeData.status} />
        </div>
        <span className="text-[10px] text-text-tertiary lowercase tracking-wide block">
          {nodeData.description}
        </span>
        {nodeData.throughput > 0 && (
          <span className="text-[10px] text-accent mt-1 block">
            {nodeData.throughput} docs/s
          </span>
        )}
        {nodeData.model && (
          <span className="text-[9px] text-text-tertiary mt-1 block">
            {nodeData.model.name}
          </span>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-border !border-0 !w-2 !h-2" />
    </>
  )
}

export default memo(PipelineNodeComponent)
