import os
import tempfile
import pytest
from app.db.session import DatabaseManager
from app.schemas.profile import CandidateProfile, JobRequirements
from app.services.orchestrator import InterviewOrchestrator
from app.services.retriever import KnowledgeRetriever


@pytest.fixture
def temp_db_and_orchestrator(tmp_path):
    db_file = os.path.join(tmp_path, "test_interviewpilot.db")
    db_mgr = DatabaseManager(db_path=db_file)
    chroma_dir = os.path.join(tmp_path, "chroma")
    retriever = KnowledgeRetriever(persist_dir=chroma_dir)
    orchestrator = InterviewOrchestrator(db_manager=db_mgr, retriever=retriever)
    return db_mgr, orchestrator


def create_test_profile():
    return CandidateProfile(
        name="Sarah Connor",
        title="Full Stack Software Engineer",
        years_of_experience=4.0,
        primary_competencies=["React", "Python", "REST APIs", "SQL"],
    )


def create_test_job():
    return JobRequirements(
        title="Full Stack Developer",
        experience_level="Mid-Senior",
        core_competencies=["React State Architecture", "Python FastAPI Concurrency", "Database Design & Caching"],
    )


def test_create_session(temp_db_and_orchestrator):
    _, orchestrator = temp_db_and_orchestrator
    profile = create_test_profile()
    job = create_test_job()

    session, initial_q = orchestrator.create_session(
        candidate_profile=profile,
        job_requirements=job,
        total_questions=3,
    )

    assert session.session_id.startswith("s_")
    assert session.status == "question_ready"
    assert session.current_question_index == 0
    assert session.total_questions == 3
    assert len(session.competency_plan) == 3

    assert initial_q is not None
    assert initial_q.session_id == session.session_id
    assert initial_q.order_index == 0
    assert len(initial_q.question_text) > 10

    # Verify retrieved from DB
    questions = orchestrator.get_questions(session.session_id)
    assert len(questions) == 1
    assert questions[0].question_id == initial_q.question_id


def test_progression_to_completion(temp_db_and_orchestrator):
    _, orchestrator = temp_db_and_orchestrator
    profile = create_test_profile()
    job = create_test_job()

    session, q0 = orchestrator.create_session(
        candidate_profile=profile,
        job_requirements=job,
        total_questions=2,
    )

    assert session.current_question_index == 0

    # Advance to question 2 (index 1)
    session, q1, is_completed = orchestrator.generate_next_question(session.session_id)
    assert not is_completed
    assert q1 is not None
    assert session.current_question_index == 1
    assert q1.order_index == 1

    # Attempt to advance beyond total questions -> complete interview
    session, q2, is_completed = orchestrator.generate_next_question(session.session_id)
    assert is_completed
    assert q2 is None
    assert session.status == "completed"

    # All generated questions stored in DB
    all_qs = orchestrator.get_questions(session.session_id)
    assert len(all_qs) == 2


def test_state_transitions_and_validation(temp_db_and_orchestrator):
    _, orchestrator = temp_db_and_orchestrator
    profile = create_test_profile()
    job = create_test_job()

    session, _ = orchestrator.create_session(
        candidate_profile=profile,
        job_requirements=job,
        total_questions=3,
    )

    # Valid transition: question_ready -> awaiting_answer
    updated = orchestrator.transition_state(session.session_id, "awaiting_answer")
    assert updated.status == "awaiting_answer"

    # Valid transition: awaiting_answer -> question_ready
    updated = orchestrator.transition_state(session.session_id, "question_ready")
    assert updated.status == "question_ready"

    # Illegal transition: question_ready directly to setup
    with pytest.raises(ValueError, match="Illegal state transition"):
        orchestrator.transition_state(session.session_id, "setup")


def test_persistence_across_orchestrator_instances(tmp_path):
    db_file = os.path.join(tmp_path, "persisted.db")
    db1 = DatabaseManager(db_path=db_file)
    orch1 = InterviewOrchestrator(db_manager=db1)

    profile = create_test_profile()
    job = create_test_job()
    session, q0 = orch1.create_session(profile, job, total_questions=3)

    # Create brand new orchestrator pointing to the same SQLite DB file
    db2 = DatabaseManager(db_path=db_file)
    orch2 = InterviewOrchestrator(db_manager=db2)

    loaded_session = orch2.get_session(session.session_id)
    assert loaded_session is not None
    assert loaded_session.session_id == session.session_id
    assert loaded_session.status == "question_ready"

    loaded_qs = orch2.get_questions(session.session_id)
    assert len(loaded_qs) == 1
    assert loaded_qs[0].question_id == q0.question_id

