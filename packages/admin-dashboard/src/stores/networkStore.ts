import { create } from 'zustand'

interface NetworkState {
  isOffline: boolean
  setOffline: (offline: boolean) => void
}

export const useNetworkStore = create<NetworkState>()((set) => ({
  isOffline: typeof navigator !== 'undefined' ? !navigator.onLine : false,
  setOffline: (offline) => set({ isOffline: offline }),
}))

if (typeof window !== 'undefined') {
  window.addEventListener('online', () => useNetworkStore.getState().setOffline(false))
  window.addEventListener('offline', () => useNetworkStore.getState().setOffline(true))
}
