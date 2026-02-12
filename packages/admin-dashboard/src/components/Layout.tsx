import { Outlet } from 'react-router-dom'
import Header from './Header'

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col bg-base">
      <Header />
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
