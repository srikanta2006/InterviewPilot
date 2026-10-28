from typing import List, Optional
from pydantic import BaseModel, Field

RUBRIC_WEIGHTS = {
    "correctness": 30,
    "completeness": 30,
    "relevance": 20,
    "clarity": 20,
}
RUBRIC_VERSION = "1.0.0"


def calculate_weighted_score(correctness: int, completeness: int, relevance: int, clarity: int) -> float:
    """
    Compute 0-100 score in backend code using the agreed rubric:
    total_score = (correctness * 30 + completeness * 30 + relevance * 20 + clarity * 20) / 5
    """
    for dim, val in [
        ("correctness", correctness),
        ("completeness", completeness),
        ("relevance", relevance),
        ("clarity", clarity),
    ]:
        if not (0 <= val <= 5):
            raise ValueError(f"Score for {dim} must be an integer between 0 and 5, got {val}")

    raw = (
        correctness * RUBRIC_WEIGHTS["correctness"]
        + completeness * RUBRIC_WEIGHTS["completeness"]
        + relevance * RUBRIC_WEIGHTS["relevance"]
        + clarity * RUBRIC_WEIGHTS["clarity"]
    )
    return round(raw / 5.0, 2)


class DimensionScores(BaseModel):
    correctness: int = Field(..., ge=0, le=5, description="Factual and conceptual accuracy (30%)")
    completeness: int = Field(..., ge=0, le=5, description="Coverage of expected concepts & edge cases (30%)")
    relevance: int = Field(..., ge=0, le=5, description="Focus on question prompt without fluff (20%)")
    clarity: int = Field(..., ge=0, le=5, description="Structure, precision, and technical articulation (20%)")


class CitationItem(BaseModel):
    chunk_id: str = Field(..., description="ID of the verified retrieved reference chunk")
    source_name: str = Field(..., description="Document source name")
    topic: Optional[str] = Field(None, description="Topic classification")
    excerpt: Optional[str] = Field(None, description="Relevant excerpt grounding the evaluation")


class EvaluationResult(BaseModel):
    evaluation_id: str
    session_id: str
    question_id: str
    candidate_answer: str
    dimension_scores: DimensionScores
    weighted_score: float = Field(..., ge=0.0, le=100.0, description="Computed 0-100 weighted score")
    strengths: List[str] = Field(default_factory=list, description="Demonstrated strengths in the answer")
    missing_concepts: List[str] = Field(default_factory=list, description="Key concepts or trade-offs omitted")
    actionable_feedback: str = Field(..., description="Targeted guidance for candidate improvement")
    citation_chunk_ids: List[str] = Field(default_factory=list, description="Validated citation chunk IDs")
    citations: List[CitationItem] = Field(default_factory=list, description="Resolved citation metadata")
    evaluation_status: str = Field(
        default="completed",
        description="'completed' | 'insufficient_evidence' | 'conflicting_evidence'"
    )
    rubric_version: str = Field(default=RUBRIC_VERSION)
    created_at: str


class SubmitAnswerRequest(BaseModel):
    answer_text: str = Field(..., min_length=1, description="Candidate's technical response")


class SubmitAnswerResponse(BaseModel):
    evaluation: EvaluationResult
    session_id: str
    question_id: str
    session_status: str
    has_more_questions: bool

