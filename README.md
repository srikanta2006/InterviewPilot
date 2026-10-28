# InterviewPilot 🎙️

**InterviewPilot** is an AI-powered, adaptive technical interview preparation platform designed for software engineers. Candidates provide a resume and job description to receive targeted competency-focused interview questions, submit answers via text or real-time voice speech-to-text, and receive deterministic rubric evaluations backed by verified knowledge base citations.

---

## Key Features

- **📄 Document Parsing & Profile Extraction:** Parses resumes and job descriptions (`.pdf`, `.docx`, `.txt`) into structured profiles (candidate skills, experience level, and core target competencies) with deterministic offline fallback.
- **🧠 Inspectable RAG Knowledge Base:** Persistent local ChromaDB vector store using `sentence-transformers/all-MiniLM-L6-v2`. Supports shared technical references (System Design, Concurrency, Distributed Systems) and job-specific knowledge with transparent citation provenance.
- **🎯 Dynamic Question Generation & Orchestration:** Plans competency coverage, adapts difficulty, and grounds questions in candidate background and retrieved reference chunks without hallucinating source metadata.
- **⚖️ 4-Dimension Rubric Evaluation:** Computes an objective 0–100 weighted score based on:
  $$\text{Score} = \frac{\text{Correctness} \times 30 + \text{Completeness} \times 30 + \text{Relevance} \times 20 + \text{Clarity} \times 20}{5}$$
  Strictly validates citations against real ChromaDB chunks, rejecting hallucinations and flagging insufficient evidence safely.
- **🎙️ Real-Time Voice Input:** Native browser speech-to-text with microphone status controls, live transcript buffering, editable pre-submission review, and graceful text fallback for unsupported environments.
- **📊 Comprehensive Report & Session History:** Generates post-interview diagnostic reports featuring hiring recommendations, radar breakdowns, actionable coaching tips, and question-by-question audit accordions. Past sessions are persisted in local SQLite and can be re-opened, reviewed, or deleted at any time.
- **🌿 Fresh Mint & Olive Light Theme:** High-contrast, accessibility-focused light interface using a custom organic palette (`#1D1E18` Carbon Black, `#6B8F71` Dusty Olive, `#AAD2BA` Celadon, `#D9FFF5` Frozen Water, `#B9F5D8` Celadon Mint).

---

## Architecture & Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 19, Vite, Web Speech API, Vanilla CSS Design System |
| **Backend** | Python 3.10+ (FastAPI, Uvicorn, Pydantic v2 Settings & Schemas) |
| **Vector Store** | ChromaDB (local persistence at `backend/chroma_db/`) |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` (runs 100% locally) |
| **Database** | SQLite (local session and evaluation persistence at `backend/interviewpilot.db`) |
| **LLM Provider** | Groq API (`llama-3.3-70b-versatile` / `llama-3.1-8b-instant`) with automatic deterministic offline fallback engine |
| **Code Quality** | Pytest (Backend, 72+ test suite), Oxlint & Vite Build (Frontend) |

---

## Repository Structure

```text
interviewpilot/
├── MASTER_PLAN.md                # System design, architecture, and phase specifications
├── AGENT_WORKFLOW.md             # Strict engineering protocols and quality gates
├── PHASE_LOG.md                  # Detailed phase execution audit trail & approvals
├── README.md                     # Project documentation & local startup guide
├── .gitignore                    # Secrets, virtualenvs, databases, & cache exclusions
├── .env.example                  # Root environment template
├── knowledge_base/               # Reference technical documentation
│   ├── shared/                   # System design, concurrency, distributed systems
│   └── job_specific/             # Role-specific criteria and domain documents
├── backend/
│   ├── .env.example              # Backend environment template (safe placeholders)
│   ├── requirements.txt          # Python dependencies
│   ├── app/
│   │   ├── main.py               # FastAPI application & router mounting
│   │   ├── config.py             # App configuration & CORS settings
│   │   ├── api/                  # REST API route handlers
│   │   │   ├── documents.py      # Resume & job description upload & parsing
│   │   │   ├── knowledge.py      # Knowledge base ingestion & retrieval search
│   │   │   └── interviews.py     # Session creation, questions, answers, evaluations, reports
│   │   ├── schemas/              # Pydantic v2 data models
│   │   │   ├── document.py       # Profile & job specification schemas
│   │   │   ├── knowledge.py      # Document chunk & search result schemas
│   │   │   ├── interview.py      # Session states & question schemas
│   │   │   ├── evaluation.py     # Rubric dimension scores & citation schemas
│   │   │   └── report.py         # Final interview report & history item schemas
│   │   ├── services/             # Core business logic & AI pipelines
│   │   │   ├── parser.py         # Multi-format document parser (.pdf, .docx, .txt)
│   │   │   ├── chunker.py        # Semantic sliding-window text chunker
│   │   │   ├── embeddings.py     # Local Sentence-Transformers embedding service
│   │   │   ├── retriever.py      # ChromaDB vector retrieval with scope filtering
│   │   │   ├── groq_client.py    # Resilient Groq LLM client with retry & fallback
│   │   │   ├── question_generator.py # Context-grounded adaptive question generator
│   │   │   ├── answer_evaluator.py   # Rubric scoring & citation hallucination verifier
│   │   │   └── orchestrator.py   # Session state machine & workflow coordination
│   │   └── db/
│   │       └── session.py        # SQLite schema, tables, and CRUD operations
│   └── tests/                    # 72+ Pytest automated unit and integration tests
└── frontend/
    ├── package.json              # React 19 dependencies & scripts
    ├── vite.config.js            # Vite configuration
    └── src/
        ├── main.jsx              # React DOM entrypoint
        ├── index.css             # Light theme design tokens & global CSS variables
        ├── App.jsx               # Application shell, navigation, & health status
        ├── App.css               # Header, navigation, & system stats styling
        └── components/           # Interactive UI views
            ├── DocumentSetup.jsx      # Resume & job spec parser cockpit
            ├── KnowledgeBase.jsx      # Vector RAG search & document manager
            ├── InterviewWorkspace.jsx # Adaptive interview arena with voice & rubric
            ├── InterviewReport.jsx    # Comprehensive final report view
            └── InterviewHistory.jsx   # Past session history management table
