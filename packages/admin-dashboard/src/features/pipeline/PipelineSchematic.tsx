// ISSUE #1, #4: Enhanced Pipeline Schematic with Model Visibility
// REASONING: Show model identity and live status at each pipeline stage
// ADDED BY: Kombai on 2026-02-14

import { useState } from 'react'
import { usePipelineStore } from '../../stores/pipelineStore'
import Inspector from '../../components/Inspector'
import Panel from '../../components/Panel'
import PipelineLogStream from './PipelineLogStream'
import { useModelEvents } from '../../hooks/useModelEvents'

// Map pipeline stages to their associated models
const STAGE_MODELS: Record<string, { name: string; version: string }> = {
  parse: { name: 'docling', version: '2.7.0' },
  embed: { name: 'nomic-embed-text-v1', version: '1.5.0' },
  verify: { name: 'policy-classifier', version: '1.2.3' },
}

export default function PipelineSchematic() {
  const { nodes } = usePipelineStore()
  const [inspectorNode, setInspectorNode] = useState<string | null>(null)
  const { data: recentEvents } = useModelEvents({ limit: 10 })

  // Get latest event for each stage to show live status
  const getStageStatus = (stageId: string) => {
    const latestEvent = recentEvents?.find(e => e.stage === stageId)
    return latestEvent?.status ?? 'idle'
  }

  const chain: { ts: string; op: string; ok: boolean }[] = [
    { ts: '2026-02-12 14:03:22', op: 'UPLOAD', ok: true },
    { ts: '2026-02-12 14:03:25', op: 'PARSE', ok: true },
    { ts: '2026-02-12 14:03:28', op: 'SIGN', ok: true },
  ]

  return (
    <>
      <Panel title="PIPELINE SCHEMATIC — MODEL OBSERVATORY">
        <div className="flex flex-wrap items-center gap-2 font-mono text-sm">
          {nodes.map((node, i) => {
            const model = STAGE_MODELS[node.id]
            const status = getStageStatus(node.id)
            const statusColor = 
              status === 'processing' ? 'text-blue-400' :
              status === 'completed' ? 'text-accent' :
              status === 'failed' ? 'text-red-400' :
              'text-text-tertiary'
            
            return (
              <span key={node.id} className="flex items-center gap-2">
                <button
                  onClick={() => setInspectorNode(node.id)}
                  className={`px-2 py-1 border flex flex-col items-center min-w-[6rem] relative ${
                    node.active ? 'border-accent bg-surface text-accent' : 'border-border bg-surface text-text-primary'
                  }`}
                  aria-label={`View ${node.label} stage details${model ? ` using ${model.name}` : ''}`}
                >
                  {/* Live status indicator */}
                  {model && (
                    <span 
                      className={`absolute top-1 right-1 w-1.5 h-1.5 rounded-full ${statusColor}`}
                      title={status}
                      aria-hidden="true"
                    />
                  )}
                  
                  <span>[{node.label}]</span>
                  <span className="text-[10px] text-text-tertiary mt-0.5 lowercase tracking-wide">
                    {node.desc}
                  </span>
                  
                  {/* Model identity */}
                  {model && (
                    <span className="text-[9px] text-text-tertiary mt-1 font-mono">
                      {model.name.split('-')[0]}
                    </span>
                  )}
                </button>
                {i < nodes.length - 1 && (
                  <span className={node.active ? 'text-accent' : 'text-border'}>
                    ────►
                  </span>
                )}
              </span>
            )
          })}
        </div>
        <PipelineLogStream />
      </Panel>

      {inspectorNode && (
        <Inspector
          title={nodes.find((n) => n.id === inspectorNode)?.label ?? inspectorNode}
          chain={chain}
          onClose={() => setInspectorNode(null)}
        />
      )}
    </>
  )
}
