import React, { useState, useEffect } from 'react'
import { repoApi, chatApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import './Sidebar.css'

const MODE_COLORS = {
  agentic: { bg: 'var(--accent-dim)', color: 'var(--accent)',  label: 'task' },
  rag:     { bg: 'var(--purple-dim)', color: 'var(--purple)',  label: 'rag'  },
  general: { bg: 'var(--border)',     color: 'var(--text-secondary)', label: 'chat' },
  defect:  { bg: 'var(--red-dim)',    color: 'var(--red)',     label: 'defect'  },
  feature: { bg: 'var(--blue-dim)',   color: 'var(--blue)',    label: 'feature' },
}

function Badge({ mode }) {
  const cfg = MODE_COLORS[mode] || MODE_COLORS.general
  return (
    <span
      className="conv-badge"
      style={{ background: cfg.bg, color: cfg.color }}
    >{cfg.label}</span>
  )
}

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr)
  const m = Math.floor(diff / 60000)
  if (m < 1)  return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export default function Sidebar({
  selectedNamespace,
  onNamespaceChange,
  selectedConv,
  onSelectConv,
  onNewChat,
  refreshTrigger,
}) {
  const { user, logout }            = useAuth()
  const [repos,         setRepos]   = useState([])
  const [conversations, setConvs]   = useState([])
  const [showRepoModal, setRepoModal] = useState(false)
  const [repoUrl,       setRepoUrl] = useState('')
  const [syncBranch,    setSyncBranch] = useState('main')
  const [repoLoading,   setRepoLoading] = useState(false)
  const [repoError,     setRepoError]   = useState('')

  useEffect(() => {
    repoApi.list().then(r => setRepos(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    chatApi.getConversations()
      .then(r => setConvs(r.data))
      .catch(() => {})
  }, [refreshTrigger])

  const ingestRepo = async () => {
    setRepoError('')
    setRepoLoading(true)
    try {
      const res = await repoApi.ingest(repoUrl, syncBranch)
      setRepos(prev => [...prev, res.data])
      onNamespaceChange(res.data.vector_namespace)
      setRepoModal(false)
      setRepoUrl('')
    } catch (err) {
      setRepoError(err.response?.data?.detail || 'Ingestion failed')
    } finally {
      setRepoLoading(false)
    }
  }

  const deleteConv = async (e, id) => {
    e.stopPropagation()
    await chatApi.deleteConversation(id)
    setConvs(prev => prev.filter(c => c.conversation_id !== id))
    if (selectedConv === id) onNewChat()
  }

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="brand-mark">S</div>
        <span className="brand-name">Synthr</span>
      </div>

      {/* Repo Selector */}
      <div className="sidebar-section-block">
        <div className="section-label">Repository</div>
        <div className="repo-selector">
          <select
            value={selectedNamespace || ''}
            onChange={e => onNamespaceChange(e.target.value || null)}
          >
            <option value="">No repository selected</option>
            {repos.map(r => (
              <option key={r.repo_id} value={r.vector_namespace}>
                {r.vector_namespace}
              </option>
            ))}
          </select>
          <button className="repo-add-btn" onClick={() => setRepoModal(true)} title="Add repository">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="sidebar-section-block">
        <button className="new-chat-btn" onClick={onNewChat}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          New conversation
        </button>
      </div>

      {/* Conversations */}
      <div className="section-label" style={{ padding: '0 14px', marginBottom: 6 }}>Conversations</div>
      <div className="conv-list">
        {conversations.length === 0 && (
          <div className="conv-empty">No conversations yet</div>
        )}
        {conversations.map(c => (
          <div
            key={c.conversation_id}
            className={`conv-item ${selectedConv === c.conversation_id ? 'active' : ''}`}
            onClick={() => onSelectConv(c.conversation_id)}
          >
            <div className="conv-top">
              <Badge mode={c.mode || c.ticket_type || 'general'} />
              <span className="conv-time">{timeAgo(c.created_at)}</span>
            </div>
            <div className="conv-title">
              {c.ticket_description || 'Untitled conversation'}
            </div>
            <div className="conv-status-row">
              <span className={`conv-status ${c.status}`}>{c.status}</span>
              <button
                className="conv-delete"
                onClick={e => deleteConv(e, c.conversation_id)}
                title="Delete"
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* User Footer */}
      <div className="sidebar-footer">
        <div className="user-info">
          <div className="user-avatar">{user?.email?.[0]?.toUpperCase()}</div>
          <span className="user-email">{user?.email}</span>
        </div>
        <button className="logout-btn" onClick={logout} title="Sign out">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M5 2H2.5A1.5 1.5 0 001 3.5v7A1.5 1.5 0 002.5 12H5M9 10l3-3-3-3M12 7H5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>

      {/* Repo Ingest Modal */}
      {showRepoModal && (
        <div className="modal-overlay" onClick={() => setRepoModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span>Add repository</span>
              <button onClick={() => setRepoModal(false)}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </button>
            </div>
            <div className="modal-body">
              <div className="field">
                <label>GitHub URL</label>
                <input
                  type="url"
                  value={repoUrl}
                  onChange={e => setRepoUrl(e.target.value)}
                  placeholder="https://github.com/owner/repo"
                />
              </div>
              <div className="field">
                <label>Sync branch</label>
                <input
                  type="text"
                  value={syncBranch}
                  onChange={e => setSyncBranch(e.target.value)}
                  placeholder="main"
                />
              </div>
              {repoError && <div className="modal-error">{repoError}</div>}
              <button
                className="modal-submit"
                onClick={ingestRepo}
                disabled={repoLoading || !repoUrl}
              >
                {repoLoading
                  ? <><span className="spinner-sm"></span> Ingesting...</>
                  : 'Ingest repository'
                }
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}
