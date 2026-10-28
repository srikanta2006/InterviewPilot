import logging
import re
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.evaluation import (
    CitationItem,
    DimensionScores,
    EvaluationResult,
    RUBRIC_VERSION,
    calculate_weighted_score,
)
from app.schemas.knowledge import SearchResultItem
from app.services.groq_client import GroqClientService

logger = logging.getLogger(__name__)


class LLMEvaluationPayload(BaseModel):
    """Structured response expected from Groq LLM evaluation."""
    correctness: int = Field(..., ge=0, le=5, description="Factual correctness (0-5)")
    completeness: int = Field(..., ge=0, le=5, description="Depth and coverage of expected criteria (0-5)")
    relevance: int = Field(..., ge=0, le=5, description="Direct addressing of the question (0-5)")
    clarity: int = Field(..., ge=0, le=5, description="Structure and technical communication (0-5)")
    strengths: List[str] = Field(default_factory=list, description="Demonstrated strengths")
    missing_concepts: List[str] = Field(default_factory=list, description="Missing expected criteria or gaps")
    actionable_feedback: str = Field(..., description="Actionable coaching feedback")
    suggested_citation_chunk_ids: List[str] = Field(
        default_factory=list,
        description="Chunk IDs from the provided context supporting the evaluation"
    )
    is_insufficient_evidence: bool = Field(
        default=False,
        description="True if provided technical context is insufficient to evaluate the answer"
    )


