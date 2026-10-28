import { useState } from 'react'
import './DocumentSetup.css'

const SAMPLE_RESUME_TEXT = `Sarah Chen
sarah.chen@example.com | (415) 890-1234 | San Francisco, CA

Professional Summary:
Senior Full-Stack Software Engineer with 6+ years specializing in Python, FastAPI, React, and scalable cloud architectures. Proven track record building high-throughput distributed systems and intuitive user interfaces.

Experience:
Senior Software Engineer — CloudVertex AI (2022 – Present)
- Engineered async microservices handling 25M daily transactions using FastAPI, Redis, and PostgreSQL.
- Architected candidate assessment platform with React, TypeScript, and Docker containerization.
- Led automated testing adoption, achieving 94% test coverage across core backend modules.

Software Engineer — Horizon Labs (2019 – 2022)
- Built customer-facing dashboard using React, modern CSS, and Python REST APIs.
- Optimized SQL database queries and implemented caching layers reducing p99 latency by 45%.

Education:
B.S. in Computer Science — University of California, Berkeley (2019)

Technical Skills:
Python, FastAPI, React, TypeScript, JavaScript, SQL, PostgreSQL, Redis, Docker, Kubernetes, AWS, Git, REST APIs, System Design, CI/CD`

const SAMPLE_JOB_TEXT = `Senior Full-Stack Engineer — Platform Architecture
Nexus Dynamics | Hybrid (San Francisco, CA)

About the Role:
We are seeking a Senior Full-Stack Engineer to architect and scale our next-generation AI automation platform. You will design robust backend services, create responsive user experiences, and collaborate on core distributed architecture.

Key Requirements:
- 5+ years of software development experience with Python, FastAPI, and PostgreSQL.
- Strong proficiency in modern frontend development using React and TypeScript.
- Solid understanding of distributed system architecture, REST APIs, and microservices.
- Experience with containerization (Docker, Kubernetes) and CI/CD pipelines.
- Commitment to high code quality, automated testing, and comprehensive code reviews.

Responsibilities:
- Lead the architecture and implementation of critical backend APIs and interactive frontend applications.
- Design reliable relational database schemas and optimize system throughput.
- Mentor engineers and participate in architecture design reviews.`

