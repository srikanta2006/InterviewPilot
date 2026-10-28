# InterviewPilot

InterviewPilot is an AI-powered interview preparation application. A candidate provides a resume and job description to receive personalized, competency-focused interview questions, submits text or voice responses, and receives rubric-based evaluations with cited reference evidence.

---

## Architecture & Technology Stack

- **Frontend:** React 19 + Vite (Vanilla CSS design system, responsive UI)
- **Backend:** Python + FastAPI (Async REST API, Pydantic v2 schemas)
- **LLM Provider:** Groq API (`llama-3.3-70b-versatile` / `llama-3.1-8b-instant`)
- **Vector Store:** ChromaDB (Persistent local embeddings)
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2`
- **Relational Storage:** SQLite (Interview sessions, questions, evaluations)
- **Testing & Tooling:** `pytest` (Backend), `oxlint` & `vite` (Frontend)

---

## Prerequisites

- **Python:** 3.10+ (Tested on Python 3.13.13)
- **Node.js:** 18+ (Tested on Node v22.14.0 / npm 10.9.2)
- **Git**

---

## Repository Structure

```text
interviewpilot/
├── MASTER_PLAN.md        # Architecture, product vision, and phased roadmap
├── AGENT_WORKFLOW.md     # Engineering rules and approval protocols
├── PHASE_LOG.md          # Execution log and phase approval audit trail
├── README.md             # Repository documentation and local run instructions
├── .gitignore            # Git exclusion rules (virtual environments, secrets, databases)
├── .env.example          # Root environment variable template
├── backend/
│   ├── .env.example      # Backend environment template
│   ├── requirements.txt  # Python baseline dependencies
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py     # Pydantic Settings configuration
│   │   └── main.py       # FastAPI application and health endpoints
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_health.py # Pytest health endpoint tests
│   └── .venv/            # Local virtual environment (ignored by Git)
└── frontend/
    ├── package.json      # Frontend dependencies and npm scripts
    ├── vite.config.js    # Vite configuration
    ├── index.html        # HTML entry point
    └── src/
        ├── App.jsx       # Health monitor and system status dashboard
        ├── App.css       # Cockpit styling
        ├── index.css     # Global theme variables and typography
        └── main.jsx      # React DOM entry point
```

---

## Local Setup & Quickstart

### 1. Backend Setup

From the repository root:

```powershell
# Navigate to backend directory
cd backend

# Create a virtual environment (if not already created)
python -m venv .venv

# Activate the virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
.\.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create local environment file from example template
Copy-Item .env.example .env
# Linux / macOS: cp .env.example .env

# Run the FastAPI server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend is now accessible at:
- **API Root:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Health Check:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- **Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### 2. Frontend Setup

In a new terminal window:

```powershell
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```

The frontend dashboard will be available at:
- **Web App:** [http://localhost:5173](http://localhost:5173)

---

## Verification & Testing

### Backend Automated Tests

Run the backend test suite using pytest:

```powershell
cd backend
.\.venv\Scripts\pytest -v
```

Expected output:
```text
tests/test_health.py::test_root_endpoint PASSED
tests/test_health.py::test_health_endpoint PASSED
```

### Frontend Lint and Build Checks

Run the frontend code checks:

```powershell
cd frontend

# Lint check
npm run lint

# Production build check
npm run build
```

Expected output:
```text
0 warnings and 0 errors
✓ built in <time>ms
```

---

## Environment Variables & Security

- Never commit real API keys or sensitive values to version control.
- `.env` files, SQLite database files (`*.db`, `*.sqlite3`), ChromaDB persistence directories (`chroma_db/`), upload caches, and build outputs are strictly excluded via `.gitignore`.
- Set your Groq API key in `backend/.env` for local LLM inference when implementing future phases.

---

## Phase Status

- **Phase 0 (Workspace inspection & project setup):** COMPLETE (Human approval: PENDING)
- **Phase 1 (Document parsing & structured profile):** PENDING APPROVAL
