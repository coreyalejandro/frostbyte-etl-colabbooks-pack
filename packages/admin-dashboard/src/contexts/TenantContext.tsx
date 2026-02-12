import { createContext, useContext, useState, ReactNode } from 'react'

interface TenantContextType {
  selectedTenantId: string | null
  setSelectedTenantId: (id: string | null) => void
}

const TenantContext = createContext<TenantContextType | null>(null)

export function TenantProvider({ children }: { children: ReactNode }) {
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>('default')
  return (
    <TenantContext.Provider value={{ selectedTenantId, setSelectedTenantId }}>
      {children}
    </TenantContext.Provider>
  )
}

export function useTenant() {
  const ctx = useContext(TenantContext)
  if (!ctx) throw new Error('useTenant must be used within TenantProvider')
  return ctx
}