export function DocumentSetup({ onParsed, apiBase = 'http://127.0.0.1:8000' }) {
  // Input modes: 'file' | 'text'
  const [resumeMode, setResumeMode] = useState('text')
  const [resumeText, setResumeText] = useState(SAMPLE_RESUME_TEXT)
  const [resumeFile, setResumeFile] = useState(null)

  const [jobMode, setJobMode] = useState('text')
  const [jobText, setJobText] = useState(SAMPLE_JOB_TEXT)
  const [jobFile, setJobFile] = useState(null)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [parseResult, setParseResult] = useState(null)
  const [activeTab, setActiveTab] = useState('profile') // 'profile' | 'job' | 'json'

  const handleResumeFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setResumeFile(e.target.files[0])
      setError('')
    }
  }

  const handleJobFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setJobFile(e.target.files[0])
      setError('')
    }
  }

  const handleLoadSamples = () => {
    setResumeMode('text')
    setResumeText(SAMPLE_RESUME_TEXT)
    setResumeFile(null)
    setJobMode('text')
    setJobText(SAMPLE_JOB_TEXT)
    setJobFile(null)
    setError('')
  }

  const handleClear = () => {
    setResumeText('')
    setResumeFile(null)
    setJobText('')
    setJobFile(null)
    setError('')
    setParseResult(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const formData = new FormData()

      if (resumeMode === 'file' && resumeFile) {
        formData.append('resume_file', resumeFile)
      } else if (resumeText.trim()) {
        formData.append('resume_text', resumeText.trim())
      } else {
        throw new Error('Please upload a resume file or paste resume text.')
      }

      if (jobMode === 'file' && jobFile) {
        formData.append('job_description_file', jobFile)
      } else if (jobText.trim()) {
        formData.append('job_description_text', jobText.trim())
      } else {
        throw new Error('Please upload a job description file or paste job description text.')
      }

      const response = await fetch(`${apiBase}/api/documents/parse`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => null)
        throw new Error(errorData?.detail || `HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      setParseResult(data)
      if (onParsed) onParsed(data)
    } catch (err) {
      setError(err.message || 'Failed to extract profile')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="setup-container">
      {/* Configuration Header */}
      <div className="setup-header">
        <div>
          <h2 className="setup-title">Document Ingestion & Profile Extraction</h2>
          <p className="setup-subtitle">
            Upload or paste candidate resume and job specifications. Documents are validated, parsed,
            and structured into standardized schemas without leaking credentials.
          </p>
        </div>
        <div className="setup-actions">
          <button
            type="button"
            id="btn-load-sample"
            className="btn-secondary"
            onClick={handleLoadSamples}
            disabled={loading}
          >
            📋 Load Sample Data
          </button>
          <button
            type="button"
            id="btn-clear-setup"
            className="btn-secondary"
            onClick={handleClear}
            disabled={loading}
          >
            🗑️ Clear
          </button>
        </div>
      </div>

      {error && (
        <div id="setup-error-banner" className="error-banner">
          ⚠️ <strong>Extraction Error:</strong> {error}
        </div>
      )}

      {/* Input Panels Grid */}
      <form onSubmit={handleSubmit} className="inputs-grid">
        {/* Resume Input Panel */}
        <div className="input-panel">
          <div className="panel-tab-header">
            <span className="panel-label">1. Candidate Resume</span>
            <div className="segmented-control">
              <button
                type="button"
                className={`segment-btn ${resumeMode === 'text' ? 'active' : ''}`}
                onClick={() => setResumeMode('text')}
              >
                Paste Text
              </button>
              <button
                type="button"
                className={`segment-btn ${resumeMode === 'file' ? 'active' : ''}`}
                onClick={() => setResumeMode('file')}
              >
                Upload File (.pdf, .docx)
              </button>
            </div>
          </div>

          {resumeMode === 'text' ? (
            <textarea
              id="resume-text-input"
              className="text-input-area"
              rows={12}
              placeholder="Paste candidate resume text here..."
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              disabled={loading}
            />
          ) : (
            <div className="file-dropzone">
              <input
                id="resume-file-input"
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleResumeFileChange}
                disabled={loading}
                className="file-input-hidden"
              />
              <label htmlFor="resume-file-input" className="file-dropzone-label">
                <span className="file-icon">📄</span>
                <span className="file-primary-text">
                  {resumeFile ? resumeFile.name : 'Click to select or drag Resume file'}
                </span>
                <span className="file-hint">Supported: .pdf, .docx, .txt (Max 10MB)</span>
              </label>
              {resumeFile && (
                <div className="file-badge">
                  Selected: <strong>{resumeFile.name}</strong> ({(resumeFile.size / 1024).toFixed(1)} KB)
                  <button type="button" onClick={() => setResumeFile(null)} className="btn-file-remove">✕</button>
                </div>
              )}
            </div>
          )}
          <div className="char-counter">
            {resumeMode === 'text' ? `${resumeText.length} characters` : resumeFile ? `${(resumeFile.size / 1024).toFixed(1)} KB` : 'No file chosen'}
          </div>
        </div>

        {/* Job Description Input Panel */}
        <div className="input-panel">
          <div className="panel-tab-header">
            <span className="panel-label">2. Target Job Description</span>
            <div className="segmented-control">
              <button
                type="button"
                className={`segment-btn ${jobMode === 'text' ? 'active' : ''}`}
                onClick={() => setJobMode('text')}
              >
                Paste Text
              </button>
              <button
                type="button"
                className={`segment-btn ${jobMode === 'file' ? 'active' : ''}`}
                onClick={() => setJobMode('file')}
              >
                Upload File (.pdf, .docx)
              </button>
            </div>
          </div>

          {jobMode === 'text' ? (
            <textarea
              id="job-text-input"
              className="text-input-area"
              rows={12}
              placeholder="Paste job description requirements and responsibilities here..."
              value={jobText}
              onChange={(e) => setJobText(e.target.value)}
              disabled={loading}
            />
          ) : (
            <div className="file-dropzone">
              <input
                id="job-file-input"
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleJobFileChange}
                disabled={loading}
                className="file-input-hidden"
              />
              <label htmlFor="job-file-input" className="file-dropzone-label">
                <span className="file-icon">💼</span>
                <span className="file-primary-text">
                  {jobFile ? jobFile.name : 'Click to select or drag Job Description file'}
                </span>
                <span className="file-hint">Supported: .pdf, .docx, .txt (Max 10MB)</span>
              </label>
              {jobFile && (
                <div className="file-badge">
                  Selected: <strong>{jobFile.name}</strong> ({(jobFile.size / 1024).toFixed(1)} KB)
                  <button type="button" onClick={() => setJobFile(null)} className="btn-file-remove">✕</button>
                </div>
              )}
            </div>
          )}
          <div className="char-counter">
            {jobMode === 'text' ? `${jobText.length} characters` : jobFile ? `${(jobFile.size / 1024).toFixed(1)} KB` : 'No file chosen'}
          </div>
        </div>

        {/* Submit Execution Button */}
        <div className="submit-bar">
          <button
            type="submit"
            id="btn-parse-documents"
            className="btn-primary"
            disabled={loading}
          >
            {loading ? 'Processing & Extracting Profile...' : '✨ Extract Candidate Profile & Job Requirements'}
          </button>
        </div>
      </form>

      {/* Extracted Structured Results */}
      {parseResult && (
        <section id="parsed-results-section" className="results-container">
          {/* Result Metadata Banner */}
          <div className="results-header">
            <div className="results-badge-group">
              <span className={`method-badge ${parseResult.extraction_method}`}>
                Engine: {parseResult.extraction_method === 'groq' ? 'Groq LLM (llama-3.3-70b)' : 'Deterministic Local Heuristics'}
              </span>
              <span className="stat-pill">
                Resume: {parseResult.stats.resume_char_count} chars
              </span>
              <span className="stat-pill">
                Job Spec: {parseResult.stats.job_description_char_count} chars
              </span>
            </div>

            <div className="results-tabs">
              <button
                type="button"
                className={`result-tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
                onClick={() => setActiveTab('profile')}
              >
                Candidate Profile
              </button>
              <button
                type="button"
                className={`result-tab-btn ${activeTab === 'job' ? 'active' : ''}`}
                onClick={() => setActiveTab('job')}
              >
                Job Requirements
              </button>
              <button
                type="button"
                className={`result-tab-btn ${activeTab === 'json' ? 'active' : ''}`}
                onClick={() => setActiveTab('json')}
              >
                Raw JSON Schema
              </button>
            </div>
          </div>

          {parseResult.warnings && parseResult.warnings.length > 0 && (
            <div className="warnings-box">
              {parseResult.warnings.map((w, idx) => (
                <div key={idx} className="warning-item">ℹ️ {w}</div>
              ))}
            </div>
          )}

          {/* TAB 1: Candidate Profile */}
          {activeTab === 'profile' && (
            <div className="tab-content profile-tab">
              <div className="profile-hero">
                <div className="profile-identity">
                  <div className="avatar-placeholder">
                    {parseResult.candidate_profile.full_name?.charAt(0) || 'C'}
                  </div>
                  <div>
                    <h3 className="candidate-name">{parseResult.candidate_profile.full_name || 'Candidate'}</h3>
                    <div className="contact-details">
                      {parseResult.candidate_profile.email && <span>📧 {parseResult.candidate_profile.email}</span>}
                      {parseResult.candidate_profile.phone && <span>📱 {parseResult.candidate_profile.phone}</span>}
                    </div>
                  </div>
                </div>
                {parseResult.candidate_profile.summary && (
                  <p className="candidate-summary">{parseResult.candidate_profile.summary}</p>
                )}
              </div>

              {/* Primary Competencies */}
              <div className="section-block">
                <h4 className="section-heading">Primary Competencies (Interview Targets)</h4>
                <div className="tags-cloud">
                  {parseResult.candidate_profile.primary_competencies?.map((comp, idx) => (
                    <span key={idx} className="comp-tag">🎯 {comp}</span>
                  ))}
                </div>
              </div>

              {/* Skills */}
              <div className="section-block">
                <h4 className="section-heading">Extracted Technical Skills</h4>
                <div className="tags-cloud">
                  {parseResult.candidate_profile.skills?.map((skill, idx) => (
                    <span key={idx} className="skill-tag">{skill}</span>
                  ))}
                </div>
              </div>

              {/* Experience */}
              {parseResult.candidate_profile.experiences?.length > 0 && (
                <div className="section-block">
                  <h4 className="section-heading">Work Experience</h4>
                  <div className="experience-list">
                    {parseResult.candidate_profile.experiences.map((exp, idx) => (
                      <div key={idx} className="experience-card">
                        <div className="exp-header">
                          <span className="exp-title">{exp.title}</span>
                          <span className="exp-duration">{exp.duration}</span>
                        </div>
                        {exp.company && <div className="exp-company">{exp.company}</div>}
                        {exp.description && <p className="exp-desc">{exp.description}</p>}
                        {exp.technologies?.length > 0 && (
                          <div className="exp-techs">
                            {exp.technologies.map((t, i) => (
                              <span key={i} className="mini-tag">{t}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: Job Requirements */}
          {activeTab === 'job' && (
            <div className="tab-content job-tab">
              <div className="job-hero">
                <h3 className="job-role-title">{parseResult.job_requirements.job_title || 'Target Role'}</h3>
                {parseResult.job_requirements.experience_level && (
                  <span className="level-badge">Seniority: {parseResult.job_requirements.experience_level}</span>
                )}
                {parseResult.job_requirements.summary && (
                  <p className="job-summary">{parseResult.job_requirements.summary}</p>
                )}
              </div>

              <div className="section-block">
                <h4 className="section-heading">Core Evaluation Competencies</h4>
                <div className="tags-cloud">
                  {parseResult.job_requirements.core_competencies?.map((comp, idx) => (
                    <span key={idx} className="comp-tag core">⚡ {comp}</span>
                  ))}
                </div>
              </div>

              <div className="section-block">
                <h4 className="section-heading">Required Technical Skills</h4>
                <div className="tags-cloud">
                  {parseResult.job_requirements.required_skills?.map((skill, idx) => (
                    <span key={idx} className="skill-tag required">✓ {skill}</span>
                  ))}
                </div>
              </div>

              {parseResult.job_requirements.responsibilities?.length > 0 && (
                <div className="section-block">
                  <h4 className="section-heading">Key Responsibilities</h4>
                  <ul className="responsibilities-list">
                    {parseResult.job_requirements.responsibilities.map((resp, idx) => (
                      <li key={idx}>{resp}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: Raw JSON */}
          {activeTab === 'json' && (
            <div className="tab-content json-tab">
              <pre className="json-pre">{JSON.stringify(parseResult, null, 2)}</pre>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
