from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.profile import CandidateProfile, JobRequirements


class CompetencyPlanItem(BaseModel):
    """An individual planned competency topic within the interview session."""
    competency: str = Field(..., description="Technical competency to evaluate")
    difficulty: str = Field(default="Medium", description="Target difficulty ('Easy', 'Medium', 'Hard')")
    order_index: int = Field(..., description="0-indexed order position in the interview")
    scope: str = Field(default="shared", description="'shared' or 'job_specific'")
    rationale: Optional[str] = Field(None, description="Reason this competency was scheduled")


class CreateSessionRequest(BaseModel):
    """Payload to initialize a new interview session."""
    candidate_profile: CandidateProfile
    job_requirements: JobRequirements
    total_questions: int = Field(default=5, ge=1, le=10, description="Total planned questions")


class GeneratedQuestion(BaseModel):
    """Structured question grounded in retrieved evidence."""
    question_id: str
    session_id: str
    order_index: int
    competency: str
    difficulty: str
    question_text: str
    expected_criteria: List[str] = Field(
        default_factory=list,
        description="Key technical concepts candidate is expected to mention"
    )
    retrieved_chunk_ids: List[str] = Field(
        default_factory=list,
        description="IDs of Knowledge Base chunks used as evidence"
    )
    retrieved_context: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Evidence chunk texts and source provenance"
    )
    follow_up_rationale: Optional[str] = None
    status: str = Field(default="unanswered", description="'unanswered' | 'answered' | 'evaluated'")


class SessionResponse(BaseModel):
    """Interview session details and state machine progress."""
    session_id: str
    status: str = Field(
        ...,
        description="State: 'setup', 'profile_ready', 'question_ready', 'awaiting_answer', 'evaluating', 'completed'"
    )
    current_question_index: int
    total_questions: int
    competency_plan: List[CompetencyPlanItem]
    candidate_profile: CandidateProfile
    job_requirements: JobRequirements
    created_at: str
    updated_at: str


class CreateSessionResponse(BaseModel):
    """Response returned upon session creation, including first generated question."""
    session: SessionResponse
    initial_question: Optional[GeneratedQuestion] = None


class NextQuestionResponse(BaseModel):
    """Response when advancing to the next question in an interview."""
    session: SessionResponse
    question: Optional[GeneratedQuestion] = None
    is_completed: bool = False

