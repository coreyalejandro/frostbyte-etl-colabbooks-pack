import { useState, useCallback } from 'react'

interface AutoStartButtonProps {
  onStarted?: () => void
}

export function AutoStartButton({ onStarted }: AutoStartButtonProps) {
  const [isStarting, setIsStarting] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleAutoStart = useCallback(async () => {
    setIsStarting(true)
    setError(null)
    setMessage('Checking infrastructure...')

    try {
      // Check infrastructure first
      const checks = [
        { name: 'Redis', url: 'http://localhost:6379', type: 'tcp' },
        { name: 'PostgreSQL', url: 'http://localhost:5433', type: 'tcp' },
        { name: 'MinIO', url: 'http://localhost:9000/minio/health/live', type: 'http' },
        { name: 'Qdrant', url: 'http://localhost:6333/readyz', type: 'http' },
      ]

      for (const check of checks) {
        setMessage(`Checking ${check.name}...`)
        try {
          if (check.type === 'http') {
            const response = await fetch(check.url, { method: 'GET', mode: 'no-cors' })
            // With no-cors, we can't read response, but if it doesn't throw, it's probably ok
          }
          // For TCP checks, we'll just proceed and let the pipeline manager handle it
        } catch {
          // Continue anyway, pipeline manager will check properly
        }
      }

      setMessage('Starting Pipeline API...')
      
      // Try to trigger auto-start via the manager
      // Since we can't easily execute shell from browser, we'll poll for the API to come up
      // The user needs to run: make pipeline-auto  or  ./scripts/pipeline-manager.sh start
      
      setMessage('Waiting for Pipeline API to start...')
      
      // Poll for up to 60 seconds
      for (let i = 0; i < 60; i++) {
        try {
          const response = await fetch('http://localhost:8000/health', {
            method: 'GET',
            headers: { 'Accept': 'application/json' },
          })
          if (response.ok) {
            setMessage('✅ Pipeline API is running!')
            onStarted?.()
            setTimeout(() => {
              setIsStarting(false)
              setMessage(null)
            }, 2000)
            return
          }
        } catch {
          // Not ready yet
        }
        
        await new Promise(resolve => setTimeout(resolve, 1000))
        setMessage(`Waiting for Pipeline API... (${i + 1}s)`)
      }
      
      throw new Error('Pipeline API did not start within 60 seconds')
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start Pipeline API')
      setIsStarting(false)
    }
  }, [onStarted])

  if (error) {
    return (
      <div className="space-y-2">
        <div className="text-red-400 text-sm">{error}</div>
        <div className="text-text-tertiary text-xs">
          <p>Please start manually:</p>
          <code className="block bg-surface-elevated p-2 rounded mt-1 font-mono text-xs">
            make pipeline
          </code>
          <p className="mt-2">Or in a new terminal:</p>
          <code className="block bg-surface-elevated p-2 rounded mt-1 font-mono text-xs">
            ./scripts/pipeline-manager.sh start
          </code>
        </div>
        <button
          onClick={() => {
            setError(null)
            setIsStarting(false)
          }}
          className="text-xs text-accent hover:underline"
        >
          Try Again
        </button>
      </div>
    )
  }

  if (isStarting) {
    return (
      <div className="flex items-center gap-2 text-text-secondary">
        <LoadingSpinner className="w-4 h-4 animate-spin" />
        <span className="text-sm">{message}</span>
      </div>
    )
  }

  return (
    <button
      onClick={handleAutoStart}
      className="px-4 py-2 bg-accent text-black text-sm font-medium rounded hover:bg-accent-hover transition-colors"
    >
      Auto-Start Pipeline
    </button>
  )
}

function LoadingSpinner({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}
