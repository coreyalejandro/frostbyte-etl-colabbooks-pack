import { useEffect, useState, useCallback } from 'react'
import { MockPipelineSocket } from '../services/mockWebSocket'
import { usePipelineStore } from '../stores/pipelineStore'
import type { ThroughputEvent, NodeStatusEvent } from '../services/mockWebSocket'

const socket = new MockPipelineSocket()
let listenerCount = 0

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(socket.isConnected)

  useEffect(() => {
    const unsubConnection = socket.on('connection', (data) => {
      setIsConnected((data as { connected: boolean }).connected)
    })

    const unsubThroughput = socket.on('pipeline:throughput', (data) => {
      const { nodeId, throughput } = data as ThroughputEvent
      usePipelineStore.getState().setNodeThroughput(nodeId, throughput)
    })

    const unsubStatus = socket.on('pipeline:node-status', (data) => {
      const { nodeId, status } = data as NodeStatusEvent
      usePipelineStore.setState((state) => ({
        nodes: state.nodes.map((n) =>
          n.id === nodeId ? { ...n, active: status !== 'idle' } : n
        ),
      }))
    })

    listenerCount++
    if (listenerCount === 1) {
      socket.connect()
    }
    setIsConnected(socket.isConnected)

    return () => {
      unsubConnection()
      unsubThroughput()
      unsubStatus()
      listenerCount--
      if (listenerCount === 0) {
        socket.disconnect()
      }
    }
  }, [])

  const disconnect = useCallback(() => {
    socket.disconnect()
  }, [])

  const reconnect = useCallback(() => {
    socket.connect()
  }, [])

  return { isConnected, disconnect, reconnect }
}
