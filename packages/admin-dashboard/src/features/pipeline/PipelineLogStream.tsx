import { useEffect, useRef } from 'react'
import { usePipelineLog, type LogEntry } from '../../hooks/usePipelineLog'

const LEVEL_COLOR: Record<string, string> = {
  info: 'text-text-secondary',
  success: 'text-accent',
  warn: 'text-amber-400',
  error: 'text-red-400',
}

const STAGE_WIDTH = 10 // fixed width for stage tag alignment

function LogLine({ entry }: { entry: LogEntry }) {
  const color = LEVEL_COLOR[entry.level] || 'text-text-secondary'
  const stage = entry.stage.padEnd(STAGE_WIDTH)
  return (
    <div className={`${color} whitespace-pre leading-5`}>
      <span className="text-text-tertiary">{entry.timestamp}</span>
      {'  '}
      <span className="text-text-primary">[{stage}]</span>
      {'  '}
      <span>{entry.message}</span>
    </div>
  )
}

export default function PipelineLogStream() {
  const { logs, connected, clear } = usePipelineLog()
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    const el = scrollRef.current
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }, [logs.length])

  return (
    <div
      className="bg-surface border border-border mt-2"
      style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-medium uppercase tracking-wider text-text-secondary">
            PIPELINE LOG
          </h3>
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              connected ? 'bg-accent' : 'bg-red-400'
            }`}
            title={connected ? 'Stream connected' : 'Stream disconnected'}
          />
          <span className="text-[10px] text-text-tertiary">
            {connected ? 'LIVE' : 'DISCONNECTED'}
          </span>
        </div>
        <button
          onClick={clear}
          className="text-[10px] uppercase tracking-wider text-text-tertiary hover:text-text-secondary border border-border px-2 py-0.5"
        >
          CLEAR
        </button>
      </div>

      {/* Log output */}
      <div
        ref={scrollRef}
        className="font-mono text-xs px-4 py-2 overflow-y-auto"
        style={{ maxHeight: '14rem', minHeight: '6rem' }}
      >
        {logs.length === 0 ? (
          <div className="text-text-tertiary italic">
            {connected
              ? 'Waiting for pipeline events... Upload a document to see activity.'
              : 'Connecting to pipeline stream...'}
          </div>
        ) : (
          logs.map((entry, i) => <LogLine key={i} entry={entry} />)
        )}
      </div>
    </div>
  )
}
