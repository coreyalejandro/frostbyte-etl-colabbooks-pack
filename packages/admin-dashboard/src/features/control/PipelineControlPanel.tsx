import { useState, useCallback, useRef, useEffect } from 'react'
import { usePipelineStore } from '../../stores/pipelineStore'
import type { PipelineMode, EmbeddingModel } from '../../stores/pipelineStore'
import { api } from '../../api/client'
import Panel from '../../components/Panel'

const MODES: PipelineMode[] = ['ONLINE', 'OFFLINE', 'HYBRID']
const MODELS: EmbeddingModel[] = ['OPENAI', 'QWEN', 'KIMI', 'NOMIC']

type CommitStatus = 'idle' | 'committing' | 'success' | 'failed'

function getCommitLabel(status: CommitStatus): string {
  switch (status) {
    case 'committing':
      return '[COMMITTING...]'
    case 'success':
      return '[COMMITTED]'
    case 'failed':
      return '[FAILED]'
    default:
      return '[COMMIT]'
  }
}

function getCommitClassName(status: CommitStatus): string {
  const base =
    'px-4 py-2 border border-border bg-interactive text-xs font-medium uppercase tracking-wider'

  switch (status) {
    case 'committing':
      return `${base} text-text-secondary cursor-not-allowed`
    case 'success':
      return `${base} text-accent`
    case 'failed':
      return `${base} text-red-400`
    default:
      return `${base} text-text-primary hover:bg-surface`
  }
}

export default function PipelineControlPanel() {
  const { mode, model, batchSize, setMode, setModel, setBatchSize, commitConfig } =
    usePipelineStore()

  const [commitStatus, setCommitStatus] = useState<CommitStatus>('idle')
  const [commitError, setCommitError] = useState<string | null>(null)
  const [lastValidBatchSize, setLastValidBatchSize] = useState<number>(batchSize)
  const [batchError, setBatchError] = useState<string | null>(null)

  const statusTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      if (statusTimeoutRef.current) clearTimeout(statusTimeoutRef.current)
    }
  }, [])

  const handleCommit = useCallback(async () => {
    if (statusTimeoutRef.current) {
      clearTimeout(statusTimeoutRef.current)
      statusTimeoutRef.current = null
    }

    setCommitStatus('committing')
    setCommitError(null)

    try {
      await api.updateConfig({ mode, model, batchSize })
      commitConfig()
      setCommitStatus('success')

      statusTimeoutRef.current = setTimeout(() => {
        setCommitStatus('idle')
        statusTimeoutRef.current = null
      }, 2000)
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unknown error occurred'
      setCommitStatus('failed')
      setCommitError(message)

      statusTimeoutRef.current = setTimeout(() => {
        setCommitStatus('idle')
        setCommitError(null)
        statusTimeoutRef.current = null
      }, 3000)
    }
  }, [mode, model, batchSize, commitConfig])

  const handleBatchSizeChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const parsed = parseInt(e.target.value, 10) || 32
      setBatchSize(parsed)
      if (parsed >= 1 && parsed <= 256) {
        setLastValidBatchSize(parsed)
        setBatchError(null)
      }
    },
    [setBatchSize],
  )

  const handleBatchSizeBlur = useCallback(() => {
    if (batchSize < 1 || batchSize > 256) {
      setBatchSize(lastValidBatchSize)
      setBatchError('VALID RANGE: 1-256')
    } else {
      setBatchError(null)
    }
  }, [batchSize, lastValidBatchSize, setBatchSize])

  const isCommitting = commitStatus === 'committing'

  return (
    <Panel title="PIPELINE CONTROL">
      <div className="space-y-6">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-text-secondary mb-2">
            MODE
          </p>
          <div className="flex gap-2">
            {MODES.map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`px-3 py-2 text-xs font-medium uppercase tracking-wider border ${
                  mode === m
                    ? 'border-accent text-text-primary'
                    : 'border-border text-text-secondary'
                }`}
              >
                [{m}]
              </button>
            ))}
          </div>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-text-secondary mb-2">
            MODEL
          </p>
          <div className="flex flex-wrap gap-4">
            {MODELS.map((m) => (
              <label key={m} className="flex items-center gap-2 cursor-pointer">
                <span className="text-text-primary font-mono text-sm">
                  ({model === m ? '●' : ' '}) {m}
                </span>
                <input
                  type="radio"
                  name="model"
                  checked={model === m}
                  onChange={() => setModel(m)}
                  className="sr-only"
                />
              </label>
            ))}
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium uppercase tracking-wider text-text-secondary mb-2">
            BATCH SIZE
          </label>
          <input
            type="number"
            value={batchSize}
            onChange={handleBatchSizeChange}
            onBlur={handleBatchSizeBlur}
            min={1}
            max={256}
            className="bg-base border border-border px-3 py-2 w-24 text-text-primary font-mono focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-0"
          />
          {batchError && (
            <p className="text-red-400 text-xs font-mono mt-1">{batchError}</p>
          )}
        </div>
        <div>
          <button
            onClick={handleCommit}
            disabled={isCommitting}
            className={getCommitClassName(commitStatus)}
          >
            {getCommitLabel(commitStatus)}
          </button>
          {commitStatus === 'failed' && commitError && (
            <p className="text-red-400 text-xs font-mono mt-1">{commitError}</p>
          )}
        </div>
      </div>
    </Panel>
  )
}
