// PRIORITY 4: Error Handling & Resilience - Dashboard Skeleton
// Full dashboard loading state

import { SkeletonCard } from './SkeletonCard'

export function DashboardSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading dashboard">
      {/* Header skeleton */}
      <div className="flex justify-between items-center">
        <div className="h-8 bg-gray-700 rounded w-48 animate-pulse" />
        <div className="h-10 bg-gray-700 rounded w-32 animate-pulse" />
      </div>

      {/* Stats skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>

      {/* Charts skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="h-64 bg-gray-800 rounded-lg animate-pulse" />
        <div className="h-64 bg-gray-800 rounded-lg animate-pulse" />
      </div>

      {/* Tables skeleton */}
      <div className="space-y-4">
        <div className="h-6 bg-gray-700 rounded w-32 animate-pulse" />
        <div className="h-48 bg-gray-800 rounded-lg animate-pulse" />
      </div>
    </div>
  )
}
