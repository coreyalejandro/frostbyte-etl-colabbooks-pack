import { useCallback, useEffect, useRef, useState } from 'react'

export interface LogEntry {
  stage: string
  message: string
  level: 'info' | 'warn' | 'error' | 'success'
  timestamp: string
  document_id?: string
  tenant_id?: string
}

const MAX_ENTRIES = 200
const RECONNECT_BASE_MS = 1000
const RECONNECT_MAX_MS = 16000

interface ConnectionError {
  message: string
  timestamp: Date
}

/**
 * SSE hook that streams pipeline log events from /api/v1/pipeline/stream.
 * Maintains a capped buffer, auto-reconnects on error with exponential backoff.
 */
export function usePipelineLog() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [connected, setConnected] = useState(false)
  const [lastError, setLastError] = useState<ConnectionError | null>(null)
  const [reconnectAttempt, setReconnectAttempt] = useState(0)
  const retryDelay = useRef(RECONNECT_BASE_MS)
  const esRef = useRef<EventSource | null>(null)
  const [checkTrigger, setCheckTrigger] = useState(0)

  const clear = useCallback(() => setLogs([]), [])

  // Function to manually trigger connection check
  const checkConnection = useCallback(() => {
    setCheckTrigger(prev => prev + 1)
  }, [])

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | null = null

    function connect() {
      if (cancelled) return
      
      console.log('[PipelineLog] Connecting to SSE...')
      const es = new EventSource('/api/v1/pipeline/stream')
      esRef.current = es

      es.onopen = () => {
        console.log('[PipelineLog] SSE connection opened')
        setConnected(true)
        setLastError(null)
        setReconnectAttempt(0)
        retryDelay.current = RECONNECT_BASE_MS
      }

      es.onmessage = (e) => {
        try {
          const entry: LogEntry = JSON.parse(e.data)
          setLogs((prev) => {
            const next = [...prev, entry]
            return next.length > MAX_ENTRIES ? next.slice(-MAX_ENTRIES) : next
          })
        } catch (err) {
          console.error('[PipelineLog] Failed to parse event:', err)
        }
      }

      es.onerror = (error) => {
        console.error('[PipelineLog] SSE error:', error)
        es.close()
        esRef.current = null
        setConnected(false)
        
        const errorMsg = 'Connection failed. Ensure pipeline API is running on port 8000.'
        setLastError({ message: errorMsg, timestamp: new Date() })
        
        if (!cancelled) {
          setReconnectAttempt(prev => prev + 1)
          timer = setTimeout(() => {
            retryDelay.current = Math.min(retryDelay.current * 2, RECONNECT_MAX_MS)
            console.log(`[PipelineLog] Reconnecting in ${retryDelay.current}ms...`)
            connect()
          }, retryDelay.current)
        }
      }
    }

    connect()

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
      esRef.current?.close()
      esRef.current = null
    }
  }, [checkTrigger]) // Re-run when checkTrigger changes

  return { logs, connected, clear, lastError, reconnectAttempt, checkConnection }
}
