import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { useNetworkStore } from '../stores/networkStore'

export function useApi<T>(
  queryKey: string[],
  queryFn: () => Promise<T>,
  options?: Omit<UseQueryOptions<T, Error>, 'queryKey' | 'queryFn'>,
) {
  const { isOffline, setOffline } = useNetworkStore()

  const query = useQuery<T, Error>({
    queryKey,
    queryFn: async () => {
      try {
        const result = await queryFn()
        if (useNetworkStore.getState().isOffline) setOffline(false)
        return result
      } catch (error) {
        if (error instanceof TypeError && error.message.includes('fetch')) {
          setOffline(true)
        }
        throw error
      }
    },
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    enabled: !isOffline,
    ...options,
  })

  return {
    ...query,
    isOffline,
  }
}
