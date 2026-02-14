// PRIORITY 4: Error Handling & Resilience - Skeleton Table
// Loading placeholder for table content

interface SkeletonTableProps {
  rows?: number
  columns?: number
}

export function SkeletonTable({ rows = 5, columns = 4 }: SkeletonTableProps) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 animate-pulse">
          {Array.from({ length: columns }).map((_, j) => (
            <div
              key={j}
              className="h-4 bg-gray-700 rounded flex-1"
              style={{ animationDelay: `${i * 100}ms` }}
            />
          ))}
        </div>
      ))}
    </div>
  )
}