class AnswerEvaluator:
    """
    Evaluates candidate answers against a deterministic rubric,
    grounds feedback in retrieved reference evidence, validates citation IDs,
    and computes weighted score in backend code.
    """

    def __init__(self, groq_client: Optional[GroqClientService] = None):
        self.groq_client = groq_client or GroqClientService()

    def evaluate(
        self,
        session_id: str,
        question_id: str,
        question_text: str,
        competency: str,
        difficulty: str,
        expected_criteria: List[str],
        candidate_answer: str,
        retrieved_chunks: List[SearchResultItem],
    ) -> EvaluationResult:
        """
        Evaluate candidate answer.
        Computes weighted score deterministically in Python.
        Validates citation IDs against retrieved chunks.
        """
        evaluation_id = f"eval_{uuid.uuid4().hex[:10]}"
        trimmed_answer = candidate_answer.strip()

        # Build lookup map of valid retrieved chunks for strict citation verification
        valid_chunk_map: Dict[str, SearchResultItem] = {
            c.chunk_id: c for c in retrieved_chunks
        }

        # Check for insufficient evidence condition
        if not retrieved_chunks:
            logger.info("No reference chunks retrieved for evaluation. Flagging insufficient evidence.")
            return self._build_insufficient_evidence_result(
                evaluation_id=evaluation_id,
                session_id=session_id,
                question_id=question_id,
                candidate_answer=trimmed_answer,
                expected_criteria=expected_criteria,
            )

        llm_payload: Optional[LLMEvaluationPayload] = None

        if self.groq_client.is_configured:
            llm_payload = self._evaluate_with_groq(
                question_text=question_text,
                competency=competency,
                difficulty=difficulty,
                expected_criteria=expected_criteria,
                candidate_answer=trimmed_answer,
                retrieved_chunks=retrieved_chunks,
            )

        if not llm_payload:
            llm_payload = self._evaluate_deterministic_fallback(
                expected_criteria=expected_criteria,
                candidate_answer=trimmed_answer,
                retrieved_chunks=retrieved_chunks,
                competency=competency,
                difficulty=difficulty,
            )

        # Flag if LLM or fallback determined evidence was insufficient
        if llm_payload.is_insufficient_evidence:
            return self._build_insufficient_evidence_result(
                evaluation_id=evaluation_id,
                session_id=session_id,
                question_id=question_id,
                candidate_answer=trimmed_answer,
                expected_criteria=expected_criteria,
            )

        # Enforce integer clamping for dimension scores (0 to 5)
        correctness = max(0, min(5, int(llm_payload.correctness)))
        completeness = max(0, min(5, int(llm_payload.completeness)))
        relevance = max(0, min(5, int(llm_payload.relevance)))
        clarity = max(0, min(5, int(llm_payload.clarity)))

        # Compute weighted score strictly in Python code per Section 7 formula
        weighted_score = calculate_weighted_score(
            correctness=correctness,
            completeness=completeness,
            relevance=relevance,
            clarity=clarity,
        )

        # Validate citation IDs strictly against retrieved chunks (reject any hallucinated IDs)
        verified_chunk_ids: List[str] = []
        resolved_citations: List[CitationItem] = []

        for cid in llm_payload.suggested_citation_chunk_ids:
            if cid in valid_chunk_map and cid not in verified_chunk_ids:
                verified_chunk_ids.append(cid)
                chunk = valid_chunk_map[cid]
                resolved_citations.append(
                    CitationItem(
                        chunk_id=chunk.chunk_id,
                        source_name=chunk.source_name,
                        topic=chunk.topic,
                        excerpt=chunk.text[:250].strip(),
                    )
                )

        # If LLM cited nothing but we have retrieved chunks, attach the top grounding reference
        if not verified_chunk_ids and retrieved_chunks:
            top_c = retrieved_chunks[0]
            verified_chunk_ids.append(top_c.chunk_id)
            resolved_citations.append(
                CitationItem(
                    chunk_id=top_c.chunk_id,
                    source_name=top_c.source_name,
                    topic=top_c.topic,
                    excerpt=top_c.text[:250].strip(),
                )
            )

        import datetime
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return EvaluationResult(
            evaluation_id=evaluation_id,
            session_id=session_id,
            question_id=question_id,
            candidate_answer=trimmed_answer,
            dimension_scores=DimensionScores(
                correctness=correctness,
                completeness=completeness,
                relevance=relevance,
                clarity=clarity,
            ),
            weighted_score=weighted_score,
            strengths=llm_payload.strengths,
            missing_concepts=llm_payload.missing_concepts,
            actionable_feedback=llm_payload.actionable_feedback,
            citation_chunk_ids=verified_chunk_ids,
            citations=resolved_citations,
            evaluation_status="completed",
            rubric_version=RUBRIC_VERSION,
            created_at=now_iso,
        )

    def _evaluate_with_groq(
        self,
        question_text: str,
        competency: str,
        difficulty: str,
        expected_criteria: List[str],
        candidate_answer: str,
        retrieved_chunks: List[SearchResultItem],
    ) -> Optional[LLMEvaluationPayload]:
        """Request structured evaluation from Groq."""
        system_prompt = (
            "You are an impartial, highly rigorous Technical Bar Raiser at a premier engineering company. "
            "Evaluate the candidate's answer against the specific interview question, the expected evaluation criteria, "
            "and the provided technical reference documentation.\n\n"
            "SCORING RUBRIC (Each dimension is an integer 0 to 5):\n"
            "- Correctness (0-5): Technical accuracy, absence of misconceptions.\n"
            "- Completeness (0-5): Depth of coverage regarding expected criteria and edge cases.\n"
            "- Relevance (0-5): Direct focus on the prompt, no irrelevant filler.\n"
            "- Clarity (0-5): Technical precision, structured articulation.\n\n"
            "STRICT CITATION RULES:\n"
            "1. In 'suggested_citation_chunk_ids', you may ONLY list chunk IDs that exist verbatim in the provided reference excerpts.\n"
            "2. Never hallucinate or invent new chunk IDs.\n"
            "3. If the reference excerpts do not contain sufficient evidence to verify technical claims, set 'is_insufficient_evidence': true.\n"
            "4. Return strictly valid JSON."
        )

        context_block = ""
        for chunk in retrieved_chunks:
            context_block += f"[Chunk ID: {chunk.chunk_id} | Source: {chunk.source_name} ({chunk.topic})]\n{chunk.text}\n\n"

        criteria_block = "\n".join(f"- {c}" for c in expected_criteria)

        user_prompt = f"""
Competency Tested: {competency} (Difficulty: {difficulty})

Interview Question:
{question_text}

Expected Key Concepts / Evaluation Criteria:
{criteria_block}

Candidate's Submitted Answer:
{candidate_answer if candidate_answer else '[Candidate submitted empty response]'}

Retrieved Reference Context:
{context_block}

Evaluate the response and output a JSON object adhering to:
- "correctness": integer 0-5
- "completeness": integer 0-5
- "relevance": integer 0-5
- "clarity": integer 0-5
- "strengths": array of specific strengths noted in the answer
- "missing_concepts": array of concepts/criteria the candidate failed to mention
- "actionable_feedback": concrete advice for improvement
- "suggested_citation_chunk_ids": array of valid chunk IDs from the retrieved reference context
- "is_insufficient_evidence": boolean
"""
        return self.groq_client.extract_structured_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=LLMEvaluationPayload,
        )

    def _evaluate_deterministic_fallback(
        self,
        expected_criteria: List[str],
        candidate_answer: str,
        retrieved_chunks: List[SearchResultItem],
        competency: str,
        difficulty: str,
    ) -> LLMEvaluationPayload:
        """
        Deterministic, offline evaluation engine.
        Scores candidate answer based on keyword matches with expected criteria,
        answer substance, and technical depth.
        """
        words = candidate_answer.lower().split()
        word_count = len(words)

        # Empty or trivial response
        if word_count < 5:
            return LLMEvaluationPayload(
                correctness=0,
                completeness=0,
                relevance=0 if word_count == 0 else 1,
                clarity=0 if word_count == 0 else 1,
                strengths=[],
                missing_concepts=expected_criteria,
                actionable_feedback=(
                    f"The submitted answer is empty or too brief to evaluate competency in {competency}. "
                    "In a technical interview, structure your answer by outlining core principles, "
                    "implementation trade-offs, and operational failure modes."
                ),
                suggested_citation_chunk_ids=[c.chunk_id for c in retrieved_chunks[:1]],
                is_insufficient_evidence=False,
            )

        # Keyword matching against expected criteria
        covered_criteria = []
        missing_criteria = []

        for crit in expected_criteria:
            crit_keywords = [
                re.sub(r"[^\w]", "", w.lower())
                for w in crit.split()
                if len(w) > 3 and w.lower() not in {"with", "that", "from", "when", "into", "between"}
            ]
            matches = sum(1 for kw in crit_keywords if kw in words)
            if matches >= 1:
                covered_criteria.append(crit)
            else:
                missing_criteria.append(crit)

        total_crit = max(1, len(expected_criteria))
        coverage_ratio = len(covered_criteria) / total_crit

        # Score formulation
        if coverage_ratio >= 0.75 and word_count >= 50:
            correctness = 5
            completeness = 5
            relevance = 5
            clarity = 4 if word_count <= 250 else 3
        elif coverage_ratio >= 0.5 and word_count >= 30:
            correctness = 4
            completeness = 4
            relevance = 4
            clarity = 4
        elif coverage_ratio >= 0.25 or word_count >= 20:
            correctness = 3
            completeness = 2
            relevance = 3
            clarity = 3
        else:
            correctness = 2
            completeness = 1
            relevance = 2
            clarity = 2

        # Adjust clarity for very long repetitive answers
        if word_count > 400:
            clarity = max(1, clarity - 1)

        strengths = [
            f"Addressed key concept: {c}" for c in covered_criteria
        ]
        if word_count >= 40:
            strengths.append(f"Provided thoughtful technical explanation for {competency}.")

        missing = missing_criteria if missing_criteria else ["Consider elaborating further on operational telemetry and metrics."]

        feedback = (
            f"Good effort discussing {competency} at {difficulty} level. "
            f"You successfully touched upon {len(covered_criteria)} out of {total_crit} key evaluation criteria. "
        )
        if missing_criteria:
            feedback += f"To achieve a top score, deepen your response by covering: {', '.join(missing_criteria[:2])}."

        citation_ids = [c.chunk_id for c in retrieved_chunks[:2]]

        return LLMEvaluationPayload(
            correctness=correctness,
            completeness=completeness,
            relevance=relevance,
            clarity=clarity,
            strengths=strengths,
            missing_concepts=missing,
            actionable_feedback=feedback,
            suggested_citation_chunk_ids=citation_ids,
            is_insufficient_evidence=False,
        )

    def _build_insufficient_evidence_result(
        self,
        evaluation_id: str,
        session_id: str,
        question_id: str,
        candidate_answer: str,
        expected_criteria: List[str],
    ) -> EvaluationResult:
        """Create explicit insufficient evidence evaluation result."""
        import datetime
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return EvaluationResult(
            evaluation_id=evaluation_id,
            session_id=session_id,
            question_id=question_id,
            candidate_answer=candidate_answer,
            dimension_scores=DimensionScores(
                correctness=0,
                completeness=0,
                relevance=0,
                clarity=0,
            ),
            weighted_score=0.0,
            strengths=[],
            missing_concepts=expected_criteria,
            actionable_feedback=(
                "Evaluation Notice: The knowledge base does not currently contain verified reference documentation "
                "to reliably corroborate or refute technical claims for this specific answer. "
                "Per system safety rules, this evaluation is flagged as insufficient evidence rather than guessing."
            ),
            citation_chunk_ids=[],
            citations=[],
            evaluation_status="insufficient_evidence",
            rubric_version=RUBRIC_VERSION,
            created_at=now_iso,
        )

