from unittest.mock import MagicMock
from app.schemas.knowledge import SearchResultItem
from app.schemas.profile import CandidateProfile, JobRequirements
from app.services.groq_client import GroqClientService
from app.services.question_generator import (
    LLMQuestionPayload,
    QuestionGenerator,
)


def create_sample_profile() -> CandidateProfile:
    return CandidateProfile(
        name="Alex River",
        title="Senior Python Backend Engineer",
        years_of_experience=5.5,
        primary_competencies=["FastAPI & Python", "PostgreSQL", "Docker", "System Architecture"],
    )


def create_sample_job() -> JobRequirements:
    return JobRequirements(
        title="Lead Platform Engineer",
        experience_level="Senior",
        core_competencies=["Python Concurrency", "System Architecture & Design", "Distributed Systems"],
    )


def create_mock_chunks():
    return [
        SearchResultItem(
            chunk_id="chunk_fastapi_001",
            document_id="doc_fastapi",
            source_name="FastAPI Concurrency Deep Dive",
            scope="shared",
            topic="Python FastAPI Concurrency",
            chunk_index=0,
            text="FastAPI runs async def endpoints on the main event loop thread. Blocking synchronous calls block all concurrent requests unless offloaded to a threadpool via run_in_threadpool.",
            similarity_score=0.92,
            distance=0.16,
            metadata={"doc_hash": "abc123hash"},
        ),
        SearchResultItem(
            chunk_id="chunk_fastapi_002",
            document_id="doc_fastapi",
            source_name="FastAPI Concurrency Deep Dive",
            scope="shared",
            topic="Python FastAPI Concurrency",
            chunk_index=1,
            text="Dependency injection with Depends manages per-request lifecycle and connection teardown cleanly using yield fixtures.",
            similarity_score=0.88,
            distance=0.24,
            metadata={"doc_hash": "abc123hash"},
        ),
    ]


def test_plan_competencies_ordering_and_count():
    profile = create_sample_profile()
    job = create_sample_job()

    # Plan 4 questions
    plan = QuestionGenerator.plan_competencies(profile, job, total_questions=4)

    assert len(plan) == 4
    # Job requirements should take initial precedence
    comp_names = [p.competency.lower() for p in plan]
    assert "python concurrency" in comp_names[0]
    # Check difficulty progression for senior
    assert all(p.difficulty in ["Medium", "Hard", "Easy"] for p in plan)
    assert plan[0].order_index == 0
    assert plan[3].order_index == 3


def test_deterministic_fallback_grounds_retrieved_chunk_ids():
    """Verify that returned question strictly binds to provided chunk IDs without hallucination."""
    generator = QuestionGenerator(groq_client=GroqClientService(api_key="placeholder_key"))
    chunks = create_mock_chunks()
    profile = create_sample_profile()
    job = create_sample_job()

    question = generator.generate_question(
        session_id="test_session_123",
        order_index=0,
        competency="Python FastAPI Concurrency",
        difficulty="Hard",
        candidate_profile=profile,
        job_requirements=job,
        retrieved_chunks=chunks,
    )

    assert question.session_id == "test_session_123"
    assert question.order_index == 0
    assert question.difficulty == "Hard"
    assert len(question.question_text) > 20
    assert len(question.expected_criteria) >= 3
    # Critical acceptance criterion: backend resolves source IDs, model cannot invent them
    assert question.retrieved_chunk_ids == ["chunk_fastapi_001", "chunk_fastapi_002"]
    assert len(question.retrieved_context) == 2
    assert question.retrieved_context[0]["source_name"] == "FastAPI Concurrency Deep Dive"


def test_groq_llm_generation_with_mocked_client():
    mock_groq = MagicMock(spec=GroqClientService)
    mock_groq.is_configured = True
    mock_groq.extract_structured_json.return_value = LLMQuestionPayload(
        question_text="How would you architect a distributed task worker in FastAPI using Redis Streams?",
        expected_criteria=["Consumer groups and ack handling", "Connection pooling", "Dead-letter queue"],
        follow_up_rationale="Tests asynchronous integration at senior scale.",
    )

    generator = QuestionGenerator(groq_client=mock_groq)
    chunks = create_mock_chunks()
    profile = create_sample_profile()
    job = create_sample_job()

    question = generator.generate_question(
        session_id="test_session_456",
        order_index=1,
        competency="FastAPI Distributed Systems",
        difficulty="Hard",
        candidate_profile=profile,
        job_requirements=job,
        retrieved_chunks=chunks,
    )

    assert mock_groq.extract_structured_json.called
    assert "Redis Streams" in question.question_text
    assert len(question.expected_criteria) == 3
    assert question.retrieved_chunk_ids == ["chunk_fastapi_001", "chunk_fastapi_002"]


def test_groq_malformed_fallback_handling():
    """If Groq returns None due to malformed output or error, fallback activates gracefully."""
    mock_groq = MagicMock(spec=GroqClientService)
    mock_groq.is_configured = True
    mock_groq.extract_structured_json.return_value = None  # Simulates malformed response

    generator = QuestionGenerator(groq_client=mock_groq)
    chunks = create_mock_chunks()
    profile = create_sample_profile()
    job = create_sample_job()

    question = generator.generate_question(
        session_id="test_session_789",
        order_index=0,
        competency="React State Architecture",
        difficulty="Medium",
        candidate_profile=profile,
        job_requirements=job,
        retrieved_chunks=chunks,
    )

    # Question should still be successfully generated via deterministic fallback
    assert question.question_id.startswith("q_")
    assert "React" in question.question_text
    assert len(question.expected_criteria) >= 2


def test_duplicate_question_avoidance():
    generator = QuestionGenerator(groq_client=GroqClientService(api_key="placeholder_key"))
    chunks = create_mock_chunks()
    profile = create_sample_profile()
    job = create_sample_job()

    # Generate first question
    q1 = generator.generate_question(
        session_id="sess_dup",
        order_index=0,
        competency="FastAPI Concurrency",
        difficulty="Medium",
        candidate_profile=profile,
        job_requirements=job,
        retrieved_chunks=chunks,
        previous_questions=[],
    )

    # Pass q1 text into previous_questions for question 2 with same topic
    q2 = generator.generate_question(
        session_id="sess_dup",
        order_index=1,
        competency="FastAPI Concurrency",
        difficulty="Medium",
        candidate_profile=profile,
        job_requirements=job,
        retrieved_chunks=chunks,
        previous_questions=[q1.question_text],
    )

    # q2 must avoid being identical to q1
    assert q2.question_text != q1.question_text
    assert "operational" in q2.question_text.lower() or "monitor" in q2.question_text.lower()