```

---

## Local Setup & Quickstart

### Prerequisites
- **Python 3.10+** (Tested on Python 3.13)
- **Node.js 18+** (Tested on Node v22 / npm 10)
- **Git**

---

### Step 1: Start the Backend (Terminal 1)

```powershell
# Navigate to backend directory
cd backend

# Create and activate virtual environment (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server on port 8000
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

> **API Verification:**
> - Health Endpoint: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
> - Interactive Swagger Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Step 2: Start the Frontend (Terminal 2)

```powershell
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite dev server on port 5173
npm run dev
```

> **Web App:** Open your browser to **[http://localhost:5173](http://localhost:5173)**.

---

### Step 3: (Optional) Enabling Live Groq LLM

InterviewPilot functions **100% offline out-of-the-box** using its deterministic fallback engine. If you want to use live Groq LLM models:

1. Copy `backend/.env.example` to `backend/.env`:
   ```powershell
   Copy-Item backend\.env.example backend\.env
   ```
2. Insert your personal Groq API key:
   ```env
   GROQ_API_KEY=gsk_your_actual_key_here
   ```
3. Restart the backend process.

*(Note: Real `.env` files and local databases are strictly excluded by `.gitignore`).*

---

## Testing & Quality Verification

### Backend Automated Test Suite (72 tests)
Run the full test suite in `backend/`:

```powershell
cd backend
.\.venv\Scripts\pytest -v
```

Expected result:
```text
======================= 72 passed, 13 warnings in 6.11s =======================
```

The test suite thoroughly validates:
- **`test_parser.py`**: Valid, empty, corrupt, and oversized file handling across `.pdf`, `.docx`, and `.txt`.
- **`test_chunker.py`**: Semantic token chunking, overlap calculations, and metadata integrity.
- **`test_retriever.py`**: ChromaDB vector indexing, semantic search, scope filtering, and idempotent re-indexing.
- **`test_question_generator.py`**: Structured competency planning, deduplication, and context grounding.
- **`test_score_formula.py`**: Boundary values (0 and 100), rubric weight formula precision, and range exceptions.
- **`test_answer_evaluator.py`**: Rubric evaluations, rejection of hallucinated citation IDs, and insufficient evidence safety flags.
- **`test_orchestrator.py` & `test_report.py`**: End-to-end interview state machine transitions, SQLite persistence, report aggregation, and session history management.

### Frontend Linter and Production Build
Run checks in `frontend/`:

```powershell
cd frontend

# Oxlint code check
npm run lint

# Vite production bundle build
npm run build
```

Expected result:
```text
Found 0 warnings and 0 errors.
✓ built in ~200-300ms
```

---

## Security & Privacy Guardrails

- **Zero Secret Leakage:** No API keys are committed or returned in client payloads (`test_no_secret_leakage_in_response`).
- **Prompt Injection Boundaries:** Candidate inputs and untrusted documents are encapsulated within explicit structural delimiters in prompts.
- **Citation Hallucination Prevention:** The backend independently resolves and verifies every cited chunk ID against ChromaDB; unverified IDs are discarded.
- **Insufficient Evidence Protection:** When reference evidence is ambiguous or absent, answers are flagged with `insufficient_evidence` and scored 0.0 rather than hallucinating facts.
- **Cascading Deletion:** Deleting an interview session from the UI permanently purges all associated questions, answers, and evaluations from SQLite.

---

## Phase Status Summary

- **Phase 0 — Workspace inspection & project setup:** APPROVED
- **Phase 1 — Document parsing & structured profile:** APPROVED
- **Phase 2 — Knowledge base & inspectable RAG:** APPROVED
- **Phase 3 — Question generation & state machine:** APPROVED
- **Phase 4 — Answer evaluation & scoring rubric:** APPROVED
- **Phase 5 — Complete text interview & report UI:** APPROVED
- **Phase 6 — Voice input, hardening, & portfolio delivery:** IN PROGRESS
