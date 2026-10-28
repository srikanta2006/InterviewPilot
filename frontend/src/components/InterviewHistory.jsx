import { useState, useEffect } from 'react'
import { InterviewReport } from './InterviewReport'
import './InterviewHistory.css'

export function InterviewHistory({ apiBase = 'http://127.0.0.1:8000', onResumeSession, onStartNew }) {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState('')
  const [selectedReport, setSelectedReport] = useState(null)
  const [loadingReport, setLoadingReport] = useState(false)

  useEffect(() => {
    let active = true
    fetch(`${apiBase}/api/interviews`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => {
        if (active && Array.isArray(data)) {
          setSessions(data)
        }
      })
      .catch((err) => {
        if (active) setErrorMsg(err.message || 'Error fetching interview history')
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [apiBase])

  const handleRefresh = async () => {
    setLoading(true)
    setErrorMsg('')
    try {
      const response = await fetch(`${apiBase}/api/interviews`)
      if (!response.ok) {
        throw new Error(`Failed to load sessions (HTTP ${response.status})`)
      }
      const data = await response.json()
      setSessions(Array.isArray(data) ? data : [])
    } catch (err) {
      setErrorMsg(err.message || 'Error fetching interview history')
    } finally {
      setLoading(false)
    }
  }


  const handleViewReport = async (sessionId) => {
    setLoadingReport(true)
    setErrorMsg('')
    try {
      const response = await fetch(`${apiBase}/api/interviews/${sessionId}/report`)
      if (!response.ok) {
        throw new Error(`Failed to load report (HTTP ${response.status})`)
      }
      const reportData = await response.json()
      setSelectedReport(reportData)
    } catch (err) {
      setErrorMsg(err.message || 'Error compiling interview report')
    } finally {
      setLoadingReport(false)
    }
  }

  const handleDeleteSession = async (sessionId) => {
    if (!window.confirm(`Delete interview session ${sessionId}? This cannot be undone.`)) {
      return
    }
    try {
      const response = await fetch(`${apiBase}/api/interviews/${sessionId}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        throw new Error(`Failed to delete session (HTTP ${response.status})`)
      }
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId))
      if (selectedReport?.session_id === sessionId) {
        setSelectedReport(null)
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to delete session')
    }
  }

  const handleClearAllSessions = async () => {
    if (!window.confirm('Delete all past interview sessions? This cannot be undone.')) {
      return
    }
    setLoading(true)
    setErrorMsg('')
    try {
      const response = await fetch(`${apiBase}/api/interviews`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        throw new Error(`Failed to clear history (HTTP ${response.status})`)
      }
      setSessions([])
      setSelectedReport(null)
    } catch (err) {
      setErrorMsg(err.message || 'Failed to clear history')
    } finally {
      setLoading(false)
    }
  }

  // If viewing a report from history
  if (selectedReport) {
    return (
      <div className="history-report-wrapper">
        <InterviewReport
          report={selectedReport}
          onRestart={onStartNew}
          onViewHistory={() => setSelectedReport(null)}
        />
      </div>
    )
  }

  return (
    <div className="interview-history-container">
      {/* Header */}
      <div className="history-header">
        <div>
          <h2>📜 Session History & Performance Reports</h2>
          <p>Review past interview attempts, 4-dimension rubric evaluations, and downloadable reports.</p>
        </div>
        <div className="history-actions">
          <button className="btn-secondary btn-sm" onClick={handleRefresh} disabled={loading}>
            🔄 Refresh
          </button>
          {sessions.length > 0 && (
            <button className="btn-secondary btn-sm" onClick={handleClearAllSessions} disabled={loading} title="Delete all past sessions">
              🗑️ Clear All
            </button>
          )}
          {onStartNew && (
            <button className="btn-primary btn-sm" onClick={onStartNew}>
              🚀 Start New Interview
            </button>
          )}
        </div>
      </div>

      {errorMsg && (
        <div className="error-banner">
          <span>⚠️ {errorMsg}</span>
          <button onClick={() => setErrorMsg('')}>✕</button>
        </div>
      )}

      {loadingReport && (
        <div className="loading-card">
          <div className="spinner"></div>
          <p>Compiling comprehensive interview report...</p>
        </div>
      )}

      {/* Sessions List */}
      {loading ? (
        <div className="loading-card">
          <div className="spinner"></div>
          <p>Loading past interview sessions...</p>
        </div>
      ) : sessions.length === 0 ? (
        <div className="empty-history-card">
          <div className="empty-icon">📂</div>
          <h3>No past interview sessions found</h3>
          <p>Complete your first technical interview practice session to track your performance history here.</p>
          {onStartNew && (
            <button className="btn-primary" onClick={onStartNew}>
              Start Your First Interview
            </button>
          )}
        </div>
      ) : (
        <div className="sessions-table-card">
          <table className="sessions-table">
            <thead>
              <tr>
                <th>Candidate & Target Role</th>
                <th>Session ID</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Avg Score</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => {
                const scoreClass =
                  s.avg_score >= 70 ? 'score-high' : s.avg_score >= 50 ? 'score-mid' : 'score-low'

                return (
                  <tr key={s.session_id}>
                    <td>
                      <div className="cand-info">
                        <strong>{s.candidate_name}</strong>
                        <span className="role-sub">{s.job_title}</span>
                      </div>
                    </td>
                    <td>
                      <code>{s.session_id}</code>
                    </td>
                    <td>
                      <span className={`status-badge status-${s.status}`}>
                        {s.status}
                      </span>
                    </td>
                    <td>
                      <span className="progress-text">
                        {s.questions_evaluated} / {s.total_questions} Evaluated
                      </span>
                    </td>
                    <td>
                      {s.avg_score !== null ? (
                        <span className={`score-badge ${scoreClass}`}>
                          {s.avg_score}%
                        </span>
                      ) : (
                        <span className="no-score">—</span>
                      )}
                    </td>
                    <td className="date-cell">
                      {new Date(s.created_at).toLocaleDateString()}
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="btn-action btn-view"
                          onClick={() => handleViewReport(s.session_id)}
                          title="View Final Report"
                        >
                          📊 Report
                        </button>
                        {onResumeSession && s.status !== 'completed' && (
                          <button
                            className="btn-action btn-resume"
                            onClick={() => onResumeSession(s.session_id)}
                            title="Resume Interview"
                          >
                            ▶ Resume
                          </button>
                        )}
                        <button
                          className="btn-action btn-del"
                          onClick={() => handleDeleteSession(s.session_id)}
                          title="Delete Session"
                        >
                          ✕
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
