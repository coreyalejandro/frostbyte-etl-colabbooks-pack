import { useEffect, useRef, useState } from 'react'
import { usePipelineLog, type LogEntry } from '../../hooks/usePipelineLog'
import { AutoStartButton } from '../../components/AutoStartButton'

const LEVEL_COLOR: Record<string, string> = {
  info: 'text-text-secondary',    // Gray = neutral info
  success: 'text-accent',         // Amber = success/completed
  warn: 'text-amber-400',         // Amber-400 = warnings (not failures)
  error: 'text-red-400',          // Red = errors/failures
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
  const { logs, connected, clear, lastError, reconnectAttempt, checkConnection } = usePipelineLog()
  const scrollRef = useRef<HTMLDivElement>(null)
  const [showManual, setShowManual] = useState(false)

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    const el = scrollRef.current
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }, [logs.length])

  const handleStarted = () => {
    // Trigger a reconnection check
    setTimeout(() => {
      checkConnection()
    }, 1000)
  }

  return (
    <div
      className="bg-surface border border-border mt-2"
      style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <div className="flex items-center gap-3">
          <h3 className="text-xs font-medium uppercase tracking-wider text-text-secondary">
            PIPELINE LOG
          </h3>
          
          {/* Connection Status Badge */}
          <div 
            className={`
              inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider
              transition-all duration-200
              ${connected 
                ? 'bg-green-400/20 text-green-400 border border-green-400/30' 
                : 'bg-red-400/20 text-red-400 border border-red-400/30'
              }
            `}
            title={connected ? 'Stream connected' : 'Stream disconnected'}
          >
            {/* Status Icon */}
            <span className={`
              inline-flex items-center justify-center w-4 h-4 rounded-full text-[8px]
              ${connected 
                ? 'bg-green-400 text-black animate-pulse' 
                : 'bg-red-400 text-black'
              }
            `}>
              {connected ? '●' : '✕'}
            </span>
            {connected ? 'LIVE' : 'OFFLINE'}
          </div>
          
          {/* Retry indicator when disconnected */}
          {!connected && reconnectAttempt > 0 && (
            <span className="text-[10px] text-text-tertiary">
              Retry #{reconnectAttempt}
            </span>
          )}
        </div>
        
        <button
          onClick={clear}
          disabled={logs.length === 0}
          className="text-[10px] uppercase tracking-wider text-text-tertiary hover:text-text-secondary border border-border px-2 py-0.5 disabled:opacity-30 disabled:cursor-not-allowed transition-opacity"
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
            {connected ? (
              'Waiting for pipeline events... Upload a document to see activity.'
            ) : lastError ? (
              <div className="space-y-3">
                <p className="text-red-400">{lastError.message}</p>
                
                {!showManual ? (
                  <div className="flex flex-col gap-3">
                    <AutoStartButton onStarted={handleStarted} />
                    <button
                      onClick={() => setShowManual(true)}
                      className="text-xs text-text-tertiary hover:text-text-secondary underline"
                    >
                      Show manual instructions
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2 text-xs">
                    <p className="text-text-tertiary">
                      Retry attempt: {reconnectAttempt}
                    </p>
                    <div className="bg-surface-elevated p-3 rounded space-y-2">
                      <p className="font-medium text-text-secondary">Manual start:</p>
                      <code className="block font-mono text-accent">
                        make pipeline
                      </code>
                      <p className="text-text-tertiary mt-2">Or:</p>
                      <code className="block font-mono text-accent">
                        ./scripts/pipeline-manager.sh start
                      </code>
                      <p className="text-text-tertiary mt-2">Infrastructure check:</p>
                      <code className="block font-mono text-accent">
                        docker-compose ps
                      </code>
                    </div>
                    <button
                      onClick={() => setShowManual(false)}
                      className="text-accent hover:underline"
                    >
                      ← Back to auto-start
                    </button>
                  </div>
                )}
              </div>
            ) : (
              'Connecting to pipeline stream...'
            )}
          </div>
        ) : (
          logs.map((entry, i) => <LogLine key={i} entry={entry} />)
        )}
      </div>
    </div>
  )
}
