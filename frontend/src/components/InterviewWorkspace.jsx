import { useState, useEffect, useRef } from 'react'
import { InterviewReport } from './InterviewReport'
import './InterviewWorkspace.css'


const SAMPLE_PROFILE = {
  full_name: 'Alex River',
  title: 'Senior Python & Full-Stack Engineer',
  years_of_experience: 5.5,
  primary_competencies: [
    'Python FastAPI Concurrency',
    'React State Architecture',
    'Database Design & Caching',
    'System Architecture & Design'
  ],
  experiences: [
    {
      title: 'Senior Backend Engineer',
      company: 'CloudStream Systems',
      duration: '2021 - Present',
      description: 'Architected async event-driven microservices handling 12,000 req/sec with FastAPI and Redis.',
      technologies: ['FastAPI', 'Python', 'Redis', 'Docker', 'PostgreSQL']
    }
  ],
  education: [],
  projects: []
}

const SAMPLE_JOB = {
  job_title: 'Staff Platform Engineer',
  company: 'Nexus Technologies',
  experience_level: 'Senior',
  core_competencies: [
    'Python FastAPI Concurrency',
    'Database Design & Caching',
    'React State Architecture',
    'System Architecture & Design'
  ],
  responsibilities: [
    'Lead architecture for next-generation distributed APIs',
    'Ensure high throughput and sub-50ms p99 latency'
  ],
  qualification_keywords: ['FastAPI', 'React', 'Redis', 'PostgreSQL', 'Microservices']
}

