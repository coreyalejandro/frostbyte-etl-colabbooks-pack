import { Component, type ReactNode, type ErrorInfo } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-base flex items-center justify-center p-8">
          <div className="bg-surface border border-border p-8 max-w-lg w-full">
            <h1 className="text-sm font-medium uppercase tracking-wider text-red-400 mb-4">
              SYSTEM ERROR
            </h1>
            <p className="text-text-primary font-mono text-sm mb-4">
              {this.state.error?.message ?? 'An unexpected error occurred'}
            </p>
            {import.meta.env.DEV && this.state.error?.stack && (
              <pre className="text-xs text-text-tertiary font-mono overflow-auto max-h-48 mb-4 p-2 bg-base border border-border">
                {this.state.error.stack}
              </pre>
            )}
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 border border-border bg-interactive text-text-primary text-xs font-medium uppercase tracking-wider hover:bg-surface"
            >
              [RELOAD]
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
