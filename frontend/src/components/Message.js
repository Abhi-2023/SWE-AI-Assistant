import React from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import './Message.css'

const AGENT_LABELS = {
  router_node:                    'Router',
  classifier_understand_agent:    'Classifier',
  planner_agent:                  'Planner',
  code_writer_agent:              'Code writer',
  test_debug_agent:               'Test runner',
  git_agent:                      'Git agent',
  general_node:                   'LLM',
  rag_node:                       'Retriever',
  agentic_node:                   'Agent pipeline',
  no_namespace_node:              'Router',
  retriever:                      'Retriever',
  llm:                            'LLM',
}

function AgentSteps({ steps, isStreaming }) {
  if (!steps || steps.length === 0) return null
  return (
    <div className="steps-card">
      {steps.map((s, i) => {
        const isLast   = i === steps.length - 1
        const isActive = isLast && isStreaming
        return (
          <div key={i} className="step-row">
            <div className={`step-dot ${isActive ? 'active' : 'done'}`}></div>
            <span className="step-name">
              {AGENT_LABELS[s.agent] || s.agent}
            </span>
            <span className={`step-status ${isActive ? 'running' : ''}`}>
              {isActive ? 'running...' : s.status}
            </span>
          </div>
        )
      })}
    </div>
  )
}

function PRCard({ pr }) {
  return (
    <div className="pr-card">
      <div className="pr-header">
        <div className="pr-icon">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <circle cx="4" cy="4" r="2" stroke="currentColor" strokeWidth="1.5"/>
            <circle cx="12" cy="12" r="2" stroke="currentColor" strokeWidth="1.5"/>
            <circle cx="12" cy="4" r="2" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M4 6v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M12 6v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M6 4h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </div>
        <div className="pr-info">
          <div className="pr-title">{pr.pr_title || 'Pull request opened'}</div>
          <a className="pr-link" href={pr.pr_url} target="_blank" rel="noreferrer">
            {pr.pr_url}
          </a>
        </div>
        <a href={pr.pr_url} target="_blank" rel="noreferrer" className="pr-open-btn">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M2 10L10 2M10 2H4M10 2v6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </a>
      </div>
      <div className="pr-meta">
        {pr.tests_passed !== undefined && (
          <span className={`pr-tag ${pr.tests_passed ? 'green' : 'red'}`}>
            {pr.tests_passed
              ? <><svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 5l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg> Tests passed</>
              : <><svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 2l6 6M8 2L2 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg> Tests failed</>
            }
          </span>
        )}
        {pr.files_changed?.map?.((f, i) => (
          <span key={i} className="pr-tag file">{f}</span>
        ))}
      </div>
    </div>
  )
}

function ModeTag({ mode }) {
  const cfg = {
    rag:     { label: 'rag query',    color: 'var(--purple)' },
    general: { label: 'general chat', color: 'var(--text-tertiary)' },
    agentic: { label: 'agent task',   color: 'var(--accent)' },
  }
  const c = cfg[mode]
  if (!c) return null
  return (
    <div className="mode-tag" style={{ color: c.color }}>
      <span className="mode-dot" style={{ background: c.color }}></span>
      {c.label}
    </div>
  )
}

export function UserMessage({ content }) {
  return (
    <div className="msg user">
      <div className="msg-bubble user-bubble">
        {content}
      </div>
    </div>
  )
}

export function AssistantMessage({ message, isStreaming }) {
  const { content, agent_steps, pr_url, pr_title, files_changed, tests_passed, mode } = message

  return (
    <div className="msg assistant">
      <div className="msg-avatar">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <rect x="1" y="3" width="12" height="8" rx="2" stroke="currentColor" strokeWidth="1.2"/>
          <path d="M4 6h6M4 8.5h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
        </svg>
      </div>
      <div className="msg-body">

        {mode && <ModeTag mode={mode} />}

        {/* thinking dots — show only when streaming with nothing yet */}
        {isStreaming && !content && !pr_url && agent_steps?.length === 0 && (
          <div className="thinking">
            <span></span><span></span><span></span>
          </div>
        )}

        {/* agent steps — show as they stream in */}
        {agent_steps?.length > 0 && (
          <AgentSteps steps={agent_steps} isStreaming={isStreaming} />
        )}

        {/* PR card */}
        {pr_url && (
          <PRCard pr={{ pr_url, pr_title, files_changed, tests_passed }} />
        )}

        {/* text response */}
        {content && content !== pr_url && (
          <div className="msg-bubble ai-bubble">
            <ReactMarkdown
              components={{
                code({ node, inline, className, children, ...props }) {
                  const lang = /language-(\w+)/.exec(className || '')?.[1]
                  return !inline && lang ? (
                    <SyntaxHighlighter
                      style={oneDark}
                      language={lang}
                      PreTag="div"
                      customStyle={{
                        borderRadius: '8px',
                        fontSize: '12px',
                        margin: '8px 0',
                        border: '1px solid var(--border)',
                      }}
                      {...props}
                    >{String(children).replace(/\n$/, '')}</SyntaxHighlighter>
                  ) : (
                    <code className={className} {...props}>{children}</code>
                  )
                }
              }}
            >{content}</ReactMarkdown>
            {isStreaming && <span className="cursor-blink">▋</span>}
          </div>
        )}

      </div>
    </div>
  )
}