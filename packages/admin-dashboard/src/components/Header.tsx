import { useAuth } from '../contexts/AuthContext'
import { useTenant } from '../contexts/TenantContext'
import { usePipelineStore } from '../stores/pipelineStore'
import { useNetworkStore } from '../stores/networkStore'
import Sidebar from './Sidebar'

export default function Header() {
  const { logout } = useAuth()
  const { selectedTenantId } = useTenant()
  const { online } = usePipelineStore()
  const { isOffline } = useNetworkStore()

  return (
    <header className="bg-surface border-b border-border px-6 py-4 flex justify-between items-center">
      <div className="flex items-center gap-6">
        <span className="text-text-secondary text-xs font-medium uppercase tracking-wider">
          [TENANT: {selectedTenantId?.toUpperCase() ?? 'PROD-01'}]
        </span>
        <Sidebar />
      </div>
      <div className="flex items-center gap-4">
        <span
          className={online ? 'text-accent' : 'text-inactive'}
          title={online ? 'Pipeline Online' : 'Pipeline Offline'}
          aria-label={online ? 'Pipeline status: Online' : 'Pipeline status: Offline'}
          role="status"
        >
          ●
        </span>
        <span
          className={`text-xs font-medium uppercase tracking-wider ${isOffline ? 'text-red-400' : 'text-text-tertiary'}`}
          role="status"
        >
          {isOffline ? 'OFFLINE' : 'ONLINE'}
        </span>
        <button
          onClick={logout}
          className="px-3 py-1 text-xs font-medium uppercase tracking-wider border border-border bg-interactive text-text-primary hover:bg-surface"
          aria-label="Logout from admin dashboard"
        >
          [LOGOUT]
        </button>
      </div>
    </header>
  )
}
