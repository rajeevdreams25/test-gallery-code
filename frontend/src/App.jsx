import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import SharedImage from './pages/SharedImage'
import Explore from './pages/Explore'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="center muted">Loading…</div>
  return user ? children : <Navigate to="/login" replace />
}

function GuestOnly({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="center muted">Loading…</div>
  return user ? <Navigate to="/dashboard" replace /> : children
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route
            path="/login"
            element={
              <GuestOnly>
                <Login />
              </GuestOnly>
            }
          />
          <Route
            path="/register"
            element={
              <GuestOnly>
                <Register />
              </GuestOnly>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route path="/explore" element={<Explore />} />
          <Route path="/s/:token" element={<SharedImage />} />
          <Route path="*" element={<div className="center muted">Page not found</div>} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
