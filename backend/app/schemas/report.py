from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.evaluation import CitationItem, DimensionScores


class QuestionEvaluationSummary(BaseModel):
    """Aggregated summary of an individual interview question and its evaluation."""
    question_id: str
    order_index: int
    competency: str
    difficulty: str
    question_text: str
    candidate_answer: Optional[str] = None
    dimension_scores: Optional[DimensionScores] = None
    weighted_score: Optional[float] = None
    strengths: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    actionable_feedback: Optional[str] = None
    citations: List[CitationItem] = Field(default_factory=list)
    status: str = Field(default="unanswered")


class FinalInterviewReport(BaseModel):
    """Comprehensive performance and grounding report for a completed interview session."""
    session_id: str
    candidate_name: str
    job_title: str
    total_questions: int
    questions_evaluated: int
    composite_score: float = Field(..., ge=0.0, le=100.0, description="Overall weighted average score")
    performance_level: str = Field(..., description="Target hiring or proficiency band")
    dimension_averages: Dict[str, float] = Field(
        ...,
        description="Average scores (0.0 to 5.0) for correctness, completeness, relevance, clarity"
    )
    competency_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown of score earned per technical competency"
    )
    question_summaries: List[QuestionEvaluationSummary] = Field(default_factory=list)
    key_strengths_summary: List[str] = Field(default_factory=list)
    priority_improvements_summary: List[str] = Field(default_factory=list)
    citations_summary: List[CitationItem] = Field(default_factory=list)
    created_at: str


class SessionListItem(BaseModel):
    """Summary item for interview session history listing."""
    session_id: str
    status: str
    current_question_index: int
    total_questions: int
    candidate_name: str
    job_title: str
    questions_created: int
    questions_evaluated: int
    avg_score: Optional[float] = None
    created_at: str
    updated_at: str

