import Panel from '../../components/Panel'
import PipelineDAG from '../../components/pipeline/PipelineDAG'
import PipelineLogStream from './PipelineLogStream'

export default function PipelineSchematic() {
  return (
    <Panel title="PIPELINE SCHEMATIC">
      <PipelineDAG />
      <PipelineLogStream />
    </Panel>
  )
}
