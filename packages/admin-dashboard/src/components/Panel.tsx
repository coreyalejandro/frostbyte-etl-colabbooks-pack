interface PanelProps {
  title?: string
  children: React.ReactNode
  className?: string
}

export default function Panel({ title, children, className = '' }: PanelProps) {
  return (
    <div
      className={`bg-surface border border-border p-4 ${className}`}
      style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }}
    >
      {title && (
        <h3 className="text-xs font-medium uppercase tracking-wider text-text-secondary mb-2">
          {title}
        </h3>
      )}
      {children}
    </div>
  )
}
