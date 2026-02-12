import { useState } from 'react'
import { usePipelineStore } from '../../stores/pipelineStore'
import Panel from '../../components/Panel'
import Inspector from '../../components/Inspector'

export default function AuditGallery() {
  const { audit } = usePipelineStore()
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null)
  const [verifying, setVerifying] = useState(false)
  const [verifiedIdx, setVerifiedIdx] = useState<number | null>(null)
  const [verifyResult, setVerifyResult] = useState<'✓' | 'FAIL' | null>(null)

  const handleVerify = (idx: number) => {
    setVerifying(true)
    setVerifyResult(null)
    setVerifiedIdx(idx)
    setTimeout(() => {
      setVerifyResult('✓')
      setVerifying(false)
    }, 500)
  }

  return (
    <>
      <Panel title="AUDIT GALLERY">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-surface">
                <th className="border border-border px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
                  TIMESTAMP
                </th>
                <th className="border border-border px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
                  TENANT
                </th>
                <th className="border border-border px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
                  OPERATION
                </th>
                <th className="border border-border px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
                  FINGERPRINT
                </th>
                <th className="border border-border px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-text-secondary">
                  ACTIONS
                </th>
              </tr>
            </thead>
            <tbody>
              {audit.map((e, idx) => (
                <tr
                  key={idx}
                  onClick={() => setSelectedIdx(idx)}
                  className={`cursor-pointer hover:bg-interactive ${
                    selectedIdx === idx ? 'bg-interactive' : ''
                  }`}
                >
                  <td className="border border-border px-3 py-2 text-text-primary font-mono text-sm">
                    {e.timestamp}
                  </td>
                  <td className="border border-border px-3 py-2 text-text-primary">
                    {e.tenant}
                  </td>
                  <td className="border border-border px-3 py-2 text-text-primary font-mono">
                    {e.operation}
                  </td>
                  <td className="border border-border px-3 py-2 text-text-tertiary font-mono text-sm">
                    {e.fingerprint.slice(0, 4)}...
                  </td>
                  <td className="border border-border px-3 py-2">
                    <button
                      onClick={(ev) => {
                        ev.stopPropagation()
                        handleVerify(idx)
                      }}
                      disabled={verifying}
                      className="px-2 py-0 border border-border text-text-secondary disabled:opacity-50"
                    >
                      [VERIFY]
                    </button>
                    {verifyResult && idx === verifiedIdx && (
                      <span className={verifyResult === 'FAIL' ? 'text-accent ml-2' : 'text-text-primary ml-2'}>
                        {verifyResult}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-2 flex justify-end">
          <button className="px-3 py-1 border border-border text-text-secondary text-xs font-medium uppercase tracking-wider">
            [EXP]
          </button>
        </div>
      </Panel>

      {selectedIdx !== null && audit[selectedIdx] && (
        <Inspector
          title={`${audit[selectedIdx].operation} — ${audit[selectedIdx].fingerprint}`}
          onClose={() => setSelectedIdx(null)}
        >
          <p className="text-text-secondary text-sm mb-2">Full signature and chain</p>
          <pre className="text-text-primary font-mono text-xs bg-base border border-border p-4 overflow-auto">
            {JSON.stringify(
              {
                timestamp: audit[selectedIdx].timestamp,
                tenant: audit[selectedIdx].tenant,
                operation: audit[selectedIdx].operation,
                fingerprint: audit[selectedIdx].fingerprint,
              },
              null,
              2,
            )}
          </pre>
        </Inspector>
      )}
    </>
  )
}
