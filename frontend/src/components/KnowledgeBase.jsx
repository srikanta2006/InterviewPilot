import { useState, useEffect } from 'react'
import './KnowledgeBase.css'

const SAMPLE_QUERIES = [
  { label: 'FastAPI Concurrency', query: 'How does FastAPI handle async def vs def and the event loop?', scope: 'shared' },
  { label: 'React Hooks & Virtual DOM', query: 'Explain React reconciliation, key props, and memoization hooks', scope: 'shared' },
  { label: 'Redis & DB Indexing', query: 'What are the trade-offs of Cache-Aside vs Write-Through and B-Tree indexes?', scope: 'shared' },
  { label: 'Platform Architecture SLOs', query: 'What are the latency SLOs and evidence requirements for Nexus platform?', scope: 'job_specific' },
]

export function KnowledgeBase({ apiBase = 'http://127.0.0.1:8000', onProceedToInterview = null }) {
  const [documents, setDocuments] = useState([])
  const [loadingDocs, setLoadingDocs] = useState(true)
  const [seeding, setSeeding] = useState(false)

  // Ingest form
  const [showIngestForm, setShowIngestForm] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newTopic, setNewTopic] = useState('Backend')
  const [newScope, setNewScope] = useState('shared')
  const [newText, setNewText] = useState('')
  const [ingesting, setIngesting] = useState(false)

  // Search state
  const [searchQuery, setSearchQuery] = useState('FastAPI async def event loop and threadpool')
  const [searchScope, setSearchScope] = useState('')
  const [topK, setTopK] = useState(5)
  const [searchResults, setSearchResults] = useState(null)
  const [searching, setSearching] = useState(false)

  const [statusMsg, setStatusMsg] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  const fetchDocuments = async () => {
    setLoadingDocs(true)
    setErrorMsg('')
    try {
      const res = await fetch(`${apiBase}/api/knowledge/documents`)
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      const data = await res.json()
      setDocuments(data)
    } catch (err) {
      setErrorMsg(`Failed to fetch documents: ${err.message}`)
    } finally {
      setLoadingDocs(false)
    }
  }

  const handleSeedDefaults = async () => {
    setSeeding(true)
    setStatusMsg('')
    setErrorMsg('')
    try {
      const res = await fetch(`${apiBase}/api/knowledge/seed-defaults`, { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      const data = await res.json()
      setStatusMsg(`Successfully seeded ${data.total_seeded} default technical reference documents.`)
      await fetchDocuments()
    } catch (err) {
      setErrorMsg(`Seeding failed: ${err.message}`)
    } finally {
      setSeeding(false)
    }
  }

  const handleDelete = async (docId) => {
    if (!window.confirm(`Delete document '${docId}' from the reference library?`)) return
    setErrorMsg('')
    try {
      const res = await fetch(`${apiBase}/api/knowledge/documents/${docId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      setStatusMsg(`Deleted document ${docId}`)
      await fetchDocuments()
      if (searchResults) {
        setSearchResults((prev) => ({
          ...prev,
          results: prev.results.filter((r) => r.document_id !== docId),
        }))
      }
    } catch (err) {
      setErrorMsg(`Deletion failed: ${err.message}`)
    }
  }

  const handleIngest = async (e) => {
    e.preventDefault()
    if (!newTitle.trim() || !newText.trim()) {
      setErrorMsg('Please provide both document title and body text.')
      return
    }
    setIngesting(true)
    setErrorMsg('')
    setStatusMsg('')
    try {
      const formData = new FormData()
      formData.append('source_name', newTitle.trim())
      formData.append('topic', newTopic.trim())
      formData.append('scope', newScope)
      formData.append('text', newText.trim())

      const res = await fetch(`${apiBase}/api/knowledge/ingest`, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      const data = await res.json()
      setStatusMsg(`Added '${data.document_id}' to reference library (${data.chunks_created} sections).`)
      setNewTitle('')
      setNewText('')
      setShowIngestForm(false)
      await fetchDocuments()
    } catch (err) {
      setErrorMsg(`Failed to save document: ${err.message}`)
    } finally {
      setIngesting(false)
    }
  }

  const executeSearch = async (queryToRun, scopeToUse) => {
    if (!queryToRun.trim()) return
    setSearching(true)
    setErrorMsg('')
    try {
      const payload = {
        query: queryToRun.trim(),
        top_k: Number(topK),
      }
      if (scopeToUse) payload.scope = scopeToUse

      const res = await fetch(`${apiBase}/api/knowledge/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      const data = await res.json()
      setSearchResults(data)
    } catch (err) {
      setErrorMsg(`Search failed: ${err.message}`)
    } finally {
      setSearching(false)
    }
  }

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    executeSearch(searchQuery, searchScope)
  }

  const handleQuickQuery = (item) => {
    setSearchQuery(item.query)
    setSearchScope(item.scope)
    executeSearch(item.query, item.scope)
  }

  useEffect(() => {
    let active = true

    fetch(`${apiBase}/api/knowledge/documents`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
        return res.json()
      })
      .then((data) => {
        if (active) {
          setDocuments(data)
          setLoadingDocs(false)
        }
      })
      .catch((err) => {
        if (active) {
          setErrorMsg(`Failed to fetch documents: ${err.message}`)
          setLoadingDocs(false)
        }
      })

    return () => {
      active = false
    }
  }, [apiBase])

  return (
    <section className="kb-container">
      {/* Header */}
      <div className="kb-header">
        <div>
          <h2 className="kb-title">Technical Reference Library</h2>
          <p className="kb-subtitle">
            Browse engineering concepts, architectural patterns, and standards used to generate questions and evaluate candidate responses.
          </p>
        </div>
        <div className="kb-actions">
          <button
            type="button"
            id="btn-seed-knowledge"
            className="btn-primary"
            onClick={handleSeedDefaults}
            disabled={seeding}
          >
            {seeding ? '⚡ Loading Topics...' : '⚡ Load Core Engineering Topics'}
          </button>
          <button
            type="button"
            id="btn-toggle-ingest"
            className="btn-secondary"
            onClick={() => setShowIngestForm(!showIngestForm)}
          >
            {showIngestForm ? '✕ Close Form' : '➕ Add Custom Reference'}
          </button>
          <button
            type="button"
            id="btn-refresh-docs"
            className="btn-secondary"
            onClick={fetchDocuments}
            disabled={loadingDocs}
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Reference Library Guidance Banner */}
      <div style={{ marginBottom: '20px', padding: '14px 20px', background: 'var(--color-frozen-water)', border: '1px solid var(--color-celadon)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <strong style={{ color: 'var(--color-carbon)' }}>📚 Technical Reference & Knowledge Base</strong>
          <p style={{ margin: '3px 0 0 0', fontSize: '13px', color: '#334155' }}>
            Explore reference topics or test search queries. Questions in your practice interview are aligned with this library.
          </p>
        </div>
        {onProceedToInterview && (
          <button
            type="button"
            id="btn-goto-interview-from-kb"
            className="btn-primary"
            onClick={onProceedToInterview}
          >
            Start Practice Interview →
          </button>
        )}
      </div>

      {statusMsg && (
        <div style={{ background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#6ee7b7', padding: '12px 16px', borderRadius: '8px', marginBottom: '18px', fontSize: '13px' }}>
          ✓ {statusMsg}
        </div>
      )}

      {errorMsg && (
        <div className="error-banner">
          ⚠️ {errorMsg}
        </div>
      )}

      {/* Ingest Form (Collapsible) */}
      {showIngestForm && (
        <form onSubmit={handleIngest} style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '14px', color: 'var(--accent-cyan)' }}>
            Add Custom Reference Document
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '14px', marginBottom: '14px' }}>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Source Title</label>
              <input
                type="text"
                className="query-input"
                placeholder="e.g. Distributed Database Patterns"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                required
              />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Scope</label>
              <select className="filter-select" style={{ width: '100%', height: '42px' }} value={newScope} onChange={(e) => setNewScope(e.target.value)}>
                <option value="shared">General Technical Concept</option>
                <option value="job_specific">Role-Specific Reference</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Domain Topic</label>
              <input
                type="text"
                className="query-input"
                placeholder="e.g. System Architecture"
                value={newTopic}
                onChange={(e) => setNewTopic(e.target.value)}
                required
              />
            </div>
          </div>
          <div style={{ marginBottom: '14px' }}>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Document Content (Markdown or Text)</label>
            <textarea
              className="text-input-area"
              rows={6}
              placeholder="Paste complete document text..."
              value={newText}
              onChange={(e) => setNewText(e.target.value)}
              required
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button type="button" className="btn-secondary" onClick={() => setShowIngestForm(false)}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={ingesting}>
              {ingesting ? 'Saving...' : 'Save to Library'}
            </button>
          </div>
        </form>
      )}

      {/* Two Column Section: Document Index & Live Search */}
      <div className="kb-grid">
        {/* Left: Indexed Documents Directory */}
        <div className="kb-panel">
          <div className="kb-panel-title">
            <span>📚</span>
            <span>Reference Library Documents ({documents.length})</span>
          </div>

          {loadingDocs ? (
            <div style={{ color: 'var(--text-muted)', fontSize: '13px', padding: '20px 0' }}>Loading reference documents...</div>
          ) : documents.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '36px 16px', color: 'var(--text-muted)' }}>
              <p style={{ marginBottom: '14px', fontSize: '13.5px' }}>No reference documents currently loaded.</p>
              <button type="button" className="btn-secondary" onClick={handleSeedDefaults} disabled={seeding}>
                ⚡ Load Core Engineering Topics
              </button>
            </div>
          ) : (
            <div className="docs-list">
              {documents.map((doc) => (
                <div key={doc.document_id} className="doc-card">
                  <div className="doc-info">
                    <span className="doc-title">{doc.source_name}</span>
                    <div className="doc-meta">
                      <span className={`scope-badge ${doc.scope}`}>{doc.scope}</span>
                      <span>Topic: <strong>{doc.topic}</strong></span>
                      <span>•</span>
                      <span>{doc.chunks_count} section{doc.chunks_count === 1 ? '' : 's'}</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn-delete-doc"
                    title={`Delete ${doc.document_id}`}
                    onClick={() => handleDelete(doc.document_id)}
                  >
                    🗑️
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Similarity Query Box */}
        <div className="kb-panel">
          <div className="kb-panel-title">
            <span>🔍</span>
            <span>Search Reference Library</span>
          </div>

          <form onSubmit={handleSearchSubmit} className="search-controls">
            <input
              id="kb-search-input"
              type="text"
              className="query-input"
              placeholder="Enter technical interview question or concept..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              required
            />

            <div className="search-filters-row">
              <select
                id="kb-scope-select"
                className="filter-select"
                value={searchScope}
                onChange={(e) => setSearchScope(e.target.value)}
              >
                <option value="">All Topics (General + Role-Specific)</option>
                <option value="shared">General Topics Only</option>
                <option value="job_specific">Role-Specific References Only</option>
              </select>

              <select
                id="kb-topk-select"
                className="filter-select"
                value={topK}
                onChange={(e) => setTopK(e.target.value)}
              >
                <option value={3}>Top 3 Results</option>
                <option value={5}>Top 5 Results</option>
                <option value={10}>Top 10 Results</option>
              </select>

              <button
                type="submit"
                id="btn-run-search"
                className="btn-primary"
                style={{ marginLeft: 'auto', padding: '8px 20px', fontSize: '13px' }}
                disabled={searching}
              >
                {searching ? 'Searching...' : 'Search Library'}
              </button>
            </div>

            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                Explore Sample Topics:
              </span>
              <div className="sample-queries-row">
                {SAMPLE_QUERIES.map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="sample-q-btn"
                    onClick={() => handleQuickQuery(item)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
          </form>
        </div>
      </div>

      {/* Retrieved Reference Results */}
      {searchResults && (
        <div id="rag-results-section" className="retrieval-results-section">
          <div className="retrieval-results-header">
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)' }}>
                Matched Reference Material
              </h3>
              <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                Query: <em>"{searchResults.query}"</em>
                {searchResults.scope_filter && ` • Filtered to scope: ${searchResults.scope_filter}`}
              </p>
            </div>
            <span className="results-count-pill">
              {searchResults.total_results} relevant section{searchResults.total_results === 1 ? '' : 's'} found
            </span>
          </div>

          {searchResults.results.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: '13.5px', textAlign: 'center', padding: '24px 0' }}>
              No matching reference material found.
            </div>
          ) : (
            searchResults.results.map((item, idx) => (
              <div key={item.chunk_id || idx} className="chunk-card">
                <div className="chunk-card-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span className="chunk-id-tag">Section #{item.chunk_index + 1}</span>
                    <span className={`scope-badge ${item.scope}`}>{item.scope}</span>
                    <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {item.source_name}
                    </span>
                  </div>
                  <div className="similarity-score-pill">
                    {(item.similarity_score * 100).toFixed(1)}% Match
                  </div>
                </div>

                <div className="chunk-source-provenance">
                  Topic: <strong>{item.topic}</strong> • Section #{item.chunk_index + 1}
                </div>

                <div className="chunk-body">
                  {item.text}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </section>
  )
}
