import { useState } from 'react'
import { usePipelineStore } from '../../stores/pipelineStore'
import Inspector from '../../components/Inspector'
import Panel from '../../components/Panel'
import PipelineLogStream from './PipelineLogStream'

export default function PipelineSchematic() {
  const { nodes } = usePipelineStore()
  const [inspectorNode, setInspectorNode] = useState<string | null>(null)

  const chain: { ts: string; op: string; ok: boolean }[] = [
    { ts: '2026-02-12 14:03:22', op: 'UPLOAD', ok: true },
    { ts: '2026-02-12 14:03:25', op: 'PARSE', ok: true },
    { ts: '2026-02-12 14:03:28', op: 'SIGN', ok: true },
  ]

  return (
    <>
      <Panel title="PIPELINE SCHEMATIC">
        <div className="flex flex-wrap items-center gap-2 font-mono text-sm">
          {nodes.map((node, i) => (
            <span key={node.id} className="flex items-center gap-2">
              <button
                onClick={() => setInspectorNode(node.id)}
                className={`px-2 py-1 border flex flex-col items-center min-w-[5rem] ${
                  node.active ? 'border-accent bg-surface text-accent' : 'border-border bg-surface text-text-primary'
                }`}
              >
                <span>[{node.label}]</span>
                <span className="text-[10px] text-text-tertiary mt-0.5 lowercase tracking-wide">
                  {node.desc}
                </span>
              </button>
              {i < nodes.length - 1 && (
                <span className={node.active ? 'text-accent' : 'text-border'}>
                  ────►
                </span>
              )}
            </span>
          ))}
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
