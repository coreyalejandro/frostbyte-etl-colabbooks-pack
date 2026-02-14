// ISSUE #1-10: Added Observatory route
// REASONING: Model observability page integration
// ADDED BY: Kombai on 2026-02-14

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { TenantProvider } from './contexts/TenantContext'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Observatory from './pages/Observatory'
import TenantList from './pages/TenantList'
import TenantDetail from './pages/TenantDetail'
import DocumentList from './pages/DocumentList'
import DocumentDetail from './pages/DocumentDetail'
import JobList from './pages/JobList'
import JobDetail from './pages/JobDetail'
import Verify from './pages/Verify'
import Control from './pages/Control'
import Audit from './pages/Audit'
import Onboard from './pages/Onboard'
import Settings from './pages/Settings'
import Login from './pages/Login'

const queryClient = new QueryClient()

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/admin">
        <AuthProvider>
          <TenantProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <Layout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Dashboard />} />
                <Route path="observatory" element={<Observatory />} />
                <Route path="tenants" element={<TenantList />} />
                <Route path="tenants/:id" element={<TenantDetail />} />
                <Route path="documents" element={<DocumentList />} />
                <Route path="documents/:id" element={<DocumentDetail />} />
                <Route path="jobs" element={<JobList />} />
                <Route path="jobs/:id" element={<JobDetail />} />
                <Route path="verify" element={<Verify />} />
                <Route path="control" element={<Control />} />
                <Route path="audit" element={<Audit />} />
                <Route path="onboard" element={<Onboard />} />
                <Route path="settings" element={<Settings />} />
              </Route>
            </Routes>
          </TenantProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
