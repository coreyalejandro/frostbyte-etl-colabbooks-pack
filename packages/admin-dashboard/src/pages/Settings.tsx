// PRIORITY 5: UX Polish - Settings Page
// Provider configuration and system settings

import { useState } from 'react'
import Panel from '../components/Panel'

interface ProviderConfig {
  id: string
  name: string
  enabled: boolean
  apiKey?: string
  endpoint?: string
  models: string[]
}

const MOCK_PROVIDERS: ProviderConfig[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    enabled: true,
    models: ['gpt-4', 'gpt-3.5-turbo'],
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    enabled: false,
    models: ['claude-3-opus', 'claude-3-sonnet'],
  },
  {
    id: 'local',
    name: 'Local (Ollama)',
    enabled: true,
    endpoint: 'http://localhost:11434',
    models: ['llama2', 'mistral'],
  },
]

export default function Settings() {
  const [providers, setProviders] = useState<ProviderConfig[]>(MOCK_PROVIDERS)
  const [activeTab, setActiveTab] = useState<'providers' | 'pipeline' | 'notifications'>('providers')

  const toggleProvider = (id: string) => {
    setProviders((prev) =>
      prev.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p))
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary">Settings</h1>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {(['providers', 'pipeline', 'notifications'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium uppercase tracking-wider transition-colors ${
              activeTab === tab
                ? 'text-accent border-b-2 border-accent'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Providers Tab */}
      {activeTab === 'providers' && (
        <Panel title="LLM Providers">
          <div className="space-y-4">
            {providers.map((provider) => (
              <div
                key={provider.id}
                className={`p-4 border rounded ${
                  provider.enabled ? 'border-accent bg-accent/5' : 'border-border'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => toggleProvider(provider.id)}
                      className={`w-12 h-6 rounded-full transition-colors relative ${
                        provider.enabled ? 'bg-accent' : 'bg-border'
                      }`}
                      aria-label={`Toggle ${provider.name}`}
                    >
                      <span
                        className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                          provider.enabled ? 'left-7' : 'left-1'
                        }`}
                      />
                    </button>
                    <div>
                      <div className="font-medium text-text-primary">{provider.name}</div>
                      <div className="text-xs text-text-tertiary">
                        {provider.enabled ? 'Enabled' : 'Disabled'} · {provider.models.length} models
                      </div>
                    </div>
                  </div>
                  <button className="px-3 py-1 text-xs border border-border hover:border-accent text-text-secondary hover:text-accent">
                    [CONFIGURE]
                  </button>
                </div>

                {provider.enabled && (
                  <div className="mt-4 pt-4 border-t border-border space-y-3">
                    {provider.endpoint && (
                      <div>
                        <label className="text-xs text-text-tertiary uppercase">Endpoint</label>
                        <input
                          type="text"
                          value={provider.endpoint}
                          readOnly
                          className="w-full mt-1 px-2 py-1 bg-surface border border-border text-text-secondary text-sm"
                        />
                      </div>
                    )}
                    <div>
                      <label className="text-xs text-text-tertiary uppercase">Available Models</label>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {provider.models.map((model) => (
                          <span
                            key={model}
                            className="px-2 py-0.5 text-xs bg-surface border border-border text-text-secondary"
                          >
                            {model}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Panel>
      )}

      {/* Pipeline Tab */}
      {activeTab === 'pipeline' && (
        <Panel title="Pipeline Configuration">
          <div className="space-y-4">
            <div>
              <label className="text-xs text-text-tertiary uppercase">Default Batch Size</label>
              <input
                type="number"
                defaultValue={32}
                className="w-full mt-1 px-2 py-1 bg-surface border border-border text-text-primary"
              />
            </div>
            <div>
              <label className="text-xs text-text-tertiary uppercase">Max Retry Attempts</label>
              <input
                type="number"
                defaultValue={3}
                className="w-full mt-1 px-2 py-1 bg-surface border border-border text-text-primary"
              />
            </div>
            <div>
              <label className="text-xs text-text-tertiary uppercase">Timeout (seconds)</label>
              <input
                type="number"
                defaultValue={300}
                className="w-full mt-1 px-2 py-1 bg-surface border border-border text-text-primary"
              />
            </div>
            <div className="pt-4 border-t border-border">
              <button className="px-4 py-2 bg-accent text-black text-sm font-medium hover:bg-accent-hover">
                Save Configuration
              </button>
            </div>
          </div>
        </Panel>
      )}

      {/* Notifications Tab */}
      {activeTab === 'notifications' && (
        <Panel title="Notification Settings">
          <div className="space-y-4">
            {[
              { id: 'email', label: 'Email notifications', enabled: true },
              { id: 'slack', label: 'Slack webhooks', enabled: false },
              { id: 'pagerduty', label: 'PagerDuty integration', enabled: false },
            ].map((item) => (
              <div key={item.id} className="flex items-center justify-between py-2">
                <span className="text-text-secondary">{item.label}</span>
                <button
                  className={`w-12 h-6 rounded-full transition-colors relative ${
                    item.enabled ? 'bg-accent' : 'bg-border'
                  }`}
                >
                  <span
                    className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                      item.enabled ? 'left-7' : 'left-1'
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  )
}
