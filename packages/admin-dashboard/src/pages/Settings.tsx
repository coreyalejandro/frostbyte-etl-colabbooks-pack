export default function Settings() {
  return (
    <div>
      <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary mb-4">
        SETTINGS
      </h2>
      <div
        className="bg-surface border border-border p-4"
        style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }}
      >
        <p className="text-text-secondary">
          Provider configuration, API keys. Configure via .env (VITE_API_URL).
        </p>
      </div>
    </div>
  )
}
