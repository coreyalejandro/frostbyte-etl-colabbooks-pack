import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { isMockMode } from '../api/client'

const TOKEN_TTL_MS = 30 * 60 * 1000
const WARN_BEFORE_MS = 5 * 60 * 1000
const MOCK_REFRESH_FAILURE_RATE = 0.05

export function useTokenRefresh() {
  const { isAuthenticated, logout } = useAuth()
  const [expiresIn, setExpiresIn] = useState<number | null>(null)
  const [showWarning, setShowWarning] = useState(false)
  const expiryRef = useRef<number>(Date.now() + TOKEN_TTL_MS)
  const timerRef = useRef<number | null>(null)

  const refreshToken = useCallback(async () => {
    if (!isMockMode()) return

    if (Math.random() < MOCK_REFRESH_FAILURE_RATE) {
      logout()
      return
    }

    expiryRef.current = Date.now() + TOKEN_TTL_MS
    setShowWarning(false)
    setExpiresIn(TOKEN_TTL_MS)
  }, [logout])

  useEffect(() => {
    if (!isAuthenticated) {
      setShowWarning(false)
      setExpiresIn(null)
      return
    }

    expiryRef.current = Date.now() + TOKEN_TTL_MS

    timerRef.current = window.setInterval(() => {
      const remaining = expiryRef.current - Date.now()
      setExpiresIn(remaining)

      if (remaining <= WARN_BEFORE_MS && remaining > 0) {
        setShowWarning(true)
      }

      if (remaining <= 0) {
        refreshToken()
      }
    }, 1000)

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [isAuthenticated, refreshToken])

  const dismissWarning = useCallback(() => {
    setShowWarning(false)
  }, [])

  return { expiresIn, showWarning, dismissWarning }
}
