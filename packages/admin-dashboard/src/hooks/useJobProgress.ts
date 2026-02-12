import { useEffect, useState } from 'react'

interface JobProgress {
  processed: number
  total: number
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function useJobProgress(jobId: string) {
  const [progress, setProgress] = useState<JobProgress>({ processed: 0, total: 0 })
  const [status, setStatus] = useState<string>('pending')

  useEffect(() => {
    if (!jobId) return
    const url = `${API_BASE}/api/v1/batch/jobs/${jobId}/stream`
    const es = new EventSource(url)
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.event_type === 'progress') {
          setProgress((p) => ({ ...p, processed: (p.processed || 0) + 1 }))
        } else if (data.event_type === 'complete' || data.event_type === 'cancel') {
          setStatus(data.event_type)
          es.close()
        }
      } catch {
        // ignore parse errors
      }
    }
    es.onerror = () => es.close()
    return () => es.close()
  }, [jobId])

  return { progress, status }
}
