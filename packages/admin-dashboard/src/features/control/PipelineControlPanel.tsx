import { usePipelineStore } from '../../stores/pipelineStore'
import type { PipelineMode, EmbeddingModel } from '../../stores/pipelineStore'
import Panel from '../../components/Panel'

const MODES: PipelineMode[] = ['ONLINE', 'OFFLINE', 'HYBRID']
const MODELS: EmbeddingModel[] = ['OPENAI', 'QWEN', 'KIMI', 'NOMIC']

export default function PipelineControlPanel() {
  const { mode, model, batchSize, setMode, setModel, setBatchSize, commitConfig } =
    usePipelineStore()

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
                  mode === m ? 'border-accent text-text-primary' : 'border-border text-text-secondary'
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
            onChange={(e) => setBatchSize(parseInt(e.target.value, 10) || 32)}
            min={1}
            max={256}
            className="bg-base border border-border px-3 py-2 w-24 text-text-primary font-mono focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-0"
          />
        </div>
        <button
          onClick={commitConfig}
          className="px-4 py-2 border border-border bg-interactive text-text-primary text-xs font-medium uppercase tracking-wider hover:bg-surface"
        >
          [COMMIT]
        </button>
      </div>
    </Panel>
  )
}
