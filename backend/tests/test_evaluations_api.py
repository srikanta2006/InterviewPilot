from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SAMPLE_PROFILE = {
    "name": "Jordan Dev",
    "title": "Backend Software Engineer",
    "years_of_experience": 4.0,
    "primary_competencies": ["Python FastAPI Concurrency", "Database Design & Caching"],
    "work_history": [],
    "education": [],
    "key_projects": [],
}

SAMPLE_JOB = {
    "title": "Senior Backend Engineer",
    "company": "Nexus Systems",
    "experience_level": "Senior",
    "core_competencies": ["Python FastAPI Concurrency", "Database Design & Caching"],
    "responsibilities": ["Build reliable backend APIs"],
    "qualification_keywords": ["FastAPI", "Python", "Redis"],
}


def test_submit_answer_and_retrieve_evaluation():
    # 0. Ingest reference document so knowledge base has grounding context for FastAPI
    ingest_res = client.post(
        "/api/knowledge/ingest",
        data={
            "text": "FastAPI runs async def endpoints on the main event loop thread. Synchronous blocking calls must be offloaded via run_in_threadpool. Depends provides yield cleanup.",
            "source_name": "FastAPI Concurrency Guide",
            "scope": "shared",
            "topic": "Python FastAPI Concurrency",
            "document_id": "doc_fastapi_eval_test",
        },
    )
    assert ingest_res.status_code == 200

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
        create_data = create_res.json()
        session_id = create_data["session"]["session_id"]
        initial_q = create_data["initial_question"]
        question_id = initial_q["question_id"]

        # 2. Submit candidate answer
        answer_text = (
            "In FastAPI, async def handlers execute on the main asyncio thread. Blocking sync calls must be offloaded "
            "to a threadpool using run_in_threadpool to prevent event loop starvation. Depends provides yield cleanup."
        )
        submit_res = client.post(
            f"/api/interviews/{session_id}/questions/{question_id}/answer",
            json={"answer_text": answer_text},
        )
        assert submit_res.status_code == 200
        submit_data = submit_res.json()

        assert "evaluation" in submit_data
        eval_res = submit_data["evaluation"]
        assert eval_res["question_id"] == question_id
        assert eval_res["evaluation_status"] == "completed"
        assert eval_res["dimension_scores"]["correctness"] >= 1
        assert 0 <= eval_res["weighted_score"] <= 100
        assert len(eval_res["citation_chunk_ids"]) > 0
        assert submit_data["has_more_questions"] is True

        # 3. Retrieve evaluation via GET endpoint
        get_eval_res = client.get(
            f"/api/interviews/{session_id}/questions/{question_id}/evaluation"
        )
        assert get_eval_res.status_code == 200
        retrieved_eval = get_eval_res.json()
        assert retrieved_eval["evaluation_id"] == eval_res["evaluation_id"]
        assert retrieved_eval["weighted_score"] == eval_res["weighted_score"]

        # 4. List all evaluations for the session
        list_eval_res = client.get(f"/api/interviews/{session_id}/evaluations")
        assert list_eval_res.status_code == 200
        eval_list = list_eval_res.json()
        assert len(eval_list) == 1
        assert eval_list[0]["evaluation_id"] == eval_res["evaluation_id"]
    finally:
        client.delete("/api/knowledge/documents/doc_fastapi_eval_test")



def test_duplicate_submission_idempotency():
    """Submitting an updated answer for the same question updates cleanly without constraint error."""
    create_res = client.post(
        "/api/interviews",
        json={
            "candidate_profile": SAMPLE_PROFILE,
            "job_requirements": SAMPLE_JOB,
            "total_questions": 2,
        },
    )
    session_id = create_res.json()["session"]["session_id"]
    question_id = create_res.json()["initial_question"]["question_id"]

    # First submission
    res1 = client.post(
        f"/api/interviews/{session_id}/questions/{question_id}/answer",
        json={"answer_text": "Initial quick draft response about asyncio."},
    )
    assert res1.status_code == 200

    # Second submission (refinement/update for the same question)
    res2 = client.post(
        f"/api/interviews/{session_id}/questions/{question_id}/answer",
        json={"answer_text": "Detailed refined response discussing event loop starvation and threadpool execution."},
    )
    assert res2.status_code == 200
    eval2 = res2.json()["evaluation"]
    assert eval2["candidate_answer"].startswith("Detailed refined response")


def test_submit_answer_not_found():
    res = client.post(
        "/api/interviews/nonexistent_session/questions/nonexistent_q/answer",
        json={"answer_text": "Some text"},
    )
    assert res.status_code == 404
