import { useState } from 'react'
import { usePipelineStore } from '../../stores/pipelineStore'
import Inspector from '../../components/Inspector'
import Panel from '../../components/Panel'

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
                className={`px-2 py-1 border ${
                  node.active ? 'border-accent bg-surface text-accent' : 'border-border bg-surface text-text-primary'
                }`}
              >
                [{node.label}]
              </button>
              {i < nodes.length - 1 && (
                <span className={node.active ? 'text-accent' : 'text-border'}>
                  ────►
                </span>
              )}
            </span>
          ))}
        </div>
        <div className="mt-2 text-xs text-text-tertiary">
          └──► [VERIFY]
        </div>
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
