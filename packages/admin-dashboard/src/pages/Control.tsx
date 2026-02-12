import PipelineControlPanel from '../features/control/PipelineControlPanel'
import PipelineSchematic from '../features/pipeline/PipelineSchematic'

export default function Control() {
  return (
    <div className="space-y-6">
      <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary">
        CONTROL
      </h2>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <PipelineSchematic />
        </div>
        <PipelineControlPanel />
      </div>
    </div>
  )
}
