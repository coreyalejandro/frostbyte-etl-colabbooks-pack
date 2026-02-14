import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Login() {
  const { login, error } = useAuth()
  const navigate = useNavigate()
  const [apiKey, setApiKey] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!apiKey.trim()) return
    setLoading(true)
    try {
      await login(apiKey)
      navigate('/')
    } catch {
      // error shown via context
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-base">
      <div
        className="bg-surface border border-border p-8 max-w-md w-full"
        style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }}
      >
        <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary mb-2">
          FROSTBYTE ADMIN
        </h2>
        <p id="api-key-help" className="text-text-secondary text-sm mb-6">
          Sign in with your admin API key. Set <code className="bg-interactive px-1">FROSTBYTE_ADMIN_API_KEY</code> on the pipeline server.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="api_key" className="block text-xs font-medium uppercase tracking-wider text-text-secondary mb-1">
              API KEY
            </label>
            <input
              id="api_key"
              type="text"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="ENTER ADMIN API KEY"
              className="w-full bg-base border border-border px-3 py-2 text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-0 font-mono"
              style={{ WebkitTextSecurity: 'disc' } as React.CSSProperties}
              autoComplete="off"
              autoFocus
              aria-label="Admin API Key"
              aria-describedby="api-key-help"
            />
          </div>
          {error && (
            <p className="text-sm text-red-400">FAILED: {error}</p>
          )}
          <button
            type="submit"
            disabled={loading || !apiKey.trim()}
            className="w-full py-2 px-4 border border-border bg-interactive text-text-primary font-medium uppercase text-xs tracking-wider disabled:opacity-50 disabled:cursor-not-allowed hover:bg-surface active:translate-y-px"
          >
            {loading ? 'SIGNING IN…' : '[SIGN IN]'}
          </button>
        </form>
      </div>
    </div>
  )
}
