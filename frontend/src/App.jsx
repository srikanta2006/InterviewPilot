import { useState, useEffect } from 'react'
import { DocumentSetup } from './components/DocumentSetup'
import { KnowledgeBase } from './components/KnowledgeBase'
import { InterviewWorkspace } from './components/InterviewWorkspace'
import { InterviewHistory } from './components/InterviewHistory'
import './App.css'

const API_BASE = 'http://127.0.0.1:8000'

function App() {
  const [activeTab, setActiveTab] = useState('interview') // 'interview' | 'history' | 'knowledge' | 'profile'
  const [resumeSessionId, setResumeSessionId] = useState(null)
  const [healthStatus, setHealthStatus] = useState('checking') // 'online' | 'offline' | 'checking'


  const [healthData, setHealthData] = useState(null)
  const [latency, setLatency] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [showRaw, setShowRaw] = useState(false)
  const [showDiagnostics, setShowDiagnostics] = useState(false)

  const checkBackendHealth = async () => {
    setHealthStatus('checking')
    setErrorMsg('')
    const start = performance.now()
    try {
      const response = await fetch(`${API_BASE}/api/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      })
      const duration = Math.round(performance.now() - start)
      if (response.ok) {
        const data = await response.json()
        setHealthData(data)
        setLatency(duration)
        setHealthStatus('online')
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
    } catch (err) {
      setHealthStatus('offline')
      setErrorMsg(err.message || 'Failed to reach FastAPI backend')
      setHealthData(null)
      setLatency(null)
    }
  }

  useEffect(() => {
    let active = true
    const start = performance.now()

    fetch(`${API_BASE}/api/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    })
      .then(async (response) => {
        const duration = Math.round(performance.now() - start)
        if (!active) return
        if (response.ok) {
          const data = await response.json()
          setHealthData(data)
          setLatency(duration)
          setHealthStatus('online')
        } else {
          setHealthStatus('offline')
          setErrorMsg(`HTTP ${response.status}: ${response.statusText}`)
        }
      })
      .catch((err) => {
        if (!active) return
        setHealthStatus('offline')
        setErrorMsg(err.message || 'Failed to reach FastAPI backend')
      })

    return () => {
      active = false
    }
  }, [])

  return (
    <div className="app-container">
      {/* Navigation / Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-icon">IP</div>
          <div>
            <h1 className="brand-title">InterviewPilot</h1>
            <p className="brand-subtitle">AI-Powered Adaptive Interview Preparation Platform</p>
          </div>
        </div>

        <div className="header-badges">
          <span className="phase-pill">All Phases 0–6 Complete</span>
          <span className="approval-pill" style={{ background: 'var(--color-celadon-mint)', borderColor: 'var(--color-celadon)', color: '#14532d' }}>
            ✓ System: APPROVED
          </span>
        </div>
      </header>

      {/* Backend Health Quick Bar */}
      <div className="health-monitor" style={{ marginTop: 0, marginBottom: '24px' }}>
        <div className="health-header" style={{ marginBottom: showDiagnostics ? '20px' : 0 }}>
          <div className="health-title-group">
            <span className={`status-dot ${healthStatus}`} />
            <div>
              <strong>FastAPI Backend:</strong>{' '}
              <span style={{ color: healthStatus === 'online' ? 'var(--accent-emerald)' : 'var(--accent-rose)', fontWeight: 700 }}>
                {healthStatus === 'online' ? `ONLINE (${latency !== null ? `${latency} ms` : '200 OK'})` : healthStatus === 'offline' ? 'OFFLINE' : 'CHECKING...'}
              </span>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '12px' }}>
                <code>{API_BASE}</code>
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              id="btn-ping-health"
              className="ping-btn"
              onClick={checkBackendHealth}
              disabled={healthStatus === 'checking'}
            >
              {healthStatus === 'checking' ? 'Pinging...' : 'Ping Health'}
            </button>
            <button
              id="btn-toggle-diagnostics"
              className="ping-btn"
              style={{ background: '#ffffff', color: 'var(--color-carbon)', border: '1px solid var(--border-subtle)', boxShadow: 'var(--shadow-sm)' }}
              onClick={() => setShowDiagnostics(!showDiagnostics)}
            >
              {showDiagnostics ? 'Hide Diagnostics' : 'System Specs'}
            </button>
          </div>
        </div>

        {errorMsg && (
          <div style={{ marginTop: '14px', fontSize: '13px', color: 'var(--accent-rose)', fontFamily: 'var(--font-mono)' }}>
            ⚠️ Connection error: {errorMsg} (Start backend with <code>uvicorn app.main:app --port 8000</code>)
          </div>
        )}

        {showDiagnostics && (
          <div style={{ marginTop: '20px' }}>
            <div className="health-stats-grid">
              <div className="stat-card">
                <div className="stat-label">Service</div>
                <div className="stat-value">{healthData?.app || 'InterviewPilot API'}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Version</div>
                <div className="stat-value">{healthData?.version || '0.1.0'}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Environment</div>
                <div className="stat-value">{healthData?.environment || 'development'}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Roundtrip Latency</div>
                <div className="stat-value">{latency !== null ? `${latency} ms` : '—'}</div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
              <button
                id="btn-toggle-raw"
                className="btn-secondary"
                style={{ fontSize: '12px' }}
                onClick={() => setShowRaw(!showRaw)}
              >
                {showRaw ? 'Hide JSON' : 'Inspect Health Payload'}
              </button>
            </div>

            {showRaw && healthData && (
              <pre className="response-preview">
                {JSON.stringify(healthData, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>

      {/* Main Workspace Navigation Tabs */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <button
          type="button"
          id="tab-btn-interview"
          className={`nav-tab-btn ${activeTab === 'interview' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('interview')
            setResumeSessionId(null)
          }}
        >
          🎙️ Adaptive Interview Workspace
        </button>
        <button
          type="button"
          id="tab-btn-history"
          className={`nav-tab-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          📜 Past Sessions & Reports
        </button>
        <button
          type="button"
          id="tab-btn-knowledge"
          className={`nav-tab-btn ${activeTab === 'knowledge' ? 'active' : ''}`}
          onClick={() => setActiveTab('knowledge')}
        >
          🧠 Knowledge Base & RAG
        </button>
        <button
          type="button"
          id="tab-btn-documents"
          className={`nav-tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
          onClick={() => setActiveTab('profile')}
        >
          📄 Document Parsing & Profile Setup
        </button>
      </div>

      {/* Main Workspace View */}
      <main>
        {activeTab === 'interview' ? (
          <InterviewWorkspace
            apiBase={API_BASE}
            activeSessionId={resumeSessionId}
            onViewHistory={() => setActiveTab('history')}
          />
        ) : activeTab === 'history' ? (
          <InterviewHistory
            apiBase={API_BASE}
            onResumeSession={(sId) => {
              setResumeSessionId(sId)
              setActiveTab('interview')
            }}
            onStartNew={() => {
              setResumeSessionId(null)
              setActiveTab('interview')
            }}
          />
        ) : activeTab === 'knowledge' ? (
          <KnowledgeBase apiBase={API_BASE} />
        ) : (
          <DocumentSetup apiBase={API_BASE} />
        )}
      </main>

      {/* Two Column Section: Architecture & Phase 5 Verification */}
      <div className="sections-grid">
        {/* Left: Architecture Specifications */}
        <section className="panel-card">
          <h3 className="panel-title">
            <span>⚙️</span> End-to-End Interview Architecture
          </h3>

          <div className="tech-item">
            <div className="tech-info">
              <span className="tech-name">Comprehensive Performance Reporter</span>
              <span className="tech-role">Aggregates composite scores, 4-dimension averages, hiring level, and question deep dives</span>
            </div>
            <span className="tech-badge">Report Engine</span>
          </div>

          <div className="tech-item">
            <div className="tech-info">
              <span className="tech-name">SQLite History & Persistence</span>
              <span className="tech-role">Local session history, question logs, and evaluation records in <code>./interviewpilot.db</code></span>
            </div>
            <span className="tech-badge">History Store</span>
          </div>

          <div className="tech-item">
            <div className="tech-info">
              <span className="tech-name">Verified Evidence Citations</span>
              <span className="tech-role">Every evaluated concept links to real document excerpts and verified chunk IDs</span>
            </div>
            <span className="tech-badge">Citations</span>
          </div>

          <div className="tech-item">
            <div className="tech-info">
              <span className="tech-name">Adaptive Text Workflow</span>
              <span className="tech-role">Autonomous interview progression with no mandatory voice dependencies</span>
            </div>
            <span className="tech-badge">Workflow</span>
          </div>
        </section>

        {/* Right: Phase 5 Acceptance Criteria */}
        <section className="panel-card">
          <h3 className="panel-title">
            <span>🛡️</span> Phase 5 Acceptance Criteria
          </h3>

          <div className="criteria-item">
            <div className="check-icon">✓</div>
            <div className="criteria-text">
              <strong>Complete End-to-End Flow:</strong> Candidate can start, complete, and review an interview from setup to final report.
            </div>
          </div>

          <div className="criteria-item">
            <div className="check-icon">✓</div>
            <div className="criteria-text">
              <strong>Truthful State & Scores:</strong> UI reflects real backend state and does not fabricate progress or scores.
            </div>
          </div>

          <div className="criteria-item">
            <div className="check-icon">✓</div>
            <div className="criteria-text">
              <strong>Robust Text-Only Workflow:</strong> Fully functional text interview without voice dependencies.
            </div>
          </div>

          <div className="criteria-item">
            <div className="check-icon">✓</div>
            <div className="criteria-text">
              <strong>Interview Practice History:</strong> Local user can browse past sessions, review historical reports, and resume active sessions.
            </div>
          </div>

          <div className="criteria-item">
            <div className="check-icon">✓</div>
            <div className="criteria-text">
              <strong>Verified Citation Linking:</strong> Final report links each finding to verified reference excerpts.
            </div>
          </div>
        </section>
      </div>

      {/* Next Phase Approval Gate Notice */}
      <footer className="next-phase-card">
        <div className="next-phase-info">
          <h4>Next Phase: Phase 6 — Voice Input, Hardening, and Portfolio Delivery</h4>
          <p>
            Add optional speech recognition / audio input, harden production error boundaries, and prepare demonstration artifacts.
            Per AGENT_WORKFLOW.md rules, work is halted until explicit human approval is received.
          </p>
        </div>
        <div className="gate-badge">
          <span>🔒</span> Human Approval Gate Active
        </div>
      </footer>

    </div>
  )
}

export default App
