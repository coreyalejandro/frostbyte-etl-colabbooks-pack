// ISSUE #1-10: Model Events API Hook
// REASONING: TanStack Query hook for fetching and streaming model events
// ADDED BY: Kombai on 2026-02-14

import { useQuery } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import type { ModelEvent, ModelEventFilters } from '../types/observability'
import { MOCK_MODEL_EVENTS } from '../data/mockObservability'

/**
 * Fetch model events with optional filtering
 * TODO: Replace mock data with real API call when backend ready
 */
export function useModelEvents(filters?: ModelEventFilters) {
  return useQuery({
    queryKey: ['model-events', filters],
    queryFn: async (): Promise<ModelEvent[]> => {
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 300))
      
      let filtered = [...MOCK_MODEL_EVENTS]
      
      // Apply filters
      if (filters?.tenantId) {
        filtered = filtered.filter(e => e.tenantId === filters.tenantId)
      }
      if (filters?.documentId) {
        filtered = filtered.filter(e => e.documentId === filters.documentId)
      }
      if (filters?.stage) {
        filtered = filtered.filter(e => e.stage === filters.stage)
      }
      if (filters?.modelName) {
        filtered = filtered.filter(e => e.modelName === filters.modelName)
      }
      if (filters?.status) {
        filtered = filtered.filter(e => e.status === filters.status)
      }
      
      // Sort by timestamp descending
      filtered.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      
      // Apply pagination
      const offset = filters?.offset ?? 0
      const limit = filters?.limit ?? 50
      return filtered.slice(offset, offset + limit)
    },
    refetchInterval: 5000, // Refresh every 5 seconds for "real-time" feel
  })
}

/**
 * Stream model events via SSE (Server-Sent Events)
 * Returns real-time events as they occur
 * TODO: Implement actual SSE connection when backend ready
 */
export function useModelEventStream(_filters?: ModelEventFilters) {
  const [events, setEvents] = useState<ModelEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    // Simulate SSE connection with mock data
    setIsConnected(true)
    
    // Add one mock event every 10 seconds to simulate stream
    const interval = setInterval(() => {
      const newEvent: ModelEvent = {
        id: `evt_${Date.now()}`,
        timestamp: new Date().toISOString(),
        tenantId: 'PROD-01',
        documentId: `doc_${Math.floor(Math.random() * 9999)}`,
        documentName: `document_${Math.floor(Math.random() * 100)}.pdf`,
        stage: ['parse', 'embed', 'verify'][Math.floor(Math.random() * 3)] as any,
        modelName: ['docling', 'nomic-embed-text-v1', 'policy-classifier'][Math.floor(Math.random() * 3)],
        modelVersion: '1.0.0',
        operation: 'process',
        status: Math.random() > 0.1 ? 'completed' : 'failed',
        durationMs: Math.floor(Math.random() * 5000) + 1000,
      }
      
      setEvents(prev => [newEvent, ...prev].slice(0, 100)) // Keep last 100 events
    }, 10000)

    return () => {
      clearInterval(interval)
      setIsConnected(false)
    }
  }, [])

  return {
    events,
    isConnected,
  }
}
