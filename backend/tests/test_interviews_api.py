from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SAMPLE_PROFILE = {
    "name": "Jordan Dev",
    "email": "jordan@example.com",
    "title": "Backend Software Engineer",
    "years_of_experience": 4.0,
    "primary_competencies": ["Python FastAPI Concurrency", "Database Design & Caching", "Docker"],
    "work_history": [
        {
            "company": "Tech Corp",
            "role": "Backend Engineer",
            "start_date": "2021",
            "end_date": "Present",
            "highlights": ["Built async microservices handling 5,000 req/sec."],
        }
    ],
    "education": [],
    "key_projects": [],
}

SAMPLE_JOB = {
    "title": "Senior Backend Engineer",
    "company": "Nexus Systems",
    "experience_level": "Senior",
    "core_competencies": ["Python FastAPI Concurrency", "System Architecture & Design"],
    "responsibilities": ["Scale distributed backend APIs"],
    "qualification_keywords": ["FastAPI", "PostgreSQL", "Redis"],
}


def test_api_create_session():
    payload = {
        "candidate_profile": SAMPLE_PROFILE,
        "job_requirements": SAMPLE_JOB,
        "total_questions": 3,
    }
    response = client.post("/api/interviews", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert "session" in data
    assert "initial_question" in data

    session = data["session"]
    initial_q = data["initial_question"]

    assert session["session_id"].startswith("s_")
    assert session["status"] == "question_ready"
    assert session["current_question_index"] == 0
    assert session["total_questions"] == 3
    assert len(session["competency_plan"]) == 3

    assert initial_q["session_id"] == session["session_id"]
    assert initial_q["order_index"] == 0
    assert len(initial_q["question_text"]) > 10
    assert len(initial_q["expected_criteria"]) >= 2


def test_api_get_session_and_questions():
    # 1. Create session
    create_res = client.post(
        "/api/interviews",
        json={
            "candidate_profile": SAMPLE_PROFILE,
            "job_requirements": SAMPLE_JOB,
            "total_questions": 2,
        },
    )
    assert create_res.status_code == 201
    session_id = create_res.json()["session"]["session_id"]

    # 2. Get session
    get_res = client.get(f"/api/interviews/{session_id}")
    assert get_res.status_code == 200
    session_data = get_res.json()
    assert session_data["session_id"] == session_id
    assert session_data["status"] == "question_ready"

    # 3. List questions
    q_res = client.get(f"/api/interviews/{session_id}/questions")
    assert q_res.status_code == 200
    q_list = q_res.json()
    assert len(q_list) == 1
    assert q_list[0]["order_index"] == 0


def test_api_next_question_and_completion():
    create_res = client.post(
        "/api/interviews",
        json={
            "candidate_profile": SAMPLE_PROFILE,
            "job_requirements": SAMPLE_JOB,
            "total_questions": 2,
        },
    )
    session_id = create_res.json()["session"]["session_id"]

    # Advance to question 2
    next_res = client.post(f"/api/interviews/{session_id}/next-question")
    assert next_res.status_code == 200
    next_data = next_res.json()
    assert not next_data["is_completed"]
    assert next_data["question"]["order_index"] == 1

    # Advance past total questions -> interview completes
    complete_res = client.post(f"/api/interviews/{session_id}/next-question")
    assert complete_res.status_code == 200
    complete_data = complete_res.json()
    assert complete_data["is_completed"]
    assert complete_data["question"] is None
    assert complete_data["session"]["status"] == "completed"


def test_api_transition_state():
    create_res = client.post(
        "/api/interviews",
        json={
            "candidate_profile": SAMPLE_PROFILE,
            "job_requirements": SAMPLE_JOB,
            "total_questions": 3,
        },
    )
    session_id = create_res.json()["session"]["session_id"]

    # Valid transition to awaiting_answer
    trans_res = client.post(
        f"/api/interviews/{session_id}/transition",
        json={"target_state": "awaiting_answer"},
    )
    assert trans_res.status_code == 200
    assert trans_res.json()["status"] == "awaiting_answer"

    # Illegal transition
    bad_res = client.post(
        f"/api/interviews/{session_id}/transition",
        json={"target_state": "completed"},  # Not allowed from awaiting_answer directly
    )
    assert bad_res.status_code == 400


def test_api_session_not_found():
    res = client.get("/api/interviews/nonexistent_session_id")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

