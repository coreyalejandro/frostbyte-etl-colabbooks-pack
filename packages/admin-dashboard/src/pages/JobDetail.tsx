import { useParams } from 'react-router-dom'
import { useJobProgress } from '../hooks/useJobProgress'

export default function JobDetail() {
  const { id } = useParams<{ id: string }>()
  const { progress, status } = useJobProgress(id ?? '')

  return (
    <div>
      <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary mb-4">
        JOB: {id}
      </h2>
      <div
        className="bg-surface border border-border p-4"
        style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }}
      >
        <p className="text-text-primary">STATUS: {status}</p>
        <p className="text-text-primary mt-2">
          PROGRESS: {progress.processed} / {progress.total}
        </p>
        <p className="text-xs text-text-tertiary mt-4">
          SSE stream from /api/v1/batch/jobs/&#123;id&#125;/stream (when batch API exists).
        </p>
      </div>
    </div>
  )
}
