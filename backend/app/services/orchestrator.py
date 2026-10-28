import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.db.session import DatabaseManager
from app.schemas.evaluation import (
    CitationItem,
    DimensionScores,
    EvaluationResult,
)
from app.schemas.interview import (
    CompetencyPlanItem,
    GeneratedQuestion,
    SessionResponse,
)
from app.schemas.profile import CandidateProfile, JobRequirements
from app.schemas.report import (
    FinalInterviewReport,
    QuestionEvaluationSummary,
    SessionListItem,
)
from app.services.answer_evaluator import AnswerEvaluator

from app.services.question_generator import QuestionGenerator
from app.services.retriever import KnowledgeRetriever

logger = logging.getLogger(__name__)

# Valid state machine states
VALID_STATES = {
    "setup",
    "profile_ready",
    "question_ready",
    "awaiting_answer",
    "evaluating",
    "completed",
}

# Permitted state transitions
ALLOWED_TRANSITIONS = {
    "setup": {"profile_ready"},
    "profile_ready": {"question_ready"},
    "question_ready": {"awaiting_answer", "evaluating", "question_ready", "completed"},
    "awaiting_answer": {"evaluating", "question_ready"},
    "evaluating": {"question_ready", "completed"},
    "completed": set(),
}


class InterviewOrchestrator:
    """
    Coordinates interview workflow, state transitions, competency plans,
    RAG evidence retrieval, and SQLite persistence.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        retriever: Optional[KnowledgeRetriever] = None,
        question_generator: Optional[QuestionGenerator] = None,
        answer_evaluator: Optional[AnswerEvaluator] = None,
    ):
        self.db = db_manager or DatabaseManager()
        self.retriever = retriever or KnowledgeRetriever()
        self.generator = question_generator or QuestionGenerator()
        self.evaluator = answer_evaluator or AnswerEvaluator()


    def create_session(
        self,
        candidate_profile: CandidateProfile,
        job_requirements: JobRequirements,
        total_questions: int = 5,
    ) -> Tuple[SessionResponse, GeneratedQuestion]:
        """
        Initialize a new interview session:
        1. Formulate competency plan.
        2. Create session record in SQLite (`profile_ready`).
        3. Retrieve grounded context for competency #1.
        4. Generate initial question.
        5. Persist question and advance session state to `question_ready`.
        """
        session_id = f"s_{uuid.uuid4().hex[:10]}"
        total = max(1, min(total_questions, 10))

        # 1. Build plan
        plan_items = self.generator.plan_competencies(
            candidate_profile=candidate_profile,
            job_requirements=job_requirements,
            total_questions=total,
        )
        plan_dicts = [item.model_dump() for item in plan_items]

        # 2. Persist session initially as profile_ready
        session_data = self.db.create_session(
            session_id=session_id,
            status="profile_ready",
            total_questions=total,
            candidate_profile=candidate_profile.model_dump(),
            job_requirements=job_requirements.model_dump(),
            competency_plan=plan_dicts,
        )

        # 3. Retrieve context for initial competency
        first_plan = plan_items[0]
        search_res = self.retriever.search(
            query=first_plan.competency,
            scope=first_plan.scope if first_plan.scope != "all" else None,
            top_k=3,
        )

        # 4. Generate first question
        first_question = self.generator.generate_question(
            session_id=session_id,
            order_index=0,
            competency=first_plan.competency,
            difficulty=first_plan.difficulty,
            candidate_profile=candidate_profile,
            job_requirements=job_requirements,
            retrieved_chunks=search_res.results,
            previous_questions=[],
            follow_up_rationale=first_plan.rationale,
        )

        # 5. Save question to DB
        self.db.save_question(
            question_id=first_question.question_id,
            session_id=session_id,
            order_index=0,
            competency=first_question.competency,
            difficulty=first_question.difficulty,
            question_text=first_question.question_text,
            expected_criteria=first_question.expected_criteria,
            retrieved_chunk_ids=first_question.retrieved_chunk_ids,
            retrieved_context=first_question.retrieved_context,
            follow_up_rationale=first_question.follow_up_rationale,
        )

        # 6. Advance session state to question_ready
        self.db.update_session_state(
            session_id=session_id,
            status="question_ready",
            current_question_index=0,
        )

        updated_session = self.get_session(session_id)
        if not updated_session:
            raise RuntimeError(f"Failed to load newly created session {session_id}")

        return updated_session, first_question

    def generate_next_question(
        self, session_id: str
    ) -> Tuple[SessionResponse, Optional[GeneratedQuestion], bool]:
        """
        Advance to the next question in the planned sequence.
        Returns (session, question, is_completed).
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        if session.status == "completed":
            return session, None, True

        next_index = session.current_question_index + 1

        # Check if interview is finished
        if next_index >= session.total_questions:
            self._transition_state(session_id, session.status, "completed")
            updated = self.get_session(session_id)
            return updated, None, True

        # Fetch competency plan for next question
        plan_item = session.competency_plan[next_index]

        # Gather previous questions for duplicate avoidance
        existing_questions = self.db.list_questions_for_session(session_id)
        prev_texts = [q["question_text"] for q in existing_questions]

        # Retrieve relevant RAG reference chunks
        search_res = self.retriever.search(
            query=plan_item.competency,
            scope=plan_item.scope if plan_item.scope != "all" else None,
            top_k=3,
        )

        # Generate question grounded in retrieved sources
        new_q = self.generator.generate_question(
            session_id=session_id,
            order_index=next_index,
            competency=plan_item.competency,
            difficulty=plan_item.difficulty,
            candidate_profile=session.candidate_profile,
            job_requirements=session.job_requirements,
            retrieved_chunks=search_res.results,
            previous_questions=prev_texts,
            follow_up_rationale=plan_item.rationale,
        )

        # Save question to DB
        self.db.save_question(
            question_id=new_q.question_id,
            session_id=session_id,
            order_index=next_index,
            competency=new_q.competency,
            difficulty=new_q.difficulty,
            question_text=new_q.question_text,
            expected_criteria=new_q.expected_criteria,
            retrieved_chunk_ids=new_q.retrieved_chunk_ids,
            retrieved_context=new_q.retrieved_context,
            follow_up_rationale=new_q.follow_up_rationale,
        )

        # Update session state
        self.db.update_session_state(
            session_id=session_id,
            status="question_ready",
            current_question_index=next_index,
        )

        updated_session = self.get_session(session_id)
        return updated_session, new_q, False

    def transition_state(self, session_id: str, target_state: str) -> SessionResponse:
        """Explicitly transition session state with validation."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        self._transition_state(session_id, session.status, target_state)
        return self.get_session(session_id)

    def _transition_state(self, session_id: str, current_state: str, target_state: str):
        """Validate and apply a state transition."""
        if target_state not in VALID_STATES:
            raise ValueError(f"Invalid target state '{target_state}'.")

        allowed = ALLOWED_TRANSITIONS.get(current_state, set())
        if target_state not in allowed:
            raise ValueError(
                f"Illegal state transition from '{current_state}' to '{target_state}'. "
                f"Allowed transitions: {list(allowed)}"
            )

        self.db.update_session_state(session_id=session_id, status=target_state)

    def get_session(self, session_id: str) -> Optional[SessionResponse]:
        """Fetch session by ID with validated Pydantic model."""
        raw = self.db.get_session(session_id)
        if not raw:
            return None
        return SessionResponse(
            session_id=raw["session_id"],
            status=raw["status"],
            current_question_index=raw["current_question_index"],
            total_questions=raw["total_questions"],
            competency_plan=[
                CompetencyPlanItem(**item) for item in raw["competency_plan"]
            ],
            candidate_profile=CandidateProfile(**raw["candidate_profile"]),
            job_requirements=JobRequirements(**raw["job_requirements"]),
            created_at=raw["created_at"],
            updated_at=raw["updated_at"],
        )

    def get_questions(self, session_id: str) -> List[GeneratedQuestion]:
        """Fetch all questions for a session ordered by index."""
        raw_list = self.db.list_questions_for_session(session_id)
        return [GeneratedQuestion(**q) for q in raw_list]

    def submit_and_evaluate_answer(
        self, session_id: str, question_id: str, answer_text: str
    ) -> EvaluationResult:
        """
        Transition session to 'evaluating', retrieve evidence grounded in the question & answer,
        execute deterministic rubric evaluation, persist result in SQLite, and transition state.
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        question = self.db.get_question(question_id)
        if not question or question["session_id"] != session_id:
            raise ValueError(f"Question '{question_id}' not found in session '{session_id}'.")

        # 1. Transition state machine to 'evaluating'
        if session.status in {"question_ready", "awaiting_answer"}:
            self._transition_state(session_id, session.status, "evaluating")

        # 2. Retrieve grounded evidence using question context + candidate answer
        search_query = f"{question['competency']}: {question['question_text']} {answer_text}"
        search_res = self.retriever.search(
            query=search_query,
            top_k=5,
        )

        retrieved_chunks = search_res.results
        # If secondary search returned empty, fall back to question's original retrieved context if present
        if not retrieved_chunks and question.get("retrieved_context"):
            from app.schemas.knowledge import SearchResultItem
            retrieved_chunks = [
                SearchResultItem(
                    chunk_id=c["chunk_id"],
                    document_id=c.get("document_id", "doc_ref"),
                    source_name=c.get("source_name", "Technical Reference"),
                    scope=c.get("scope", "shared"),
                    topic=c.get("topic", question["competency"]),
                    chunk_index=0,
                    text=c.get("excerpt", ""),
                    similarity_score=0.85,
                    distance=0.3,
                    metadata={},
                )
                for c in question["retrieved_context"]
            ]

        # 3. Evaluate answer
        eval_result = self.evaluator.evaluate(
            session_id=session_id,
            question_id=question_id,
            question_text=question["question_text"],
            competency=question["competency"],
            difficulty=question["difficulty"],
            expected_criteria=question["expected_criteria"],
            candidate_answer=answer_text,
            retrieved_chunks=retrieved_chunks,
        )

        # 4. Save evaluation to SQLite
        self.db.save_evaluation(
            evaluation_id=eval_result.evaluation_id,
            session_id=session_id,
            question_id=question_id,
            candidate_answer=eval_result.candidate_answer,
            evaluation_status=eval_result.evaluation_status,
            correctness=eval_result.dimension_scores.correctness,
            completeness=eval_result.dimension_scores.completeness,
            relevance=eval_result.dimension_scores.relevance,
            clarity=eval_result.dimension_scores.clarity,
            weighted_score=eval_result.weighted_score,
            strengths=eval_result.strengths,
            missing_concepts=eval_result.missing_concepts,
            actionable_feedback=eval_result.actionable_feedback,
            citation_chunk_ids=eval_result.citation_chunk_ids,
            citations=[c.model_dump() for c in eval_result.citations],
            rubric_version=eval_result.rubric_version,
        )

        # 5. Transition state back to question_ready
        self.db.update_session_state(session_id=session_id, status="question_ready")

        return eval_result

    def get_evaluation_for_question(self, question_id: str) -> Optional[EvaluationResult]:
        """Fetch evaluation for a specific question."""
        raw = self.db.get_evaluation_for_question(question_id)
        if not raw:
            return None
        return self._dict_to_evaluation(raw)

    def list_evaluations_for_session(self, session_id: str) -> List[EvaluationResult]:
        """Fetch all evaluations for a session."""
        raw_list = self.db.list_evaluations_for_session(session_id)
        return [self._dict_to_evaluation(r) for r in raw_list]

    def _dict_to_evaluation(self, d: Dict[str, Any]) -> EvaluationResult:
        return EvaluationResult(
            evaluation_id=d["evaluation_id"],
            session_id=d["session_id"],
            question_id=d["question_id"],
            candidate_answer=d["candidate_answer"],
            dimension_scores=DimensionScores(**d["dimension_scores"]),
            weighted_score=d["weighted_score"],
            strengths=d["strengths"],
            missing_concepts=d["missing_concepts"],
            actionable_feedback=d["actionable_feedback"],
            citation_chunk_ids=d["citation_chunk_ids"],
            citations=[CitationItem(**c) for c in d["citations"]],
            evaluation_status=d["evaluation_status"],
            rubric_version=d["rubric_version"],
            created_at=d["created_at"],
        )

    def get_interview_report(self, session_id: str) -> FinalInterviewReport:
        """
        Synthesize full interview report including overall composite score,
        dimension averages (0-5), competency breakdowns, key strengths, and verified citations.
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        questions = self.get_questions(session_id)
        evaluations_list = self.list_evaluations_for_session(session_id)
        eval_by_qid = {e.question_id: e for e in evaluations_list}

        question_summaries: List[QuestionEvaluationSummary] = []
        all_strengths: List[str] = []
        all_missing: List[str] = []
        citations_seen = set()
        citations_summary: List[CitationItem] = []

        scores_by_competency: Dict[str, List[float]] = {}
        dim_totals = {"correctness": 0.0, "completeness": 0.0, "relevance": 0.0, "clarity": 0.0}

        for q in questions:
            ev = eval_by_qid.get(q.question_id)
            if ev:
                question_summaries.append(
                    QuestionEvaluationSummary(
                        question_id=q.question_id,
                        order_index=q.order_index,
                        competency=q.competency,
                        difficulty=q.difficulty,
                        question_text=q.question_text,
                        candidate_answer=ev.candidate_answer,
                        dimension_scores=ev.dimension_scores,
                        weighted_score=ev.weighted_score,
                        strengths=ev.strengths,
                        missing_concepts=ev.missing_concepts,
                        actionable_feedback=ev.actionable_feedback,
                        citations=ev.citations,
                        status="evaluated",
                    )
                )
                dim_totals["correctness"] += ev.dimension_scores.correctness
                dim_totals["completeness"] += ev.dimension_scores.completeness
                dim_totals["relevance"] += ev.dimension_scores.relevance
                dim_totals["clarity"] += ev.dimension_scores.clarity

                if q.competency not in scores_by_competency:
                    scores_by_competency[q.competency] = []
                scores_by_competency[q.competency].append(ev.weighted_score)

                for s in ev.strengths:
                    if s not in all_strengths:
                        all_strengths.append(s)
                for m in ev.missing_concepts:
                    if m not in all_missing:
                        all_missing.append(m)
                for cit in ev.citations:
                    if cit.chunk_id not in citations_seen:
                        citations_seen.add(cit.chunk_id)
                        citations_summary.append(cit)
            else:
                question_summaries.append(
                    QuestionEvaluationSummary(
                        question_id=q.question_id,
                        order_index=q.order_index,
                        competency=q.competency,
                        difficulty=q.difficulty,
                        question_text=q.question_text,
                        status="unanswered",
                    )
                )

        num_eval = len(evaluations_list)
        if num_eval > 0:
            composite_score = round(
                sum(e.weighted_score for e in evaluations_list) / num_eval, 1
            )
            dim_averages = {
                k: round(v / num_eval, 2) for k, v in dim_totals.items()
            }
        else:
            composite_score = 0.0
            dim_averages = {"correctness": 0.0, "completeness": 0.0, "relevance": 0.0, "clarity": 0.0}

        competency_scores = {
            comp: round(sum(scores) / len(scores), 1)
            for comp, scores in scores_by_competency.items()
        }

        # Determine performance level band
        if composite_score >= 80.0:
            performance_level = "Strong Hire / Advanced"
        elif composite_score >= 65.0:
            performance_level = "Hire / Proficient"
        elif composite_score >= 50.0:
            performance_level = "Needs Review / Developing"
        else:
            performance_level = "Needs Improvement"

        cand_name = (
            session.candidate_profile.full_name
            or getattr(session.candidate_profile, "name", None)
            or "Candidate"
        )
        job_role = (
            session.job_requirements.job_title
            or getattr(session.job_requirements, "title", None)
            or "Technical Role"
        )

        return FinalInterviewReport(
            session_id=session_id,
            candidate_name=cand_name,
            job_title=job_role,
            total_questions=session.total_questions,
            questions_evaluated=num_eval,
            composite_score=composite_score,
            performance_level=performance_level,
            dimension_averages=dim_averages,
            competency_scores=competency_scores,
            question_summaries=question_summaries,
            key_strengths_summary=all_strengths[:5],
            priority_improvements_summary=all_missing[:5],
            citations_summary=citations_summary,
            created_at=session.created_at,
        )

    def list_all_sessions(self) -> List[SessionListItem]:
        """Fetch list of all past sessions from SQLite."""
        raw_list = self.db.list_all_sessions()
        return [SessionListItem(**r) for r in raw_list]

    def delete_session(self, session_id: str) -> bool:
        """Delete an interview session from SQLite."""
        return self.db.delete_session(session_id)

    def clear_all_sessions(self) -> int:
        """Clear all interview sessions from SQLite."""
        return self.db.clear_all_sessions()



