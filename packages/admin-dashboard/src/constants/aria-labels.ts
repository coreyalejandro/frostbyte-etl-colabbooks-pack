// PRIORITY 2: Accessibility & Compliance - ARIA Label Registry
// Central source of truth for all ARIA labels and accessibility text

export const ARIA_LABELS = {
  // Navigation
  navigation: {
    sidebar: 'Main navigation sidebar',
    dashboard: 'Go to Dashboard',
    tenants: 'Go to Tenants list',
    documents: 'Go to Documents list',
    audit: 'Go to Audit logs',
    verify: 'Go to Verification gates',
    control: 'Go to Pipeline control',
    onboard: 'Go to Onboarding',
    settings: 'Go to Settings',
    logout: 'Sign out of your account',
  },

  // Actions
  actions: {
    signIn: 'Sign in to Frostbyte Admin',
    signOut: 'Sign out of your account',
    viewDetails: (item: string) => `View details for ${item}`,
    verifyDocument: (id: string) => `Verify document ${id}`,
    inspectDocument: (id: string) => `Inspect document ${id}`,
    retryDocument: (id: string) => `Retry processing document ${id}`,
    clearLogs: 'Clear all log entries',
    clearFilters: 'Clear all filters',
    refresh: 'Refresh data',
    download: 'Download file',
    upload: 'Upload file',
  },

  // Pipeline
  pipeline: {
    streamToggle: (isLive: boolean) => isLive ? 'Disable live stream' : 'Enable live stream',
    stage: (name: string) => `${name} pipeline stage`,
    node: (name: string, status: string) => `${name} stage - ${status}`,
    connectionStatus: (isConnected: boolean) => isConnected ? 'Stream connected' : 'Stream disconnected',
  },

  // Tables
  tables: {
    sortBy: (column: string) => `Sort by ${column}`,
    selectRow: (id: string) => `Select row ${id}`,
    selectAll: 'Select all rows',
    rowActions: (id: string) => `Actions for ${id}`,
  },

  // Filters
  filters: {
    stage: 'Filter by pipeline stage',
    status: 'Filter by event status',
    tenant: 'Filter by tenant',
    dateRange: 'Filter by date range',
  },

  // Modals
  modals: {
    close: 'Close modal',
    confirm: 'Confirm action',
    cancel: 'Cancel action',
  },

  // Forms
  forms: {
    apiKey: 'API Key input',
    submit: 'Submit form',
    reset: 'Reset form',
  },

  // Observability
  observability: {
    eventCard: (model: string, operation: string) => `View details for ${model} ${operation} event`,
    decisionTracer: 'Decision tracer panel',
    provenanceTimeline: 'Model provenance timeline',
    activityMonitor: 'Model activity monitor',
  },
} as const

// Helper function to get nested values with type safety
export function getAriaLabel<T extends keyof typeof ARIA_LABELS>(
  category: T,
  key: keyof typeof ARIA_LABELS[T]
): string {
  const value = ARIA_LABELS[category][key]
  return typeof value === 'function' ? value('') : value
}
