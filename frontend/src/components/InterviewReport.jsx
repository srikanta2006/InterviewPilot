import { useState } from 'react'
import './InterviewReport.css'

export function InterviewReport({ report, onRestart, onViewHistory }) {
  const [expandedQuestionId, setExpandedQuestionId] = useState(null)
  const [showAllCitations, setShowAllCitations] = useState(false)

  if (!report) {
    return (
      <div className="report-empty-card">
        <p>No report data available.</p>
        {onRestart && (
          <button className="btn-primary" onClick={onRestart}>
            Start New Interview
          </button>
        )}
      </div>
    )
  }

  const {
    session_id,
    candidate_name,
    job_title,
    total_questions,
    questions_evaluated,
    composite_score,
    performance_level,
    dimension_averages = {},
    competency_scores = {},
    question_summaries = [],
    key_strengths_summary = [],
    priority_improvements_summary = [],
    citations_summary = [],
    created_at,
  } = report

  const scoreClass =
    composite_score >= 80 ? 'score-high' : composite_score >= 65 ? 'score-mid' : 'score-low'

  const toggleExpand = (qId) => {
    setExpandedQuestionId(expandedQuestionId === qId ? null : qId)
  }

  const handlePrint = () => {
    window.print()
  }

  return (
    <div className="interview-report-container">
      {/* Report Header Card */}
      <div className="report-header-card">
        <div className="report-title-section">
          <div className="report-badge-row">
            <span className="report-tag">Technical Interview Report</span>
            <span className="report-session-id">Session: <code>{session_id}</code></span>
          </div>
          <h2>{candidate_name}</h2>
          <p className="report-subtitle">
            Evaluated for <strong>{job_title}</strong> • {questions_evaluated} of {total_questions} Competencies Assessed
          </p>
          <div className="report-meta-timestamp">
            Completed on {new Date(created_at).toLocaleDateString()} at {new Date(created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>

        {/* Big Overall Composite Score */}
        <div className="report-score-hero">
          <div className="hero-score-label">Overall Composite Score</div>
          <div className={`hero-score-value ${scoreClass}`}>
            {composite_score} <span className="hero-score-max">/ 100</span>
          </div>
          <div className="hero-performance-badge">
            {performance_level}
          </div>
        </div>
      </div>

      {/* Action Toolbar */}
      <div className="report-toolbar">
        <div className="toolbar-left">
          {onViewHistory && (
            <button className="btn-secondary btn-sm" onClick={onViewHistory}>
              ← Past Interview History
            </button>
          )}
        </div>
        <div className="toolbar-right">
          <button className="btn-secondary btn-sm" onClick={handlePrint}>
            🖨️ Print / Save PDF
          </button>
          {onRestart && (
            <button className="btn-primary btn-sm" onClick={onRestart}>
              🚀 Practice Again
            </button>
          )}
        </div>
      </div>

      {/* Grid: 4 Dimension Averages & Competency Breakdown */}
      <div className="report-metrics-grid">
        {/* Dimension Breakdown */}
        <div className="metric-panel">
          <h4 className="panel-heading">📊 Dimension Performance (Rubric Averages / 5)</h4>
          <div className="dimension-bars-list">
            <div className="dim-row">
              <div className="dim-row-label">
                <span>Correctness (30% weight)</span>
                <strong>{dimension_averages.correctness ?? 0} / 5</strong>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill fill-cyan"
                  style={{ width: `${((dimension_averages.correctness || 0) / 5) * 100}%` }}
                />
              </div>
            </div>

            <div className="dim-row">
              <div className="dim-row-label">
                <span>Completeness (30% weight)</span>
                <strong>{dimension_averages.completeness ?? 0} / 5</strong>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill fill-cyan"
                  style={{ width: `${((dimension_averages.completeness || 0) / 5) * 100}%` }}
                />
              </div>
            </div>

            <div className="dim-row">
              <div className="dim-row-label">
                <span>Relevance (20% weight)</span>
                <strong>{dimension_averages.relevance ?? 0} / 5</strong>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill fill-cyan"
                  style={{ width: `${((dimension_averages.relevance || 0) / 5) * 100}%` }}
                />
              </div>
            </div>

            <div className="dim-row">
              <div className="dim-row-label">
                <span>Clarity (20% weight)</span>
                <strong>{dimension_averages.clarity ?? 0} / 5</strong>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill fill-cyan"
                  style={{ width: `${((dimension_averages.clarity || 0) / 5) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Competency Breakdown */}
        <div className="metric-panel">
          <h4 className="panel-heading">🎯 Competency Mastery Scores</h4>
          <div className="competency-scores-list">
            {Object.keys(competency_scores).length > 0 ? (
              Object.entries(competency_scores).map(([comp, sc], idx) => {
                const cClass = sc >= 75 ? 'score-high' : sc >= 50 ? 'score-mid' : 'score-low'
                return (
                  <div key={idx} className="comp-score-item">
                    <span className="comp-name">{comp}</span>
                    <span className={`comp-pill ${cClass}`}>{sc}%</span>
                  </div>
                )
              })
            ) : (
              <p className="no-data-hint">No competency scores recorded.</p>
            )}
          </div>
        </div>
      </div>

      {/* Two Column: Top Strengths & Priority Improvements */}
      <div className="report-insights-grid">
        <div className="insight-card strengths-card">
          <h4>🌟 Top Demonstrated Strengths</h4>
          <ul>
            {key_strengths_summary.length > 0 ? (
              key_strengths_summary.map((str, sIdx) => <li key={sIdx}>{str}</li>)
            ) : (
              <li className="no-data-hint">No specific strengths captured.</li>
            )}
          </ul>
        </div>

        <div className="insight-card improvements-card">
          <h4>🎯 Priority Improvement Areas</h4>
          <ul>
            {priority_improvements_summary.length > 0 ? (
              priority_improvements_summary.map((imp, iIdx) => <li key={iIdx}>{imp}</li>)
            ) : (
              <li className="no-data-hint">No major knowledge gaps noted.</li>
            )}
          </ul>
        </div>
      </div>

      {/* Verified Grounded Evidence Citations */}
      {citations_summary.length > 0 && (
        <div className="report-citations-panel">
          <div
            className="citations-panel-header"
            onClick={() => setShowAllCitations(!showAllCitations)}
          >
            <h4>📚 Verified Technical Grounding Citations ({citations_summary.length})</h4>
            <span className="toggle-label">{showAllCitations ? '▲ Collapse' : '▼ Inspect Citations'}</span>
          </div>

          {showAllCitations && (
            <div className="citations-table-wrapper">
              <table className="citations-table">
                <thead>
                  <tr>
                    <th>Chunk ID</th>
                    <th>Document Source</th>
                    <th>Topic</th>
                    <th>Reference Excerpt</th>
                  </tr>
                </thead>
                <tbody>
                  {citations_summary.map((cit, cIdx) => (
                    <tr key={cIdx}>
                      <td><code>{cit.chunk_id}</code></td>
                      <td><strong>{cit.source_name}</strong></td>
                      <td>{cit.topic || 'General'}</td>
                      <td className="cit-excerpt-cell">&quot;{cit.excerpt}&quot;</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Question-by-Question Deep Dive */}
      <div className="report-questions-section">
        <h4 className="section-title">📝 Question-by-Question Detailed Review</h4>
        <div className="question-accordion-list">
          {question_summaries.map((q, qIdx) => {
            const isExpanded = expandedQuestionId === q.question_id
            const isEvaluated = q.status === 'evaluated'
            const qScore = q.weighted_score ?? 0
            const qScoreClass = qScore >= 70 ? 'score-high' : qScore >= 50 ? 'score-mid' : 'score-low'

            return (
              <div key={q.question_id} className={`question-acc-card ${isExpanded ? 'expanded' : ''}`}>
                <div
                  className="question-acc-header"
                  onClick={() => toggleExpand(q.question_id)}
                >
                  <div className="q-left-meta">
                    <span className="q-order-badge">#{qIdx + 1}</span>
                    <span className="q-comp-tag">{q.competency} ({q.difficulty})</span>
                    <span className="q-title-preview">{q.question_text.slice(0, 85)}...</span>
                  </div>

                  <div className="q-right-meta">
                    {isEvaluated ? (
                      <span className={`q-acc-score ${qScoreClass}`}>{qScore}%</span>
                    ) : (
                      <span className="q-unanswered-badge">Unanswered</span>
                    )}
                    <span className="chevron-icon">{isExpanded ? '▲' : '▼'}</span>
                  </div>
                </div>

                {isExpanded && (
                  <div className="question-acc-body">
                    <div className="full-question-prompt">
                      <strong>Question Prompt:</strong>
                      <p>{q.question_text}</p>
                    </div>

                    {q.candidate_answer && (
                      <div className="candidate-answer-box">
                        <strong>Candidate Response:</strong>
                        <p>{q.candidate_answer}</p>
                      </div>
                    )}

                    {isEvaluated && (
                      <>
                        {/* Dimension scores row */}
                        <div className="q-dimension-pills">
                          <span className="dim-pill">Correctness: <strong>{q.dimension_scores?.correctness}/5</strong></span>
                          <span className="dim-pill">Completeness: <strong>{q.dimension_scores?.completeness}/5</strong></span>
                          <span className="dim-pill">Relevance: <strong>{q.dimension_scores?.relevance}/5</strong></span>
                          <span className="dim-pill">Clarity: <strong>{q.dimension_scores?.clarity}/5</strong></span>
                        </div>

                        {/* Actionable Feedback */}
                        {q.actionable_feedback && (
                          <div className="q-feedback-box">
                            <strong>💡 Coaching Feedback:</strong>
                            <p>{q.actionable_feedback}</p>
                          </div>
                        )}

                        {/* Citations for this question */}
                        {q.citations?.length > 0 && (
                          <div className="q-citations-row">
                            <span>Grounding Citations:</span>
                            {q.citations.map((c, cIdx) => (
                              <code key={cIdx} title={c.excerpt}>{c.chunk_id} ({c.source_name})</code>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

