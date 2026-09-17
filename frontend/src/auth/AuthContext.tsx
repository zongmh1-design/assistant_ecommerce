import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { PropsWithChildren } from 'react'
import { getCurrentUser, login as requestLogin } from '../api/auth'
import {
  clearStoredToken,
  getStoredToken,
  setUnauthorizedHandler,
  storeToken,
} from '../api/client'
import type { User } from '../types/auth'

interface AuthContextValue {
  token: string | null
  currentUser: User | null
  isAuthenticated: boolean
  loading: boolean
  canWrite: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(() => getStoredToken())
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(Boolean(token))

  const logout = useCallback(() => {
    clearStoredToken()
    setToken(null)
    setCurrentUser(null)
    setLoading(false)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    return () => setUnauthorizedHandler(null)
  }, [logout])

  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    let active = true
    setLoading(true)
    getCurrentUser()
      .then((user) => {
        if (active) setCurrentUser(user)
      })
      .catch(() => {
        if (active) logout()
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [token, logout])

  const login = useCallback(async (username: string, password: string) => {
    const response = await requestLogin(username, password)
    storeToken(response.access_token)
    setToken(response.access_token)
    const user = await getCurrentUser()
    setCurrentUser(user)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      currentUser,
      isAuthenticated: Boolean(token && currentUser),
      loading,
      canWrite: currentUser?.role === 'admin' || currentUser?.role === 'operator',
      login,
      logout,
    }),
    [token, currentUser, loading, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
