import { isMockMode } from '../api/client'

export default function MockBanner() {
  if (!isMockMode()) return null

  return (
    <div className="bg-surface-elevated border-b border-border px-4 py-1 text-center">
      <span className="text-xs font-medium uppercase tracking-wider text-accent">
        [MOCK] API SIMULATION ACTIVE
      </span>
    </div>
  )
}
