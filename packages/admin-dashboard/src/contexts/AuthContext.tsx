import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { login as apiLogin } from '../api/client'
import { setAuthToken } from '../api/client'

const TOKEN_KEY = 'frostbyte_admin_token'

interface AuthContextType {
  isAuthenticated: boolean
  login: (apiKey: string) => Promise<void>
  logout: () => void
  error: string | null
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    if (typeof window === 'undefined') return null
    return localStorage.getItem(TOKEN_KEY)
  })
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (token) {
      setAuthToken(token)
    } else {
      setAuthToken(null)
    }
  }, [token])

  const login = async (apiKey: string) => {
    setError(null)
    try {
      const { access_token } = await apiLogin(apiKey)
      localStorage.setItem(TOKEN_KEY, access_token)
      setToken(access_token)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Login failed')
      throw e
    }
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setAuthToken(null)
  }

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!token,
        login,
        logout,
        error,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
