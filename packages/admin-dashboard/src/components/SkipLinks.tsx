// PRIORITY 2: Accessibility & Compliance - Skip Links
// Allows keyboard users to skip navigation

export function SkipLinks() {
  return (
    <div className="skip-link-container">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <a href="#navigation" className="skip-link" style={{ left: '200px' }}>
        Skip to navigation
      </a>
    </div>
  )
}
