interface ChainStep {
  ts: string
  op: string
  ok: boolean
}

interface InspectorProps {
  title: string
  chain?: ChainStep[]
  children?: React.ReactNode
  onClose: () => void
}

export default function Inspector({ title, chain, children, onClose }: InspectorProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(10,12,14,0.95)' }}
    >
      <div
        className="bg-surface border border-border p-6 max-w-lg w-full max-h-[80vh] overflow-auto"
        style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }}
      >
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-medium uppercase tracking-wider text-text-secondary">
            INSPECTOR: {title}
          </h3>
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary text-base"
          >
            [×]
          </button>
        </div>
        <div className="border-t border-border pt-4">
          {chain ? (
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-text-secondary mb-2">
                CHAIN OF CUSTODY
              </p>
              <ol className="space-y-2 font-mono text-sm">
                {chain.map((step, i) => (
                  <li key={i} className="text-text-primary">
                    {i + 1}. {step.ts} {step.op} {step.ok ? '✓' : '⚠'}
                  </li>
                ))}
              </ol>
            </div>
          ) : (
            children
          )}
        </div>
      </div>
    </div>
  )
}
