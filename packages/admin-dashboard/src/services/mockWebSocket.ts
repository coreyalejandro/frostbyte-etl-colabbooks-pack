type EventCallback = (data: unknown) => void

export interface ThroughputEvent {
  nodeId: string
  throughput: number
}

export interface NodeStatusEvent {
  nodeId: string
  status: 'healthy' | 'processing' | 'error' | 'idle'
}

export interface DocumentProgressEvent {
  documentId: string
  stage: string
  progress: number
}

export class MockPipelineSocket {
  private listeners: Map<string, Set<EventCallback>> = new Map()
  private intervals: number[] = []
  private _isConnected = false

  get isConnected(): boolean {
    return this._isConnected
  }

  connect(): void {
    if (this._isConnected) return
    this._isConnected = true
    this.emit('connection', { connected: true })
    this.startEmitting()
  }

  disconnect(): void {
    this._isConnected = false
    for (const interval of this.intervals) {
      clearInterval(interval)
    }
    this.intervals = []
    this.emit('connection', { connected: false })
  }

  on(event: string, callback: EventCallback): () => void {
    const existing = this.listeners.get(event)
    if (existing) {
      existing.add(callback)
    } else {
      this.listeners.set(event, new Set([callback]))
    }
    return () => {
      this.listeners.get(event)?.delete(callback)
    }
  }

  private emit(event: string, data: unknown): void {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      for (const cb of callbacks) {
        cb(data)
      }
    }
  }

  private startEmitting(): void {
    const STAGES = ['intake', 'parse', 'evidence', 'embed', 'vector', 'metadata', 'verify']
    const baseThroughputs: Record<string, number> = {
      intake: 142, parse: 138, evidence: 124, embed: 120,
      vector: 118, metadata: 118, verify: 115,
    }

    this.intervals.push(
      window.setInterval(() => {
        if (!this._isConnected) return
        for (const nodeId of STAGES) {
          const base = baseThroughputs[nodeId]
          const jitter = base * 0.15
          const throughput = Math.round(base + (Math.random() * 2 - 1) * jitter)
          this.emit('pipeline:throughput', { nodeId, throughput } satisfies ThroughputEvent)
        }
      }, 2000),
    )

    this.intervals.push(
      window.setInterval(() => {
        if (!this._isConnected) return
        if (Math.random() > 0.3) return
        const nodeId = STAGES[Math.floor(Math.random() * STAGES.length)]
        const status = Math.random() > 0.15 ? 'processing' : 'healthy'
        this.emit('pipeline:node-status', { nodeId, status } satisfies NodeStatusEvent)
      }, 5000),
    )

    this.intervals.push(
      window.setInterval(() => {
        if (!this._isConnected) return
        const stageIndex = Math.floor(Math.random() * STAGES.length)
        this.emit('pipeline:document-progress', {
          documentId: `mock-${Math.random().toString(16).slice(2, 6)}`,
          stage: STAGES[stageIndex],
          progress: Math.round(Math.random() * 100),
        } satisfies DocumentProgressEvent)
      }, 3000),
    )
  }
}
