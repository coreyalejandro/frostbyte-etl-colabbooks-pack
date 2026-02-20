import { memo } from 'react'
import { getSmoothStepPath, type EdgeProps } from '@xyflow/react'

/**
 * Manhattan-routed pipeline edge.
 * getSmoothStepPath with borderRadius: 0 produces strict orthogonal
 * (horizontal + vertical only) segments — Manhattan routing.
 * offset controls the midpoint step distance for non-collinear nodes.
 */
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
    offset: 20,
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
