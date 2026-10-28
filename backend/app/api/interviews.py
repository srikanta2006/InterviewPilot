import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel

from app.schemas.evaluation import (
    EvaluationResult,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.schemas.interview import (
    CreateSessionRequest,
    CreateSessionResponse,
    GeneratedQuestion,
    NextQuestionResponse,
    SessionResponse,
)
from app.schemas.report import (
    FinalInterviewReport,
    SessionListItem,
)

from app.services.orchestrator import InterviewOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter()

# Singleton orchestrator instance for API handling
orchestrator = InterviewOrchestrator()


class StateTransitionRequest(BaseModel):
    target_state: str


@router.get(
    "",
    response_model=List[SessionListItem],
    summary="List all past interview sessions for the local user",
)
def list_sessions():
    """Returns history of all interview sessions recorded in SQLite."""
    return orchestrator.list_all_sessions()



@router.post(
    "",
    response_model=CreateSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new interview session and generate the initial question",
)
def create_session(request: CreateSessionRequest):
    """
    Formulates a competency plan, creates the session in SQLite,
    queries the vector database for relevant evidence, and generates Question #1.
    """
    try:
        session, first_q = orchestrator.create_session(
            candidate_profile=request.candidate_profile,
            job_requirements=request.job_requirements,
            total_questions=request.total_questions,
        )
        return CreateSessionResponse(session=session, initial_question=first_q)
    except Exception as e:
        logger.error(f"Failed to create interview session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize interview session: {str(e)}",
        )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get interview session details and progress",
)
def get_session(session_id: str = Path(..., description="ID of the interview session")):
    """Retrieve the current state, progress index, and competency plan for a session."""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session '{session_id}' not found.",
        )
    return session


@router.post(
    "/{session_id}/next-question",
    response_model=NextQuestionResponse,
    summary="Generate the next question according to the competency plan",
)
def next_question(session_id: str = Path(..., description="ID of the interview session")):
    """
    Advances the interview state machine: retrieves the next planned competency,
    queries reference knowledge chunks, prevents duplicate questions, and persists question.
    """
    try:
        session, new_q, is_completed = orchestrator.generate_next_question(session_id)
        return NextQuestionResponse(
            session=session,
            question=new_q,
            is_completed=is_completed,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(ve).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Error generating next question: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate next question: {str(e)}",
        )


@router.get(
    "/{session_id}/questions",
    response_model=List[GeneratedQuestion],
    summary="List all questions generated for this interview session",
)
def list_questions(session_id: str = Path(..., description="ID of the interview session")):
    """Returns chronological list of all generated questions with retrieved source evidence."""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session '{session_id}' not found.",
        )
    return orchestrator.get_questions(session_id)


@router.post(
    "/{session_id}/transition",
    response_model=SessionResponse,
    summary="Explicitly transition session state machine",
)
def transition_session(
    payload: StateTransitionRequest,
    session_id: str = Path(..., description="ID of the interview session"),
):
    """Safely transitions session state (e.g. from question_ready to awaiting_answer)."""
    try:
        return orchestrator.transition_state(session_id, payload.target_state)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Error transitioning state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transition session state: {str(e)}",
        )


@router.post(
    "/{session_id}/questions/{question_id}/answer",
    response_model=SubmitAnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit candidate answer for evaluation against rubric and retrieved context",
)
def submit_answer(
    payload: SubmitAnswerRequest,
    session_id: str = Path(..., description="ID of the interview session"),
    question_id: str = Path(..., description="ID of the question being answered"),
):
    """
    Submits candidate answer, executes secondary retrieval grounded in the question and answer,
    evaluates against the 4-dimension rubric (Correctness, Completeness, Relevance, Clarity),
    computes weighted score in Python, validates citations, and updates session state.
    """
    try:
        eval_result = orchestrator.submit_and_evaluate_answer(
            session_id=session_id,
            question_id=question_id,
            answer_text=payload.answer_text,
        )
        session = orchestrator.get_session(session_id)
        has_more = (session.current_question_index + 1) < session.total_questions

        return SubmitAnswerResponse(
            evaluation=eval_result,
            session_id=session_id,
            question_id=question_id,
            session_status=session.status,
            has_more_questions=has_more,
        )
    except ValueError as ve:
        err_msg = str(ve)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in err_msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=err_msg)
    except Exception as e:
        logger.error(f"Error evaluating answer: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate answer: {str(e)}",
        )


@router.get(
    "/{session_id}/questions/{question_id}/evaluation",
    response_model=EvaluationResult,
    summary="Get evaluation for a specific question",
)
def get_evaluation_for_question(
    session_id: str = Path(..., description="ID of the interview session"),
    question_id: str = Path(..., description="ID of the question"),
):
    """Fetch stored evaluation result with verified citations and dimension scores."""
    evaluation = orchestrator.get_evaluation_for_question(question_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No evaluation found for question '{question_id}'.",
        )
    return evaluation


@router.get(
    "/{session_id}/evaluations",
    response_model=List[EvaluationResult],
    summary="List all evaluations completed in this interview session",
)
def list_session_evaluations(
    session_id: str = Path(..., description="ID of the interview session"),
):
    """Fetch all completed evaluations for the session ordered by creation time."""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session '{session_id}' not found.",
        )
    return orchestrator.list_evaluations_for_session(session_id)


@router.get(
    "/{session_id}/report",
    response_model=FinalInterviewReport,
    summary="Generate comprehensive final interview performance report",
)
def get_session_report(
    session_id: str = Path(..., description="ID of the interview session"),
):
    """
    Synthesize complete performance report: composite score, dimension averages,
    competency scores, question breakdowns, key strengths, and verified evidence citations.
    """
    try:
        return orchestrator.get_interview_report(session_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error compiling interview report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate interview report: {str(e)}",
        )


@router.delete(
    "/{session_id}",
    summary="Delete an interview session from SQLite",
)
def delete_session(
    session_id: str = Path(..., description="ID of the interview session"),
):
    """Remove session and all associated questions and evaluations."""
    deleted = orchestrator.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session '{session_id}' not found.",
        )
    return {"success": True, "session_id": session_id}



