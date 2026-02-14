// ISSUE #44: Reusable Panel Component
// REASONING: Extract repeated panel styling into reusable component
// ADDED BY: Kombai on 2026-02-14

interface PanelProps {
  title: string
  children: React.ReactNode
  className?: string
  actions?: React.ReactNode
}

export default function Panel({ title, children, className = '', actions }: PanelProps) {
  return (
    <div
      className={`bg-surface border border-border p-4 ${className}`}
      style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-medium uppercase tracking-wider text-text-secondary">
          {title}
        </h3>
        {actions && <div>{actions}</div>}
      </div>
      {children}
    </div>
  )
}
