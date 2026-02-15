import { memo } from 'react'
import { getSmoothStepPath, type EdgeProps } from '@xyflow/react'

function PipelineEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps) {
  const isActive = (data as { active?: boolean })?.active ?? false

  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 0,
  })

  return (
    <path
      id={id}
      d={edgePath}
      fill="none"
      stroke={isActive ? '#fbbf24' : '#3c4045'}
      strokeWidth={isActive ? 2 : 1}
      strokeDasharray={isActive ? '8 4' : 'none'}
      className={isActive ? 'animate-dash' : ''}
    />
  )
}

export default memo(PipelineEdgeComponent)
