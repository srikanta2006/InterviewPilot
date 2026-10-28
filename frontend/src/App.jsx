import { useState, useEffect } from 'react'
import { DocumentSetup } from './components/DocumentSetup'
import { KnowledgeBase } from './components/KnowledgeBase'
import { InterviewWorkspace } from './components/InterviewWorkspace'
import { InterviewHistory } from './components/InterviewHistory'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

function App() {
  const [activeTab, setActiveTab] = useState('profile') // 'profile' | 'knowledge' | 'interview' | 'history'
  const [resumeSessionId, setResumeSessionId] = useState(null)
  const [healthStatus, setHealthStatus] = useState('checking') // 'online' | 'offline' | 'checking'
  const [latency, setLatency] = useState(null)

  // Profile and Job data extracted in Stage 1 passed forward to Stage 3
  const [candidateProfile, setCandidateProfile] = useState(null)
  const [jobRequirements, setJobRequirements] = useState(null)

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
          setLatency(duration)
          setHealthStatus('online')
        } else {
          setHealthStatus('offline')
        }
      })
      .catch(() => {
        if (!active) return
        setHealthStatus('offline')
      })

    return () => {
      active = false
    }
  }, [])

  const handleParsedDocuments = (result) => {
    if (result?.candidate_profile) {
      setCandidateProfile(result.candidate_profile)
    }
    if (result?.job_requirements) {
      setJobRequirements(result.job_requirements)
    }
  }

  return (
    <div className="app-container">
      {/* Navigation / Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-icon">IP</div>
          <div>
            <h1 className="brand-title">InterviewPilot</h1>
            <p className="brand-subtitle">AI-Powered Adaptive Technical Interview Platform</p>
          </div>
        </div>

        <div className="header-status-badge">
          <span className={`status-dot ${healthStatus}`} />
          <span className="status-label">
            {healthStatus === 'online'
              ? `System Online (${latency !== null ? `${latency}ms` : 'Ready'})`
              : healthStatus === 'offline'
              ? 'Backend Offline'
              : 'Connecting...'}
          </span>
        </div>
      </header>

      {/* Main Workspace Navigation Tabs - Ordered Stage 1 through Stage 4 */}
      <nav className="nav-tabs-bar">
        <button
          type="button"
          id="tab-btn-documents"
          className={`nav-tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
          onClick={() => setActiveTab('profile')}
        >
          📄 1. Candidate & Job Setup
        </button>
        <button
          type="button"
          id="tab-btn-knowledge"
          className={`nav-tab-btn ${activeTab === 'knowledge' ? 'active' : ''}`}
          onClick={() => setActiveTab('knowledge')}
        >
          🧠 2. Knowledge Base (RAG)
        </button>
        <button
          type="button"
          id="tab-btn-interview"
          className={`nav-tab-btn ${activeTab === 'interview' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('interview')
            setResumeSessionId(null)
          }}
        >
          🎙️ 3. Practice Interview
        </button>
        <button
          type="button"
          id="tab-btn-history"
          className={`nav-tab-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          📜 4. Session History
        </button>
      </nav>

      {/* Main Workspace View */}
      <main className="main-content-area">
        {activeTab === 'profile' ? (
          <DocumentSetup
            apiBase={API_BASE}
            onParsed={handleParsedDocuments}
            onProceedToKnowledge={() => setActiveTab('knowledge')}
            onProceedToInterview={() => setActiveTab('interview')}
          />
        ) : activeTab === 'knowledge' ? (
          <KnowledgeBase
            apiBase={API_BASE}
            onProceedToInterview={() => setActiveTab('interview')}
          />
        ) : activeTab === 'interview' ? (
          <InterviewWorkspace
            apiBase={API_BASE}
            activeSessionId={resumeSessionId}
            onViewHistory={() => setActiveTab('history')}
            candidateProfile={candidateProfile}
            jobRequirements={jobRequirements}
          />
        ) : (
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
        )}
      </main>

      {/* Clean Minimal Product Footer */}
      <footer className="app-footer-clean">
        <p>InterviewPilot — Adaptive AI Technical Interviews Grounded in Real Architectural References</p>
      </footer>
    </div>
  )
}

export default App
