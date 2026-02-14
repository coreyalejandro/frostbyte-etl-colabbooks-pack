import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePipelineStore } from '../../stores/pipelineStore'
import Panel from '../../components/Panel'
import Inspector from '../../components/Inspector'

export default function DocumentQueue() {
  const { documents, moveDocument } = usePipelineStore()
  const [inspectorDoc, setInspectorDoc] = useState<string | null>(null)
  const navigate = useNavigate()

  const chain = [
    { ts: '2026-02-12 14:03:22', op: 'UPLOAD', ok: true },
    { ts: '2026-02-12 14:03:25', op: 'PARSE', ok: true },
    { ts: '2026-02-12 14:03:28', op: 'SIGN', ok: true },
  ]

  return (
    <>
      <Panel title="DOCUMENT QUEUE">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-surface">
                <th className="border border-border px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
                  ID
                </th>
                <th className="border border-border px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
                  NAME
                </th>
                <th className="border border-border px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
                  SIZE
                </th>
                <th className="border border-border px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
                  STATUS
                </th>
                <th className="border border-border px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
                  VERIFICATION
                </th>
                <th className="border border-border px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
                  ACTIONS
                </th>
              </tr>
            </thead>
            <tbody>
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="border border-border px-3 py-8 text-center text-inactive">
                    — NO DOCUMENTS —
                  </td>
                </tr>
              ) : (
                documents.map((d, i) => (
                <tr
                  key={d.id}
                  className={`hover:bg-interactive ${d.status === 'FAILED' ? 'border-l-2 border-l-accent' : ''}`}
                >
                  <td className="border border-border px-3 py-2 text-text-primary font-mono">
                    {d.id}
                  </td>
                  <td className="border border-border px-3 py-2 text-text-primary">
                    {d.name}
                  </td>
                  <td className="border border-border px-3 py-2 text-text-primary">
                    {d.size}
                  </td>
                  <td
                    className={`border border-border px-3 py-2 font-mono ${
                      d.status === 'FAILED' ? 'text-red-400' : 'text-text-primary'
                    }`}
                  >
                    {d.status}
                  </td>
                  <td className="border border-border px-3 py-2 text-text-primary font-mono">
                    {d.verification.toFixed(2)}
                  </td>
                  <td className="border border-border px-3 py-2">
                    <div className="flex gap-1">
                      <button
                        onClick={() => moveDocument(d.id, 'up')}
                        disabled={i === 0}
                        className="px-2 py-0 border border-border text-text-secondary disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        [↑]
                      </button>
                      <button
                        onClick={() => moveDocument(d.id, 'down')}
                        disabled={i === documents.length - 1}
                        className="px-2 py-0 border border-border text-text-secondary disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        [↓]
                      </button>
                      <button
                        onClick={() => navigate(`/documents/${d.id}`)}
                        className="px-2 py-0 border border-border text-text-secondary"
                      >
                        [VERIFY]
                      </button>
                      <button
                        onClick={() => setInspectorDoc(d.id)}
                        className="px-2 py-0 border border-border text-text-secondary"
                      >
                        [INSPECT]
                      </button>
                    </div>
                  </td>
                </tr>
              ))
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      {inspectorDoc && (
        <Inspector
          title={`DOC-${inspectorDoc}`}
          chain={chain}
          onClose={() => setInspectorDoc(null)}
        />
      )}
    </>
  )
}
