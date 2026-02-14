/**
 * Onboarding material — all docs Frosty needs. Links use VITE_DOCS_BASE or GitHub.
 */
const DOCS_BASE = import.meta.env.VITE_DOCS_BASE || 'https://github.com/YOUR_ORG/YOUR_REPO/blob/master'

const onboardingLinks: { label: string; path: string; description: string }[] = [
  { label: 'Engineer onboarding', path: 'docs/team/ENGINEER_ONBOARDING.md', description: 'Architecture walkthrough, dev setup, first-task guide' },
  { label: 'Vendor operations guide (Dana)', path: 'docs/operations/VENDOR_OPERATIONS_GUIDE.md', description: 'Batch submission, acceptance reports, troubleshooting' },
  { label: 'Role-playing scenarios', path: 'docs/team/ROLE_PLAYING_SCENARIOS.md', description: 'CS and deployed engineer scenarios' },
  { label: 'Brief intro: enterprise data pipelines', path: 'docs/team/BRIEF_INTRO_ENTERPRISE_DATA_PIPELINES.md', description: 'Onboarding intro' },
  { label: 'Single source of truth (PROJECT)', path: '.planning/PROJECT.md', description: 'Roadmap, progress, canonical document index' },
  { label: 'Build in 1 hour (BUILD_1HR)', path: 'BUILD_1HR.md', description: 'Quick start and E2E document test' },
  { label: 'Deploy for Frosty', path: 'docs/operations/DEPLOY_FOR_FROSTY.md', description: 'Deployment plan: Vercel + backend, onboarding' },
]

function docUrl(path: string): string {
  const base = DOCS_BASE.replace(/\/$/, '')
  return `${base}/${path}`
}

export default function Onboard() {
  return (
    <div>
      <h2 className="text-lg font-medium uppercase tracking-wider text-text-secondary mb-2">
        ONBOARDING
      </h2>
      <p className="text-text-secondary text-sm mb-6">
        All onboarding material. Open in a new tab. Replace VITE_DOCS_BASE with your repo or docs site.
      </p>
      <ul className="space-y-3">
        {onboardingLinks.map((item) => (
          <li key={item.path} className="bg-surface border border-border p-4" style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }}>
            <a
              href={docUrl(item.path)}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-accent hover:underline"
            >
              {item.label}
            </a>
            <p className="text-text-secondary text-xs mt-1">{item.description}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}
