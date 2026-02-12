import { usePipelineStore } from '../../stores/pipelineStore'
import Panel from '../../components/Panel'

export default function VerificationControlRoom() {
  const { gate1, gate2, gate3 } = usePipelineStore()

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Panel title="GATE 1: EVIDENCE">
        <ul className="space-y-2 text-sm font-mono">
          {gate1.map((g, i) => (
            <li key={i} className="flex justify-between">
              <span className={g.result === 'FAIL' ? 'text-accent' : 'text-text-primary'}>
                {g.result}
              </span>
              <span className="text-text-tertiary">{g.hash ?? '—'}</span>
            </li>
          ))}
        </ul>
        <button className="mt-3 px-3 py-1 border border-border text-text-secondary text-xs font-medium uppercase tracking-wider">
          [TEST]
        </button>
      </Panel>
      <Panel title="GATE 2: RETRIEVAL">
        <ul className="space-y-2 text-sm font-mono">
          {gate2.map((g, i) => (
            <li key={i}>
              <p className="text-text-secondary text-xs mb-1">Query: {g.query}</p>
              <p className="text-text-primary">Recall: {g.recall} | Grounding: {g.grounding}</p>
            </li>
          ))}
        </ul>
        <button className="mt-3 px-3 py-1 border border-border text-text-secondary text-xs font-medium uppercase tracking-wider">
          [TEST]
        </button>
      </Panel>
      <Panel title="GATE 3: RED-TEAM">
        {gate3 ? (
          <>
            <p className="text-text-primary font-mono">Score: {gate3.score}</p>
            <p className="text-text-tertiary text-xs mt-1">Last: {gate3.lastTest}</p>
            <button className="mt-3 px-3 py-1 border border-border text-text-secondary text-xs font-medium uppercase tracking-wider">
              [RUN SUITE]
            </button>
          </>
        ) : (
          <p className="text-text-tertiary">— NO DATA —</p>
        )}
      </Panel>
    </div>
  )
}
