from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SAMPLE_PROFILE = {
    "name": "Alex River",
    "title": "Senior Platform Engineer",
    "years_of_experience": 5.0,
    "primary_competencies": ["Python FastAPI Concurrency", "Database Design & Caching"],
    "work_history": [],
    "education": [],
    "key_projects": [],
}

SAMPLE_JOB = {
    "title": "Staff Engineer",
    "company": "Nexus Platforms",
    "experience_level": "Staff",
    "core_competencies": ["Python FastAPI Concurrency", "Database Design & Caching"],
    "responsibilities": ["Lead distributed architecture"],
    "qualification_keywords": ["FastAPI", "Python", "Redis"],
}


def test_generate_interview_report_with_evaluations():
    # 0. Ingest reference document for grounding
    client.post(
        "/api/knowledge/ingest",
        data={
            "text": "FastAPI runs async def endpoints on the main event loop thread. Synchronous blocking calls must be offloaded via run_in_threadpool. Depends provides yield cleanup.",
            "source_name": "FastAPI Concurrency Guide",
            "scope": "shared",
            "topic": "Python FastAPI Concurrency",
            "document_id": "doc_fastapi_report_test",
        },
    )

    try:
        # 1. Create a session with 2 questions
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
        q1_id = create_res.json()["initial_question"]["question_id"]

        # 2. Answer question 1
        ans1_res = client.post(
            f"/api/interviews/{session_id}/questions/{q1_id}/answer",
            json={
                "answer_text": "In FastAPI, async def handlers execute on the asyncio loop. Synchronous blocking calls must be offloaded using run_in_threadpool. Depends handles yield cleanup."
            },
        )
        assert ans1_res.status_code == 200

        # 3. Advance to question 2 and answer it
        next_res = client.post(f"/api/interviews/{session_id}/next-question")
        assert next_res.status_code == 200
        q2_id = next_res.json()["question"]["question_id"]

        ans2_res = client.post(
            f"/api/interviews/{session_id}/questions/{q2_id}/answer",
            json={
                "answer_text": "For caching, we employ cache-aside with Redis, distributed locks for stampedes, and Bloom filters for cache penetration."
            },
        )
        assert ans2_res.status_code == 200

        # 4. Generate final report
        report_res = client.get(f"/api/interviews/{session_id}/report")
        assert report_res.status_code == 200
        report = report_res.json()

        assert report["session_id"] == session_id
        assert report["candidate_name"] == "Alex River"
        assert report["job_title"] == "Staff Engineer"
        assert report["total_questions"] == 2
        assert report["questions_evaluated"] == 2
        assert report["composite_score"] > 0.0
        assert report["performance_level"] in [
            "Strong Hire / Advanced",
            "Hire / Proficient",
            "Needs Review / Developing",
            "Needs Improvement",
        ]
        assert "correctness" in report["dimension_averages"]
        assert "completeness" in report["dimension_averages"]
        assert len(report["question_summaries"]) == 2
        assert report["question_summaries"][0]["status"] == "evaluated"
        assert len(report["key_strengths_summary"]) > 0
        assert len(report["citations_summary"]) > 0
    finally:
        client.delete("/api/knowledge/documents/doc_fastapi_report_test")


def test_interview_history_listing_and_deletion():
    # 1. Create a session
    create_res = client.post(
        "/api/interviews",
        json={
            "candidate_profile": SAMPLE_PROFILE,
            "job_requirements": SAMPLE_JOB,
            "total_questions": 3,
        },
    )
    assert create_res.status_code == 201
    session_id = create_res.json()["session"]["session_id"]

    # 2. List sessions from history endpoint
    list_res = client.get("/api/interviews")
    assert list_res.status_code == 200
    sessions = list_res.json()
    assert any(s["session_id"] == session_id for s in sessions)
    target = next(s for s in sessions if s["session_id"] == session_id)
    assert target["candidate_name"] == "Alex River"
    assert target["job_title"] == "Staff Engineer"
    assert target["total_questions"] == 3

    # 3. Delete session
    del_res = client.delete(f"/api/interviews/{session_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 4. Confirm deleted
    get_res = client.get(f"/api/interviews/{session_id}")
    assert get_res.status_code == 404


def test_report_on_unanswered_session():
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

    report_res = client.get(f"/api/interviews/{session_id}/report")
    assert report_res.status_code == 200
    report = report_res.json()
    assert report["composite_score"] == 0.0
    assert report["questions_evaluated"] == 0
    assert report["question_summaries"][0]["status"] == "unanswered"
