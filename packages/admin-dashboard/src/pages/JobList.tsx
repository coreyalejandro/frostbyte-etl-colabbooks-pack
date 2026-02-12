export default function JobList() {
  return (
    <div>
      <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary mb-4">
        BATCH JOBS
      </h2>
      <div
        className="bg-surface border border-border p-4"
        style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }}
      >
        <p className="text-text-secondary">
          Batch job history and progress. Integrate with batch API (POST /batch/jobs, SSE stream) when available.
        </p>
      </div>
    </div>
  )
}
