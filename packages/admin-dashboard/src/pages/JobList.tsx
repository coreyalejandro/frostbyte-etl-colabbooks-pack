// PRIORITY 5: UX Polish - Jobs Page
// Job management and monitoring

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Panel from '../components/Panel'

interface Job {
  id: string
  name: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  type: 'ingest' | 'parse' | 'embed' | 'verify' | 'export'
  tenantId: string
  documentCount: number
  createdAt: string
  startedAt?: string
  completedAt?: string
  errorMessage?: string
}

const MOCK_JOBS: Job[] = [
  {
    id: 'job-001',
    name: 'Batch Ingest - Q4 Contracts',
    status: 'running',
    progress: 67,
    type: 'ingest',
    tenantId: 'default',
    documentCount: 150,
    createdAt: '2026-02-14T08:00:00Z',
    startedAt: '2026-02-14T08:05:00Z',
  },
  {
    id: 'job-002',
    name: 'Re-embed with new model',
    status: 'queued',
    progress: 0,
    type: 'embed',
    tenantId: 'default',
    documentCount: 1247,
    createdAt: '2026-02-14T07:30:00Z',
  },
  {
    id: 'job-003',
    name: 'Policy verification sweep',
    status: 'completed',
    progress: 100,
    type: 'verify',
    tenantId: 'default',
    documentCount: 89,
    createdAt: '2026-02-14T06:00:00Z',
    startedAt: '2026-02-14T06:05:00Z',
    completedAt: '2026-02-14T06:45:00Z',
  },
  {
    id: 'job-004',
    name: 'Export audit logs',
    status: 'failed',
    progress: 45,
    type: 'export',
    tenantId: 'default',
    documentCount: 0,
    createdAt: '2026-02-14T05:00:00Z',
    startedAt: '2026-02-14T05:05:00Z',
    completedAt: '2026-02-14T05:15:00Z',
    errorMessage: 'MinIO connection timeout',
  },
]

const STATUS_COLORS: Record<Job['status'], string> = {
  queued: 'text-text-secondary',
  running: 'text-blue-400',
  completed: 'text-accent',
  failed: 'text-red-400',
  cancelled: 'text-inactive',
}

const STATUS_ICONS: Record<Job['status'], string> = {
  queued: '○',
  running: '⟳',
  completed: '✓',
  failed: '✗',
  cancelled: '⊘',
}

export default function JobList() {
  const navigate = useNavigate()
  const [jobs, setJobs] = useState<Job[]>(MOCK_JOBS)
  const [filter, setFilter] = useState<Job['status'] | 'all'>('all')

  const filteredJobs = filter === 'all' ? jobs : jobs.filter((j) => j.status === filter)

  const cancelJob = (id: string) => {
    setJobs((prev) =>
      prev.map((j) => (j.id === id ? { ...j, status: 'cancelled' as const } : j))
    )
  }

  const retryJob = (id: string) => {
    setJobs((prev) =>
      prev.map((j) =>
        j.id === id
          ? { ...j, status: 'queued' as const, progress: 0, errorMessage: undefined }
          : j
      )
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-primary">Jobs</h1>
        <button className="px-4 py-2 bg-accent text-black text-sm font-medium hover:bg-accent-hover flex items-center gap-2">
          <span>+</span>
          <span>NEW JOB</span>
        </button>
      </div>

      <Panel title="JOB QUEUE">
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 mb-4 pb-3 border-b border-border">
          {(['all', 'queued', 'running', 'completed', 'failed'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-3 py-1 text-xs font-medium uppercase tracking-wider border transition-colors ${
                filter === status
                  ? 'border-accent text-accent bg-accent/5'
                  : 'border-border text-text-secondary hover:text-text-primary hover:border-text-secondary'
              }`}
            >
              {status}
            </button>
          ))}
        </div>

        {/* Job List */}
        <div className="space-y-3">
          {filteredJobs.length === 0 ? (
            <div className="text-center py-12 text-text-tertiary">
              <p>No jobs found</p>
            </div>
          ) : (
            filteredJobs.map((job) => (
              <div
                key={job.id}
                className="p-4 border border-border bg-surface hover:bg-interactive transition-colors cursor-pointer"
                onClick={() => navigate(`/jobs/${job.id}`)}
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Left: Job Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-sm ${STATUS_COLORS[job.status]}`}>
                        {STATUS_ICONS[job.status]}
                      </span>
                      <span className="font-medium text-text-primary truncate">{job.name}</span>
                      <span className="text-[10px] text-text-tertiary uppercase px-1.5 py-0.5 border border-border">
                        {job.type}
                      </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="mb-2">
                      <div className="h-1.5 bg-border rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-300 ${
                            job.status === 'failed'
                              ? 'bg-red-400'
                              : job.status === 'completed'
                              ? 'bg-accent'
                              : 'bg-blue-400'
                          }`}
                          style={{ width: `${job.progress}%` }}
                        />
                      </div>
                      <div className="flex justify-between mt-1">
                        <span className="text-[10px] text-text-tertiary">
                          {job.status === 'running' ? (
                            <span className="text-blue-400 animate-pulse">Processing...</span>
                          ) : job.status === 'failed' ? (
                            <span className="text-red-400">{job.errorMessage}</span>
                          ) : (
                            `${job.progress}%`
                          )}
                        </span>
                        <span className="text-[10px] text-text-tertiary">
                          {job.documentCount > 0 && `${job.documentCount} documents`}
                        </span>
                      </div>
                    </div>

                    {/* Timestamps */}
                    <div className="flex items-center gap-4 text-[10px] text-text-tertiary">
                      <span>Created: {new Date(job.createdAt).toLocaleTimeString()}</span>
                      {job.startedAt && <span>Started: {new Date(job.startedAt).toLocaleTimeString()}</span>}
                      {job.completedAt && (
                        <span>Completed: {new Date(job.completedAt).toLocaleTimeString()}</span>
                      )}
                    </div>
                  </div>

                  {/* Right: Actions */}
                  <div className="flex items-center gap-2">
                    {job.status === 'running' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          cancelJob(job.id)
                        }}
                        className="px-3 py-1 text-xs border border-red-400 text-red-400 hover:bg-red-400 hover:text-black transition-colors"
                      >
                        [CANCEL]
                      </button>
                    )}
                    {job.status === 'failed' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          retryJob(job.id)
                        }}
                        className="px-3 py-1 text-xs border border-accent text-accent hover:bg-accent hover:text-black transition-colors"
                      >
                        [RETRY]
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          )}
        </div>

        {/* Summary */}
        <div className="mt-4 pt-3 border-t border-border flex justify-between text-xs text-text-tertiary">
          <span>{filteredJobs.length} JOBS</span>
          <span>
            Running: {jobs.filter((j) => j.status === 'running').length} ·
            Queued: {jobs.filter((j) => j.status === 'queued').length} ·
            Failed: {jobs.filter((j) => j.status === 'failed').length}
          </span>
        </div>
      </Panel>
    </div>
  )
}
