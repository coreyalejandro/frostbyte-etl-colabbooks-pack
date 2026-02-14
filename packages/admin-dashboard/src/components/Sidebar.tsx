import { Link, useLocation } from 'react-router-dom'

const nav: { label: string; href: string }[] = [
  { label: 'DASH', href: '/' },
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
          >
            [{item.label}]
          </Link>
        )
      })}
    </nav>
  )
}
