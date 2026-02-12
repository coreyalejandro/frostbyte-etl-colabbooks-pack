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

/**
 * SSE hook that streams pipeline log events from /api/v1/pipeline/stream.
 * Maintains a capped buffer, auto-reconnects on error with exponential backoff.
 */
export function usePipelineLog() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [connected, setConnected] = useState(false)
  const retryDelay = useRef(RECONNECT_BASE_MS)
  const esRef = useRef<EventSource | null>(null)

  const clear = useCallback(() => setLogs([]), [])

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | null = null

    function connect() {
      if (cancelled) return
      const es = new EventSource('/api/v1/pipeline/stream')
      esRef.current = es

      es.onopen = () => {
        setConnected(true)
        retryDelay.current = RECONNECT_BASE_MS
      }

      es.onmessage = (e) => {
        try {
          const entry: LogEntry = JSON.parse(e.data)
          setLogs((prev) => {
            const next = [...prev, entry]
            return next.length > MAX_ENTRIES ? next.slice(-MAX_ENTRIES) : next
          })
        } catch {
          // ignore malformed events
        }
      }

      es.onerror = () => {
        es.close()
        esRef.current = null
        setConnected(false)
        if (!cancelled) {
          timer = setTimeout(() => {
            retryDelay.current = Math.min(retryDelay.current * 2, RECONNECT_MAX_MS)
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
  }, [])

  return { logs, connected, clear }
}
