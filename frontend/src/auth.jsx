import { createContext, useContext, useEffect, useState } from 'react'
import { api, tokenStore } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // Nothing to verify when there's no stored token, so don't start in a
  // loading state at all — that avoids a needless first render pass.
  const [loading, setLoading] = useState(() => Boolean(tokenStore.get()))

  // A token in localStorage only counts as a session if the API still accepts it.
  useEffect(() => {
    if (!tokenStore.get()) return
    api
      .me()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false))
  }, [])

  const login = async (email, password) => {
    const data = await api.login(email, password)
    tokenStore.set(data.access_token)
    setUser(data.user)
  }

  const register = async (email, password) => {
    const data = await api.register(email, password)
    tokenStore.set(data.access_token)
    setUser(data.user)
  }

  const logout = () => {
    tokenStore.clear()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
