import { useEffect, useRef, useState, useCallback } from 'react'
import { MockPipelineSocket } from '../services/mockWebSocket'
import { usePipelineStore } from '../stores/pipelineStore'
import type { NodeStatusEvent } from '../services/mockWebSocket'

export function useWebSocket() {
  const socketRef = useRef<MockPipelineSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const store = usePipelineStore

  useEffect(() => {
    const socket = new MockPipelineSocket()
    socketRef.current = socket

    socket.on('connection', (data) => {
      setIsConnected((data as { connected: boolean }).connected)
    })

    socket.on('pipeline:node-status', (data) => {
      const { nodeId, status } = data as NodeStatusEvent
      store.setState((state) => ({
        nodes: state.nodes.map((n) =>
          n.id === nodeId ? { ...n, active: status !== 'idle' } : n
        ),
      }))
    })

    socket.connect()

    return () => {
      socket.disconnect()
      socketRef.current = null
    }
  }, [])

  const disconnect = useCallback(() => {
    socketRef.current?.disconnect()
  }, [])

  const reconnect = useCallback(() => {
    socketRef.current?.connect()
  }, [])

  return { isConnected, disconnect, reconnect }
}
