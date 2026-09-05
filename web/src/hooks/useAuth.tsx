import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { AdminSession } from '@/types/auth'
import { getStoredSession, login as loginRequest, logout as logoutRequest } from '@/services/auth.service'

interface AuthContextValue {
  session: AdminSession | null
  isAuthenticated: boolean
  isAuthenticating: boolean
  error: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AdminSession | null>(() => getStoredSession())
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const login = useCallback(async (username: string, password: string) => {
    setIsAuthenticating(true)
    setError(null)
    try {
      const nextSession = await loginRequest(username, password)
      setSession(nextSession)
    } catch {
      setError('INVALID_CREDENTIALS')
      throw new Error('INVALID_CREDENTIALS')
    } finally {
      setIsAuthenticating(false)
    }
  }, [])

  const logout = useCallback(async () => {
    await logoutRequest()
    setSession(null)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      isAuthenticated: session !== null,
      isAuthenticating,
      error,
      login,
      logout,
    }),
    [session, isAuthenticating, error, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
