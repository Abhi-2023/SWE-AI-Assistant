import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import './Auth.css'

export default function Auth() {
  const [mode,     setMode]     = useState('login')
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)
  const { login, register }     = useAuth()
  const navigate                = useNavigate()

  const submit = async e => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') await login(email, password)
      else await register(email, password)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-left">
        <div className="auth-brand">
          <div className="auth-logo">
            <span className="logo-s">S</span>
          </div>
          <span className="auth-wordmark">Synthr</span>
        </div>
        <div className="auth-tagline">
          <h1>Your codebase,<br />intelligently understood.</h1>
          <p>Submit tickets, explore your repo, and ship faster with AI that knows your code.</p>
        </div>
        <div className="auth-features">
          <div className="feat">
            <span className="feat-dot"></span>
            Agentic task execution with PR creation
          </div>
          <div className="feat">
            <span className="feat-dot"></span>
            Codebase-aware RAG queries
          </div>
          <div className="feat">
            <span className="feat-dot"></span>
            Auto-sync on every push
          </div>
        </div>
      </div>

      <div className="auth-right">
        <div className="auth-card">
          <div className="auth-tabs">
            <button
              className={mode === 'login' ? 'active' : ''}
              onClick={() => setMode('login')}
            >Sign in</button>
            <button
              className={mode === 'register' ? 'active' : ''}
              onClick={() => setMode('register')}
            >Create account</button>
          </div>

          <form onSubmit={submit}>
            <div className="field">
              <label>Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>
            <div className="field">
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>

            {error && <div className="auth-error">{error}</div>}

            <button type="submit" className="auth-submit" disabled={loading}>
              {loading
                ? <span className="spinner"></span>
                : mode === 'login' ? 'Sign in' : 'Create account'
              }
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
