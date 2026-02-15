import { useTokenRefresh } from '../hooks/useTokenRefresh'

function formatTime(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

export default function SessionWarning() {
  const { expiresIn, showWarning, dismissWarning } = useTokenRefresh()

  if (!showWarning || expiresIn === null) return null

  return (
    <div className="fixed top-4 right-4 z-50 bg-surface border border-accent p-4 max-w-xs">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-accent mb-1">
            SESSION EXPIRES IN
          </p>
          <p className="text-lg font-mono text-text-primary">
            {formatTime(expiresIn)}
          </p>
        </div>
        <button
          onClick={dismissWarning}
          className="text-text-secondary hover:text-text-primary text-xs"
        >
          [x]
        </button>
      </div>
    </div>
  )
}