export function InterviewWorkspace({
  apiBase = 'http://127.0.0.1:8000',
  onViewHistory = null,
  activeSessionId = null,
}) {
  const [session, setSession] = useState(null)
  const [questions, setQuestions] = useState([])
  const [currentQuestion, setCurrentQuestion] = useState(null)
  const [candidateAnswer, setCandidateAnswer] = useState('')
  const [totalQuestions, setTotalQuestions] = useState(3)
  const [loading, setLoading] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [showCriteria, setShowCriteria] = useState(false)
  const [showGrounding, setShowGrounding] = useState(true)
  const [activeHistoryIndex, setActiveHistoryIndex] = useState(null)
  const [evaluations, setEvaluations] = useState({}) // { [question_id]: EvaluationResult }
  const [finalReport, setFinalReport] = useState(null)
  const [loadingReport, setLoadingReport] = useState(false)

  // Web Speech API Voice State (Phase 6)
  const isVoiceSupported = typeof window !== 'undefined' && Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)
  const [isRecording, setIsRecording] = useState(false)
  const [transcriptInterim, setTranscriptInterim] = useState('')
  const [micStatus, setMicStatus] = useState(!isVoiceSupported ? 'unsupported' : 'idle')
  const [voiceNotice, setVoiceNotice] = useState('')
  const recognitionRef = useRef(null)

  useEffect(() => {
    if (!isVoiceSupported) return

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onstart = () => {
      setIsRecording(true)
      setMicStatus('listening')
      setVoiceNotice('')
    }

    recognition.onresult = (event) => {
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          const finalTranscript = event.results[i][0].transcript.trim()
          if (finalTranscript) {
            setCandidateAnswer((prev) => (prev ? `${prev.trim()} ${finalTranscript}` : finalTranscript))
          }
        } else {
          interim += event.results[i][0].transcript
        }
      }
      setTranscriptInterim(interim)
    }

    recognition.onerror = (event) => {
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setMicStatus('denied')
        setVoiceNotice('Microphone access was denied. You can continue typing your response in the text box.')
      } else if (event.error === 'no-speech') {
        // Natural pause in speech
      } else {
        setVoiceNotice(`Speech recognition status: ${event.error}`)
      }
      setIsRecording(false)
    }

    recognition.onend = () => {
      setIsRecording(false)
      setTranscriptInterim('')
      setMicStatus((prev) => (prev === 'listening' ? 'idle' : prev))
    }

    recognitionRef.current = recognition

    return () => {
      try {
        recognition.stop()
      } catch {
        // ignore
      }
    }
  }, [isVoiceSupported])

  const handleToggleVoice = () => {
    if (!isVoiceSupported) return
    setVoiceNotice('')
    if (isRecording) {
      try {
        recognitionRef.current?.stop()
      } catch {
        // ignore
      }
      setIsRecording(false)
      setMicStatus('idle')
    } else {
      try {
        recognitionRef.current?.start()
        setIsRecording(true)
        setMicStatus('listening')
      } catch (err) {
        setVoiceNotice(`Could not activate microphone: ${err.message || 'Check browser permissions.'}`)
        setMicStatus('error')
        setIsRecording(false)
      }
    }
  }

  const handleClearAnswer = () => {
    setCandidateAnswer('')
    setTranscriptInterim('')
  }

  // Load session if activeSessionId provided
  useEffect(() => {
    if (!activeSessionId) return
    let active = true
    Promise.resolve().then(() => {
      if (active) setLoading(true)
    })
    fetch(`${apiBase}/api/interviews/${activeSessionId}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((sess) => {
        if (active && sess) {
          setSession(sess)
        }
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [activeSessionId, apiBase])

  const handleLoadFinalReport = async (sessionId) => {
    const sId = sessionId || session?.session_id
    if (!sId) return
    setLoadingReport(true)
    setErrorMsg('')
    try {
      const response = await fetch(`${apiBase}/api/interviews/${sId}/report`)
      if (!response.ok) {
        throw new Error(`Failed to compile report (HTTP ${response.status})`)
      }
      const reportData = await response.json()
      setFinalReport(reportData)
    } catch (err) {
      setErrorMsg(err.message || 'Error generating report')
    } finally {
      setLoadingReport(false)
    }
  }

  // Start a new session
  const handleStartSession = async () => {
    setLoading(true)
    setErrorMsg('')
    setFinalReport(null)

    try {
      const response = await fetch(`${apiBase}/api/interviews`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_profile: SAMPLE_PROFILE,
          job_requirements: SAMPLE_JOB,
          total_questions: totalQuestions,
        }),
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || `Server returned HTTP ${response.status}`)
      }

      const data = await response.json()
      setSession(data.session)
      setCurrentQuestion(data.initial_question)
      setQuestions(data.initial_question ? [data.initial_question] : [])
      setCandidateAnswer('')
      setEvaluations({})
      setActiveHistoryIndex(null)
    } catch (err) {
      setErrorMsg(err.message || 'Failed to start interview session.')
    } finally {
      setLoading(false)
    }
  }

  // Advance to next question
  const handleNextQuestion = async () => {
    if (!session) return
    setLoading(true)
    setErrorMsg('')
    try {
      const response = await fetch(`${apiBase}/api/interviews/${session.session_id}/next-question`, {
        method: 'POST',
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || `Server returned HTTP ${response.status}`)
      }

      const data = await response.json()
      setSession(data.session)

      if (data.is_completed || !data.question) {
        setCurrentQuestion(null)
      } else {
        setCurrentQuestion(data.question)
        setQuestions((prev) => [...prev, data.question])
        setCandidateAnswer('')
      }
      setActiveHistoryIndex(null)
    } catch (err) {
      setErrorMsg(err.message || 'Failed to advance to next question.')
    } finally {
      setLoading(false)
    }
  }

  // Submit candidate answer for rubric evaluation
  const handleSubmitAnswer = async (questionId) => {
    if (!session || !questionId) return
    if (!candidateAnswer.trim()) {
      setErrorMsg('Please enter an answer before submitting for evaluation.')
      return
    }

    setEvaluating(true)
    setErrorMsg('')
    try {
      const response = await fetch(`${apiBase}/api/interviews/${session.session_id}/questions/${questionId}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer_text: candidateAnswer }),
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || `Server returned HTTP ${response.status}`)
      }

      const data = await response.json()
      setEvaluations((prev) => ({
        ...prev,
        [questionId]: data.evaluation,
      }))
    } catch (err) {
      setErrorMsg(err.message || 'Failed to evaluate answer.')
    } finally {
      setEvaluating(false)
    }
  }

  // Load questions and evaluations list if session exists
  useEffect(() => {
    if (!session?.session_id) return
    let active = true

    // Fetch questions
    fetch(`${apiBase}/api/interviews/${session.session_id}/questions`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => {
        if (active && Array.isArray(data)) {
          setQuestions(data)
        }
      })
      .catch(() => {})

    // Fetch existing evaluations
    fetch(`${apiBase}/api/interviews/${session.session_id}/evaluations`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => {
        if (active && Array.isArray(data)) {
          const evalMap = {}
          data.forEach((ev) => {
            evalMap[ev.question_id] = ev
          })
          setEvaluations(evalMap)
        }
      })
      .catch(() => {})

    return () => {
      active = false
    }
  }, [apiBase, session?.session_id])

  const displayedQuestion = activeHistoryIndex !== null ? questions[activeHistoryIndex] : currentQuestion
  const isViewingHistory = activeHistoryIndex !== null && activeHistoryIndex !== (session?.current_question_index ?? 0)
  const currentEval = displayedQuestion ? evaluations[displayedQuestion.question_id] : null

  // Helpers for sample answers
  const handleLoadSampleStrongAnswer = () => {
    if (!displayedQuestion) return
    const comp = displayedQuestion.competency.toLowerCase()
    if (comp.includes('fastapi') || comp.includes('python')) {
      setCandidateAnswer(
        'In FastAPI, declaring an endpoint as `async def` runs the coroutine directly on the main asyncio event loop. ' +
        'If a route performs synchronous blocking operations—such as CPU-heavy JSON parsing or legacy blocking DB calls—' +
        'it monopolizes the event loop thread, preventing other concurrent connections from processing. ' +
        'To mitigate this, blocking calls should be offloaded using `fastapi.concurrency.run_in_threadpool` or regular `def` syntax. ' +
        'Furthermore, dependency injection with `Depends` and `yield` fixtures ensures per-request resource cleanup, such as returning database connections to SQLAlchemy pools.'
      )
    } else if (comp.includes('react')) {
      setCandidateAnswer(
        'In React 18, state management must account for concurrent rendering. The Fiber reconciler schedules state updates ' +
        'by assigning lanes. Urgent updates (typing, clicking) interrupt non-urgent transitions wrapped in `startTransition` or `useDeferredValue`. ' +
        'To prevent tearing, React uses immutable tree double-buffering. For multi-view data, we colocate state and use context splitting or specialized selectors ' +
        'so consumers only re-render when their specific slice changes, avoiding broad subscription invalidation cascades.'
      )
    } else {
      setCandidateAnswer(
        'When architecting a high-throughput caching tier with Redis in front of PostgreSQL, we employ the cache-aside pattern. ' +
        'To mitigate cache stampedes (dog-piling) when hot keys expire under sudden traffic spikes, we apply distributed locks (Redlock) or probabilistic early expiration (XFetch). ' +
        'For cache penetration, we utilize Bloom filters at the API gateway layer or cache sentinel null values with short TTLs. ' +
        'Finally, adding random jitter to TTL durations prevents synchronized cache avalanches.'
      )
    }
  }

  const handleLoadSampleWeakAnswer = () => {
    setCandidateAnswer('FastAPI is very fast because of async and Python. It works good.')
  }

  // Calculate overall session evaluation average
  const evalList = Object.values(evaluations)
  const averageScore = evalList.length > 0
    ? Math.round(evalList.reduce((acc, curr) => acc + curr.weighted_score, 0) / evalList.length)
    : null

  if (finalReport) {
    return (
      <InterviewReport
        report={finalReport}
        onRestart={() => {
          setFinalReport(null)
          setSession(null)
          setCurrentQuestion(null)
          setQuestions([])
          setEvaluations({})
          setActiveHistoryIndex(null)
        }}
        onViewHistory={onViewHistory}
      />
    )
  }

  return (
    <div className="interview-workspace">
      {/* Header Bar */}
      <div className="workspace-header-card">
        <div className="header-info">
          <h2>🎙️ Adaptive Interview & Answer Evaluation</h2>
          <p>
            Dynamically generates grounded questions and evaluates responses using a deterministic 4-dimension rubric (Correctness, Completeness, Relevance, Clarity).
          </p>
        </div>

        <div className="header-actions">
          {onViewHistory && (
            <button
              className="btn-secondary btn-sm"
              onClick={onViewHistory}
              title="View past interview practice sessions"
            >
              📜 Past Sessions
            </button>
          )}

          {!session ? (
            <div className="start-controls">
              <label className="question-count-label">
                Questions:
                <select
                  value={totalQuestions}
                  onChange={(e) => setTotalQuestions(Number(e.target.value))}
                  disabled={loading}
                >
                  <option value={2}>2 Questions</option>
                  <option value={3}>3 Questions</option>
                  <option value={4}>4 Questions</option>
                </select>
              </label>
              <button
                className="btn-primary"
                onClick={handleStartSession}
                disabled={loading}
              >
                {loading ? 'Initializing...' : '🚀 Start Interview Session'}
              </button>
            </div>
          ) : (
            <div className="active-session-meta">
              <div className="session-id-pill">
                Session: <code>{session.session_id}</code>
              </div>
              {averageScore !== null && (
                <div className="avg-score-pill">
                  Avg Score: <strong>{averageScore}%</strong>
                </div>
              )}
              <div className={`status-badge status-${session.status}`}>
                {session.status}
              </div>
              <button
                className="btn-secondary btn-sm"
                onClick={() => {
                  setSession(null)
                  setCurrentQuestion(null)
                  setQuestions([])
                  setEvaluations({})
                  setActiveHistoryIndex(null)
                }}
              >
                Reset Session
              </button>
            </div>
          )}
        </div>
      </div>

      {errorMsg && (
        <div className="error-banner">
          <span>⚠️ {errorMsg}</span>
          <button onClick={() => setErrorMsg('')}>✕</button>
        </div>
      )}

      {/* Preflight Setup View */}
      {!session && (
        <div className="preflight-card">
          <h3>Ready to start adaptive interview & rubric evaluation</h3>
          <p>
            The orchestrator will formulate a competency plan for <strong>Alex River</strong> and <strong>Staff Platform Engineer at Nexus Technologies</strong>,
            query relevant reference chunks in ChromaDB, generate structured questions, and evaluate submitted answers against the agreed 4-dimension rubric.
          </p>

          <div className="preflight-grid">
            <div className="preflight-box">
              <div className="box-title">👤 Candidate Profile Preview</div>
              <ul>
                <li><strong>Role:</strong> {SAMPLE_PROFILE.title}</li>
                <li><strong>Experience:</strong> {SAMPLE_PROFILE.years_of_experience} Years</li>
                <li><strong>Key Skills:</strong> {SAMPLE_PROFILE.primary_competencies.join(', ')}</li>
              </ul>
            </div>
            <div className="preflight-box">
              <div className="box-title">🎯 Target Job Requirements</div>
              <ul>
                <li><strong>Role:</strong> {SAMPLE_JOB.job_title} ({SAMPLE_JOB.experience_level})</li>
                <li><strong>Company:</strong> {SAMPLE_JOB.company}</li>
                <li><strong>Core Competencies:</strong> {SAMPLE_JOB.core_competencies.join(', ')}</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Active Session Layout */}
      {session && (
        <div className="session-layout">
          {/* Competency Roadmap Sidebar */}
          <aside className="competency-sidebar">
            <div className="sidebar-header">
              <h4>Competency Plan ({session.competency_plan?.length || 0})</h4>
              <span className="progress-badge">
                {session.status === 'completed'
                  ? 'Completed'
                  : `Q ${(session.current_question_index ?? 0) + 1} of ${session.total_questions}`}
              </span>
            </div>

            <div className="roadmap-list">
              {session.competency_plan?.map((item, idx) => {
                const qForIdx = questions[idx]
                const qEval = qForIdx ? evaluations[qForIdx.question_id] : null
                const isCurrent = idx === session.current_question_index && session.status !== 'completed'
                const isDone = qEval !== undefined || (idx < (session.current_question_index ?? 0))
                const isSelectedHistory = activeHistoryIndex === idx

                return (
                  <div
                    key={idx}
                    className={`roadmap-item ${isCurrent ? 'current' : ''} ${isDone ? 'done' : ''} ${
                      isSelectedHistory ? 'selected-history' : ''
                    }`}
                    onClick={() => {
                      if (idx < questions.length) {
                        setActiveHistoryIndex(idx)
                      }
                    }}
                  >
                    <div className="roadmap-step-num">
                      {qEval ? '★' : isDone ? '✓' : idx + 1}
                    </div>
                    <div className="roadmap-item-info">
                      <div className="roadmap-competency">{item.competency}</div>
                      <div className="roadmap-meta">
                        <span className={`diff-pill diff-${item.difficulty.toLowerCase()}`}>
                          {item.difficulty}
                        </span>
                        {qEval && (
                          <span className={`eval-score-pill ${qEval.weighted_score >= 70 ? 'score-high' : qEval.weighted_score >= 50 ? 'score-mid' : 'score-low'}`}>
                            {qEval.weighted_score}%
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="sidebar-footer">
              <small>Evaluations: <strong>{Object.keys(evaluations).length} of {session.total_questions}</strong></small>
            </div>
          </aside>

          {/* Main Question & Answer Panel */}
          <section className="interview-main-panel">
            {isViewingHistory && (
              <div className="history-notice">
                <span>Viewing question #{activeHistoryIndex + 1}</span>
                <button
                  className="btn-text"
                  onClick={() => setActiveHistoryIndex(null)}
                >
                  Return to Active Question →
                </button>
              </div>
            )}

            {displayedQuestion ? (
              <div className="question-card">
                {/* Question Header */}
                <div className="question-header">
                  <div className="question-index-tag">
                    Question #{displayedQuestion.order_index + 1} of {session.total_questions}
                  </div>
                  <div className="question-badges">
                    <span className="badge-competency">{displayedQuestion.competency}</span>
                    <span className={`diff-pill diff-${displayedQuestion.difficulty.toLowerCase()}`}>
                      {displayedQuestion.difficulty}
                    </span>
                  </div>
                </div>

                {/* Question Text */}
                <div className="question-body">
                  <p className="question-text">{displayedQuestion.question_text}</p>
                </div>

                {/* Grounding & Evidence Section */}
                <div className="grounding-section">
                  <div
                    className="grounding-header"
                    onClick={() => setShowGrounding(!showGrounding)}
                  >
                    <span>🛡️ Verified Retrieved Sources ({displayedQuestion.retrieved_chunk_ids?.length || 0})</span>
                    <span className="toggle-indicator">{showGrounding ? '▲ Hide' : '▼ Inspect Evidence'}</span>
                  </div>

                  {showGrounding && (
                    <div className="grounding-content">
                      <p className="grounding-disclaimer">
                        Evidence chunks retrieved from ChromaDB vector store. The model cannot fabricate chunk IDs.
                      </p>
                      <div className="chunk-list">
                        {displayedQuestion.retrieved_context?.length > 0 ? (
                          displayedQuestion.retrieved_context.map((chunk, cIdx) => (
                            <div key={cIdx} className="chunk-item">
                              <div className="chunk-meta">
                                <span className="chunk-id-tag">{chunk.chunk_id}</span>
                                <span className="chunk-source-name">{chunk.source_name}</span>
                                <span className="chunk-topic">{chunk.topic}</span>
                              </div>
                              <div className="chunk-excerpt">
                                &quot;{chunk.excerpt}&quot;
                              </div>
                            </div>
                          ))
                        ) : (
                          <div className="no-chunks-notice">
                            No specific reference chunks matched; question generated from foundational technical standards.
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Collapsible Expected Criteria Section */}
                <div className="criteria-section">
                  <div
                    className="criteria-header"
                    onClick={() => setShowCriteria(!showCriteria)}
                  >
                    <span>📋 Expected Technical Concepts ({displayedQuestion.expected_criteria?.length || 0})</span>
                    <span className="toggle-indicator">{showCriteria ? '▲ Hide' : '▼ Show Rubric Criteria'}</span>
                  </div>

                  {showCriteria && (
                    <div className="criteria-content">
                      <ul className="criteria-list">
                        {displayedQuestion.expected_criteria?.map((crit, crIdx) => (
                          <li key={crIdx}>{crit}</li>
                        ))}
                      </ul>
                      {displayedQuestion.follow_up_rationale && (
                        <div className="rationale-box">
                          <strong>Orchestrator Rationale:</strong> {displayedQuestion.follow_up_rationale}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Answer Submission Section */}
                {!currentEval && (
                  <div className="answer-section">
                    <div className="voice-toolbar">
                      <div className="voice-controls-group">
                        {isVoiceSupported ? (
                          <button
                            type="button"
                            id="btn-voice-toggle"
                            className={`btn-voice ${isRecording ? 'recording' : ''}`}
                            onClick={handleToggleVoice}
                            disabled={evaluating}
                            title={isRecording ? 'Click to stop recording' : 'Click to speak response'}
                          >
                            {isRecording ? (
                              <>
                                <span className="voice-record-pulse" />
                                <span>⏹ Stop Recording</span>
                              </>
                            ) : (
                              <>
                                <span>🎙️ Record Answer with Voice</span>
                              </>
                            )}
                          </button>
                        ) : (
                          <div className="voice-notice unsupported">
                            ℹ️ Web Speech API not supported in this browser. Keyboard text input is ready.
                          </div>
                        )}

                        {isRecording && (
                          <div className="voice-listening-indicator">
                            <span className="voice-pulse-dot" />
                            <span>Listening... Speak response clearly</span>
                          </div>
                        )}

                        {micStatus === 'denied' && (
                          <div className="voice-notice denied">
                            ⚠️ Mic permission denied (type below)
                          </div>
                        )}

                        {candidateAnswer && (
                          <button
                            type="button"
                            className="btn-sample btn-sample-weak"
                            onClick={handleClearAnswer}
                            disabled={evaluating || isRecording}
                          >
                            Clear Text
                          </button>
                        )}
                      </div>

                      <div className="sample-answer-buttons">
                        <button
                          type="button"
                          className="btn-sample"
                          onClick={handleLoadSampleStrongAnswer}
                          disabled={evaluating || isRecording}
                        >
                          ⚡ Load Strong Sample Answer
                        </button>
                        <button
                          type="button"
                          className="btn-sample btn-sample-weak"
                          onClick={handleLoadSampleWeakAnswer}
                          disabled={evaluating || isRecording}
                        >
                          Load Brief Answer
                        </button>
                        <span className="word-count">
                          {candidateAnswer.trim() ? candidateAnswer.trim().split(/\s+/).length : 0} words
                        </span>
                      </div>
                    </div>

                    {voiceNotice && (
                      <div className="voice-alert-banner">
                        {voiceNotice}
                      </div>
                    )}

                    {transcriptInterim && (
                      <div className="voice-interim-box">
                        <span className="interim-label">Live Spoken Transcript:</span>
                        <p className="interim-text">&quot;{transcriptInterim}...&quot;</p>
                      </div>
                    )}

                    <div className="answer-header">
                      <label htmlFor="candidate-answer">
                        Candidate Answer (Voice transcribed & editable):
                      </label>
                      <span className="review-hint">
                        💡 You can review and edit your transcribed answer below before submitting.
                      </span>
                    </div>

                    <textarea
                      id="candidate-answer"
                      className="answer-textarea"
                      rows={5}
                      placeholder="Speak using the microphone above or type candidate response here..."
                      value={candidateAnswer}
                      onChange={(e) => setCandidateAnswer(e.target.value)}
                      disabled={evaluating}
                    />

                    <div className="action-row">
                      <div className="state-info">
                        Status: <code>{session.status}</code>
                      </div>
                      <button
                        className="btn-primary"
                        onClick={() => {
                          if (isRecording) {
                            try { recognitionRef.current?.stop() } catch {}
                            setIsRecording(false)
                          }
                          handleSubmitAnswer(displayedQuestion.question_id)
                        }}
                        disabled={evaluating || !candidateAnswer.trim()}
                      >
                        {evaluating ? 'Evaluating Answer...' : '🔍 Evaluate Answer'}
                      </button>
                    </div>
                  </div>
                )}

                {/* Evaluation Results Panel (Phase 4) */}
                {currentEval && (
                  <div className="evaluation-card">
                    <div className="eval-header">
                      <div className="eval-score-box">
                        <div className="score-label">Weighted Score</div>
                        <div className={`score-value ${currentEval.weighted_score >= 70 ? 'score-high' : currentEval.weighted_score >= 50 ? 'score-mid' : 'score-low'}`}>
                          {currentEval.weighted_score} <span className="score-max">/ 100</span>
                        </div>
                      </div>

                      <div className="eval-status-info">
                        <span className={`eval-status-badge status-${currentEval.evaluation_status}`}>
                          {currentEval.evaluation_status}
                        </span>
                        <div className="eval-formula-text">
                          Formula: (Correctness*30 + Completeness*30 + Relevance*20 + Clarity*20) / 5
                        </div>
                      </div>
                    </div>

                    {/* Insufficient Evidence Notice */}
                    {currentEval.evaluation_status === 'insufficient_evidence' && (
                      <div className="insufficient-alert">
                        <strong>⚠️ Notice:</strong> The reference knowledge base did not contain verified documentation
                        for this prompt. As required by system safety rules, this evaluation is flagged as insufficient evidence.
                      </div>
                    )}

                    {/* Dimension Breakdown Bars */}
                    <div className="dimension-grid">
                      <div className="dim-card">
                        <div className="dim-top">
                          <span className="dim-name">Correctness (30%)</span>
                          <span className="dim-score">{currentEval.dimension_scores.correctness} / 5</span>
                        </div>
                        <div className="dim-bar-track">
                          <div
                            className="dim-bar-fill"
                            style={{ width: `${(currentEval.dimension_scores.correctness / 5) * 100}%` }}
                          />
                        </div>
                      </div>

                      <div className="dim-card">
                        <div className="dim-top">
                          <span className="dim-name">Completeness (30%)</span>
                          <span className="dim-score">{currentEval.dimension_scores.completeness} / 5</span>
                        </div>
                        <div className="dim-bar-track">
                          <div
                            className="dim-bar-fill"
                            style={{ width: `${(currentEval.dimension_scores.completeness / 5) * 100}%` }}
                          />
                        </div>
                      </div>

                      <div className="dim-card">
                        <div className="dim-top">
                          <span className="dim-name">Relevance (20%)</span>
                          <span className="dim-score">{currentEval.dimension_scores.relevance} / 5</span>
                        </div>
                        <div className="dim-bar-track">
                          <div
                            className="dim-bar-fill"
                            style={{ width: `${(currentEval.dimension_scores.relevance / 5) * 100}%` }}
                          />
                        </div>
                      </div>

                      <div className="dim-card">
                        <div className="dim-top">
                          <span className="dim-name">Clarity (20%)</span>
                          <span className="dim-score">{currentEval.dimension_scores.clarity} / 5</span>
                        </div>
                        <div className="dim-bar-track">
                          <div
                            className="dim-bar-fill"
                            style={{ width: `${(currentEval.dimension_scores.clarity / 5) * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Strengths & Missing Concepts */}
                    <div className="eval-feedback-grid">
                      <div className="feedback-col strengths-col">
                        <h5>✓ Demonstrated Strengths</h5>
                        <ul>
                          {currentEval.strengths.length > 0 ? (
                            currentEval.strengths.map((str, sIdx) => <li key={sIdx}>{str}</li>)
                          ) : (
                            <li className="no-items">None identified in submitted response.</li>
                          )}
                        </ul>
                      </div>

                      <div className="feedback-col missing-col">
                        <h5>✕ Missing Concepts / Gaps</h5>
                        <ul>
                          {currentEval.missing_concepts.length > 0 ? (
                            currentEval.missing_concepts.map((mis, mIdx) => <li key={mIdx}>{mis}</li>)
                          ) : (
                            <li className="no-items">No major omissions detected.</li>
                          )}
                        </ul>
                      </div>
                    </div>

                    {/* Actionable Feedback */}
                    <div className="actionable-box">
                      <strong>💡 Actionable Coaching Feedback:</strong>
                      <p>{currentEval.actionable_feedback}</p>
                    </div>

                    {/* Citations Grounding */}
                    {currentEval.citations?.length > 0 && (
                      <div className="eval-citations-box">
                        <strong>📚 Grounded Evidence Citations ({currentEval.citations.length}):</strong>
                        <div className="citation-pills">
                          {currentEval.citations.map((cit, cIdx) => (
                            <div key={cIdx} className="citation-badge">
                              <code>{cit.chunk_id}</code>
                              <span>{cit.source_name}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Advance to Next Question */}
                    {!isViewingHistory && session.status !== 'completed' && (
                      <div className="eval-advance-row">
                        <button
                          className="btn-primary"
                          onClick={handleNextQuestion}
                          disabled={loading}
                        >
                          {session.current_question_index + 1 >= session.total_questions
                            ? '🏁 Finish Interview & View Summary'
                            : 'Next Question →'}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : session.status === 'completed' ? (
              <div className="completed-card">
                <div className="completed-icon">🎉</div>
                <h3>Interview Complete & Evaluated!</h3>
                <p>
                  All {session.total_questions} questions were generated, answered, and scored according to the rubric.
                </p>

                {averageScore !== null && (
                  <div className="final-score-banner">
                    <span className="banner-title">Final Overall Average Score</span>
                    <span className={`banner-score ${averageScore >= 70 ? 'score-high' : averageScore >= 50 ? 'score-mid' : 'score-low'}`}>
                      {averageScore} / 100
                    </span>
                  </div>
                )}

                <div className="completed-summary">
                  <h4>Session Evaluation Breakdown:</h4>
                  <div className="completed-questions-list">
                    {questions.map((q, qIdx) => {
                      const ev = evaluations[q.question_id]
                      return (
                        <div
                          key={qIdx}
                          className="completed-q-item"
                          onClick={() => setActiveHistoryIndex(qIdx)}
                        >
                          <span className="q-badge">#{qIdx + 1}</span>
                          <div className="q-info">
                            <span className="q-comp">{q.competency} ({q.difficulty})</span>
                            <span className="q-snip">{q.question_text.slice(0, 90)}...</span>
                          </div>
                          {ev ? (
                            <span className={`eval-score-pill ${ev.weighted_score >= 70 ? 'score-high' : ev.weighted_score >= 50 ? 'score-mid' : 'score-low'}`}>
                              {ev.weighted_score}%
                            </span>
                          ) : (
                            <span className="view-pill">Inspect →</span>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                  <button
                    className="btn-primary"
                    onClick={() => handleLoadFinalReport(session.session_id)}
                    disabled={loadingReport}
                  >
                    {loadingReport ? 'Compiling Report...' : '📊 View Comprehensive Final Report'}
                  </button>
                  <button
                    className="btn-secondary"
                    onClick={handleStartSession}
                  >
                    Start Another Session
                  </button>
                </div>
              </div>
            ) : (
              <div className="loading-card">
                <div className="spinner"></div>
                <p>Generating personalized technical question...</p>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
