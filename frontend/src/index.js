import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import App from './components/App'
import Auth from './pages/Auth'
import './index.css'

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div style={{
      height: '100vh', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-primary)'
    }}>
      <div style={{
        width: 32, height: 32,
        border: '2px solid var(--border)',
        borderTopColor: 'var(--accent)',
        borderRadius: '50%',
        animation: 'spin 0.6s linear infinite'
      }} />
    </div>
  )
  return user ? children : <Navigate to="/login" />
}

const root = ReactDOM.createRoot(document.getElementById('root'))
root.render(
  <AuthProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Auth />} />
        <Route path="/" element={
          <PrivateRoute><App /></PrivateRoute>
        } />
      </Routes>
    </BrowserRouter>
  </AuthProvider>
)
