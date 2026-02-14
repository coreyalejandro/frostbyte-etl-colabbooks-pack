import { Link, useLocation } from 'react-router-dom'

// ISSUE #1-10: Added Observatory navigation
// REASONING: Access to model observability features
// ADDED BY: Kombai on 2026-02-14

const nav: { label: string; href: string }[] = [
  { label: 'DASH', href: '/' },
  { label: 'OBSERVATORY', href: '/observatory' },
  { label: 'TENANTS', href: '/tenants' },
  { label: 'DOCS', href: '/documents' },
  { label: 'VERIFY', href: '/verify' },
  { label: 'CONTROL', href: '/control' },
  { label: 'AUDIT', href: '/audit' },
  { label: 'ONBOARD', href: '/onboard' },
]

export default function Sidebar() {
  const location = useLocation()
  return (
    <nav className="flex gap-1">
      {nav.map((item) => {
        const isActive =
          location.pathname === item.href || location.pathname.startsWith(item.href + '/')
        return (
          <Link
            key={item.label}
            to={item.href}
            className={`px-3 py-2 text-xs font-medium uppercase tracking-wider border ${
              isActive
                ? 'border-accent text-text-primary bg-surface'
                : 'border-border text-text-secondary hover:border-inactive'
            }`}
            aria-label={`Navigate to ${item.label}`}
            aria-current={isActive ? 'page' : undefined}
          >
            [{item.label}]
          </Link>
        )
      })}
    </nav>
  )
}
