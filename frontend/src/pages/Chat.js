import React, { useState, useEffect, useRef, useCallback } from 'react'
import { chatApi, streamChat } from '../services/api'
import { UserMessage, AssistantMessage } from '../components/Message'
import './Chat.css'

const PLACEHOLDERS = [
  'Describe a bug to fix, a feature to build, or ask about your codebase...',
  'e.g. "Fix the 500 error on /auth/login"',
  'e.g. "How does the ingestion pipeline work?"',
  'e.g. "Add rate limiting to all API routes"',
]

export default function Chat({ conversationId, selectedNamespace, onConversationCreated }) {
  const [messages,     setMessages]     = useState([])
  const [input,        setInput]        = useState('')
  const [streaming,    setStreaming]    = useState(false)
  const [activeConvId, setActiveConvId] = useState(conversationId)
  const [placeholder,  setPlaceholder] = useState(PLACEHOLDERS[0])
  const bottomRef  = useRef(null)
  const inputRef   = useRef(null)
  const phInterval = useRef(null)

  useEffect(() => {
    let i = 0
    phInterval.current = setInterval(() => {
      i = (i + 1) % PLACEHOLDERS.length
      setPlaceholder(PLACEHOLDERS[i])
    }, 4000)
    return () => clearInterval(phInterval.current)
  }, [])

  useEffect(() => {
    setActiveConvId(conversationId)
    if (conversationId) {
      chatApi.getMessages(conversationId)
        .then(res => setMessages(res.data.map(m => ({
          id:            m.id,
          role:          m.role,
          content:       m.content,
          agent_steps:   m.agent_steps || [],
          pr_url:        m.pr_url,
          files_changed: m.files_changed,
          tests_passed:  null,
          mode:          m.mode || null,
        }))))
        .catch(() => {})
    } else {
      setMessages([])
    }
  }, [conversationId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = useCallback(async () => {
    if (!input.trim() || streaming) return
    const text = input.trim()
    setInput('')
    setStreaming(true)

    const userMsg = { id: Date.now(), role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])

    const aiMsg = {
      id:            Date.now() + 1,
      role:          'assistant',
      content:       '',
      agent_steps:   [],
      pr_url:        null,
      pr_title:      null,
      files_changed: [],
      tests_passed:  null,
      mode:          null,
    }
    setMessages(prev => [...prev, aiMsg])

    const payload = {
      message:          text,
      vector_namespace: selectedNamespace || null,
      conversation_id:  activeConvId || null,
    }

    streamChat(
      payload,
      // ── onEvent ──────────────────────────────────────
      (event) => {
        setMessages(prev => {
          const msgs = [...prev]
          const last = { ...msgs[msgs.length - 1] }

          if (event.type === 'step') {
            last.agent_steps = [...(last.agent_steps || []), event]
            if (event.agent === 'rag_node')     last.mode = 'rag'
            if (event.agent === 'agentic_node') last.mode = 'agentic'
            if (event.agent === 'general_node') last.mode = 'general'
          }
          else if (event.type === 'message') {
            last.content = event.content
            last.mode    = last.mode || 'general'
          }
          else if (event.type === 'pr') {
            last.pr_url        = event.pr_url
            last.pr_title      = event.pr_title
            last.files_changed = event.files_changed
            last.tests_passed  = event.tests_passed
            last.mode          = 'agentic'
          }
          else if (event.type === 'error') {
            last.content = `Error: ${event.detail}`
          }

          msgs[msgs.length - 1] = last
          return msgs
        })
      },
      // ── onDone ───────────────────────────────────────
      () => {
        setStreaming(false)
        setMessages(prev => [...prev])   // ✅ force re-render so isStreaming=false
        onConversationCreated?.()
      },
      // ── onError ──────────────────────────────────────
      (err) => {
        setStreaming(false)
        setMessages(prev => {
          const msgs = [...prev]
          msgs[msgs.length - 1] = {
            ...msgs[msgs.length - 1],
            content: `Connection error: ${err.message}`,
          }
          return msgs
        })
      }
    )
  }, [input, streaming, selectedNamespace, activeConvId, onConversationCreated])

  const onKeyDown = e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div className="chat-shell">

      {isEmpty && (
        <div className="chat-empty">
          <div className="empty-logo">S</div>
          <h2>What can I help you build?</h2>
          <p>
            {selectedNamespace
              ? <>Connected to <code>{selectedNamespace}</code> — ask a question, submit a ticket, or just chat.</>
              : 'Select a repository from the sidebar to get started, or just chat.'
            }
          </p>
          <div className="empty-chips">
            {['Fix a bug', 'Explain the codebase', 'Add a feature', 'Just chat'].map(c => (
              <button
                key={c}
                className="chip"
                onClick={() => { setInput(c); inputRef.current?.focus() }}
              >{c}</button>
            ))}
          </div>
        </div>
      )}

      <div className="messages-area">
        {messages.map((m, i) => (
          m.role === 'user'
            ? <UserMessage key={m.id || i} content={m.content} />
            : <AssistantMessage
                key={m.id || i}
                message={m}
                isStreaming={streaming && i === messages.length - 1}
              />
        ))}
        <div ref={bottomRef} />
      </div>

      {selectedNamespace && (
        <div className="ns-bar">
          <span className="ns-dot"></span>
          <span className="ns-label">{selectedNamespace}</span>
        </div>
      )}

      <div className="input-area">
        <div className="input-wrap">
          <textarea
            ref={inputRef}
            className="input-box"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={placeholder}
            rows={1}
            disabled={streaming}
          />
          <button
            className={`send-btn ${streaming ? 'loading' : ''}`}
            onClick={send}
            disabled={!input.trim() || streaming}
          >
            {streaming
              ? <span className="spinner-sm dark"></span>
              : <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M2 8h12M9 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
            }
          </button>
        </div>
        <div className="input-hint">Enter to send · Shift+Enter for new line</div>
      </div>
    </div>
  )
}